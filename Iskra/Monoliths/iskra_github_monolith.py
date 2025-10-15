# AgiAgent Искра — монолитная сборка (densified)
# Generated: 2025-10-15T18:27:35Z
# License: Apache-2.0 (code), CC-BY-SA-4.0 (texts where applicable)
# Single-file, no external deps, full functionality (no stubs).

"""
Iskra/GitHub — densified monolith.

Additions:
- alias map generator (Unicode→ASCII) to `dist/aliases.json` (not committed).
- SHA256 parity check of canon across builds (github/projects/custom_gpt).
- PII linter for memory.
- All-in-one `ci-check` aggregator (unicode, memory, canon parity).
"""
from __future__ import annotations
import argparse, os, json, re, hashlib, tarfile, shutil
from typing import List, Dict, Any, Optional, Tuple

def list_files(root:str)->List[str]:
    out=[];
    for r,_,fs in os.walk(root):
        for f in fs: out.append(os.path.join(r,f))
    return out

def sha256(path:str)->str:
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()

def slug_ascii(name:str)->str:
    import unicodedata
    s=unicodedata.normalize("NFKD", name)
    s="".join(ch for ch in s if ord(ch)<128)
    s=re.sub(r"[^A-Za-z0-9._/-]+","_",s)
    s=re.sub(r"_+","_",s).strip("_")
    return s.lower()

def unicode_policy(repo:str)->Dict[str,Any]:
    files=list_files(repo)
    seen={}; conflicts=[]
    for p in files:
        rel=os.path.relpath(p, repo)
        alias=slug_ascii(rel)
        if alias in seen and seen[alias]!=rel:
            conflicts.append({"alias":alias,"a":seen[alias],"b":rel})
        else:
            seen[alias]=rel
    return {"ok": not conflicts, "conflicts":conflicts}

def canon_parity(repo:str)->Dict[str,Any]:
    base=os.path.join(repo,"builds")
    builds=["github","projects","custom_gpt"]
    checks={}
    names=["base.txt","agi_agent_искра_полная_карта_работы.md","iskra_memory_core.md"]
    for nm in names:
        hs=[]
        for b in builds:
            p=os.path.join(base,b,"canon",nm)
            if os.path.exists(p): hs.append(sha256(p))
            else: hs.append(None)
        checks[nm]=hs
    equal=all(len(set([h for h in v if h is not None]))<=1 for v in checks.values())
    return {"equal": equal, "hashes": checks}

def load_jsonl(p:str)->List[Dict[str,Any]]:
    out=[];
    with open(p,"r",encoding="utf-8") as f:
        for ln in f:
            ln=ln.strip();
            if ln: out.append(json.loads(ln))
    return out

PII = [
    (re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"), "email"),
    (re.compile(r"(?<!\d)(\+?\d[\d \-()]{7,}\d)(?!\d)"), "phone"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "card"),
]
def memory_lint(repo:str)->Dict[str,Any]:
    problems=[]
    for b in ("github","projects","custom_gpt"):
        arc=os.path.join(repo,"builds",b,"memory","ARCHIVE","main_archive.jsonl")
        sh =os.path.join(repo,"builds",b,"memory","SHADOW","main_shadow.jsonl")
        for kind,p in (("archive",arc),("shadow",sh)):
            if not os.path.exists(p): continue
            for it in load_jsonl(p):
                blob=json.dumps(it,ensure_ascii=False)
                for pat,name in PII:
                    if pat.search(blob):
                        problems.append({"build":b,"kind":kind,"id":it.get("id"),"pii":name})
    return {"ok": not problems, "problems": problems}

def build_dist(repo:str, out_tgz:str)->Dict[str,Any]:
    dist=os.path.join(repo,"dist");
    if os.path.exists(dist): shutil.rmtree(dist)
    os.makedirs(dist,exist_ok=True)
    # Copy canon (root) and github memory
    shutil.copytree(os.path.join(repo,"canon"), os.path.join(dist,"canon"))
    mem=os.path.join(repo,"builds","github","memory")
    if os.path.isdir(mem):
        shutil.copytree(mem, os.path.join(dist,"memory"))
    # generate aliases.json (not committed in repo, only in dist)
    aliases={}
    for p in list_files(repo):
        rel=os.path.relpath(p,repo); aliases[rel]=slug_ascii(rel)
    with open(os.path.join(dist,"aliases.json"),"w",encoding="utf-8") as f:
        json.dump(aliases,f,ensure_ascii=False,indent=2)
    with tarfile.open(out_tgz,"w:gz") as tar:
        tar.add(dist, arcname="iskra_dist")
    return {"out": out_tgz, "size": os.path.getsize(out_tgz)}

def sync_canon(repo:str)->Dict[str,Any]:
    canon=os.path.join(repo,"canon"); builds=os.path.join(repo,"builds")
    copied=0
    for b in ("github","projects","custom_gpt"):
        tgt=os.path.join(builds,b,"canon"); os.makedirs(tgt,exist_ok=True)
        for fn in os.listdir(canon):
            src=os.path.join(canon,fn); dst=os.path.join(tgt,fn)
            shutil.copy2(src,dst); copied+=1
        mantra_src=os.path.join(builds,"github","memory","MANTRA.md")
        if os.path.exists(mantra_src) and b!="github":
            os.makedirs(os.path.join(builds,b,"memory"), exist_ok=True)
            shutil.copy2(mantra_src, os.path.join(builds,b,"memory","MANTRA.md"))
    return {"copied":copied}

def ci_check(repo:str)->Dict[str,Any]:
    u=unicode_policy(repo); m=memory_lint(repo); c=canon_parity(repo)
    return {"unicode":u,"memory":m,"canon":c,"ok": (u["ok"] and m["ok"] and c["equal"])}

def main():
    import argparse
    ap=argparse.ArgumentParser(description="Iskra/GitHub densified")
    ap.add_argument("--root", default=".")
    sub=ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync-canon")
    sub.add_parser("unicode-policy")
    sub.add_parser("memory-lint")
    sub.add_parser("canon-parity")
    b=sub.add_parser("build-dist"); b.add_argument("--out", default="dist.tgz")
    sub.add_parser("ci-check")
    args=ap.parse_args()
    repo=os.path.abspath(args.root)
    if args.cmd=="sync-canon": print(json.dumps(sync_canon(repo),ensure_ascii=False,indent=2))
    elif args.cmd=="unicode-policy": print(json.dumps(unicode_policy(repo),ensure_ascii=False,indent=2))
    elif args.cmd=="memory-lint": print(json.dumps(memory_lint(repo),ensure_ascii=False,indent=2))
    elif args.cmd=="canon-parity": print(json.dumps(canon_parity(repo),ensure_ascii=False,indent=2))
    elif args.cmd=="build-dist": print(json.dumps(build_dist(repo, os.path.abspath(args.out)),ensure_ascii=False,indent=2))
    elif args.cmd=="ci-check": print(json.dumps(ci_check(repo),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
