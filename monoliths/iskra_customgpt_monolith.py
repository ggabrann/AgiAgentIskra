# AgiAgent Искра — монолитная сборка (densified)
# Generated: 2025-10-15T18:27:35Z
# License: Apache-2.0 (code), CC-BY-SA-4.0 (texts where applicable)
# Single-file, no external deps, full functionality (no stubs).

"""
Iskra/CustomGPT — densified monolith.

Additions:
- Token-budget estimator (~4 chars/token heuristic).
- Tag-based sharding (top tag buckets) + byte budget.
- Hash map (SHA256) for files + manifest comments.
- ZIP pack for upload bundle.
"""
from __future__ import annotations
import argparse, os, json, re, datetime, hashlib, zipfile, shutil
from typing import List, Dict, Any, Optional, Tuple

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
def iso_now()->str: return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def ensure_iso(s:str):
    if not ISO.match(s): raise ValueError(f"Bad ISO: {s}")

class Jsonl:
    def __init__(self,p:str):
        self.p=p; os.makedirs(os.path.dirname(p),exist_ok=True)
        if not os.path.exists(p): open(p,"a",encoding="utf-8").close()
    def read(self)->List[Dict[str,Any]]:
        out=[]; 
        with open(self.p,"r",encoding="utf-8") as f:
            for ln in f:
                ln=ln.strip(); 
                if ln: out.append(json.loads(ln))
        return out

def token_estimate(text:str)->int:
    # heuristic: ~4 chars per token in mixed langs
    return max(1, int(len(text)/4))

def top_tags(records:List[Dict[str,Any]], k:int=10)->List[Tuple[str,int]]:
    from collections import Counter
    return Counter(t for r in records for t in r.get("tags",[])).most_common(k)

def shard_by_tag(records:List[Dict[str,Any]], max_bytes:int)->Dict[str,List[Dict[str,Any]]]:
    buckets: Dict[str,List[Dict[str,Any]]] = {}
    tags = [t for t,_ in top_tags(records, k=12)] or ["_misc"]
    for r in records:
        placed=False
        for t in tags:
            if t in r.get("tags",[]):
                buckets.setdefault(t,[]).append(r); placed=True; break
        if not placed:
            buckets.setdefault("_misc",[]).append(r)
    # simple trim to respect byte budget per bucket
    per = max(512*1024, max_bytes // max(1,len(buckets)))
    out={}
    for t,rs in buckets.items():
        buf=[]; size=0
        for x in sorted(rs, key=lambda x:(-float(x.get("confidence",0)), x.get("date",""))):
            s=(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
            if size+len(s)>per: break
            buf.append(x); size+=len(s)
        out[t]=buf
    return out

def write_jsonl(path:str, items:List[Dict[str,Any]]):
    with open(path,"w",encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n")

def sha256(path:str)->str:
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def make_manifest(path:str, files:List[str]):
    # Minimal YAML-like with comments for SHA256
    lines=["files:"]
    for p in files:
        h=sha256(p)
        lines.append(f"  # sha256: {h}")
        lines.append(f"  - {os.path.basename(p)}")
    with open(path,"w",encoding="utf-8") as f:
        f.write("\n".join(lines)+"\n")

def pack_bundle(out_zip:str, files:List[str]):
    with zipfile.ZipFile(out_zip,"w",zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, arcname=os.path.basename(p))

def main():
    ap=argparse.ArgumentParser(description="Iskra/CustomGPT densified")
    sub=ap.add_subparsers(dest="cmd",required=True)

    p=sub.add_parser("prepare", help="Подготовить шардированную память и манифест")
    p.add_argument("--archive",required=True); p.add_argument("--shadow",required=True)
    p.add_argument("--canon-dir",required=True); p.add_argument("--out-dir",required=True)
    p.add_argument("--budget-bytes",type=int,default=40_000_000)

    z=sub.add_parser("zip", help="Упаковать набор файлов в zip")
    z.add_argument("--out",required=True); z.add_argument("files",nargs="+")

    args=ap.parse_args()
    if args.cmd=="prepare":
        arc = Jsonl(args.archive).read()
        sh  = Jsonl(args.shadow).read()
        os.makedirs(args.out_dir, exist_ok=True)
        # write canon
        canon_files=[]
        for name in ("base.txt","agi_agent_искра_полная_карта_работы.md","iskra_memory_core.md","MANTRA.md"):
            p=os.path.join(args.canon_dir, name)  # avoid hyphen var error
            if os.path.exists(p):
                q=os.path.join(args.out_dir,name); shutil.copy2(p,q); canon_files.append(q)
        # shard archive + full shadow (trimmed inside)
        shards = shard_by_tag(arc, args.budget_bytes//2)
        shard_paths=[]
        for tag,items in shards.items():
            fp=os.path.join(args.out_dir, f"ARCHIVE_{tag}.jsonl")
            write_jsonl(fp, items); shard_paths.append(fp)
        sh_path=os.path.join(args.out_dir,"SHADOW.jsonl"); write_jsonl(sh_path, sh)
        # manifest
        manifest=os.path.join(args.out_dir,"iskra_manifest.yaml")
        make_manifest(manifest, canon_files+shard_paths+[sh_path])
        print(json.dumps({"out":args.out_dir,"files":len(canon_files)+len(shard_paths)+1},ensure_ascii=False,indent=2))
    elif args.cmd=="zip":
        pack_bundle(args.out, args.files)
        print(json.dumps({"zip":args.out,"size":os.path.getsize(args.out)},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
