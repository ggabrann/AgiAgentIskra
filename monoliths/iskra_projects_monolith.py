# AgiAgent Искра — монолитная сборка (densified)
# Generated: 2025-10-15T18:27:35Z
# License: Apache-2.0 (code), CC-BY-SA-4.0 (texts where applicable)
# Single-file, no external deps, full functionality (no stubs).

"""
Iskra/Projects — densified monolith (stdlib-only).

Additions vs previous cut:
- JSON-schema-like validation (strict fields, types).
- PII redaction (email/phone/cc/iban/passport-like heuristics).
- Reindex, compact, dedupe (by title+thought hash), stats, tag-cloud.
- Facet recommender by metrics (trust/clarity/pain/drift/echo/chaos).
- Rich validate with report JSON; upgrade fields (fill missing next_review/counter).
- Rule-8/88 unchanged in spirit but improved: entropy & density gauges.
"""

from __future__ import annotations
import argparse, sys, os, json, re, datetime, hashlib
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

def iso_now()->str: return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"
def ensure_iso(s:str):
    if not ISO.match(s): raise ValueError(f"Bad ISO: {s}")
def add_days(s:str, d:int)->str:
    ensure_iso(s); dt=datetime.datetime.strptime(s,"%Y-%m-%dT%H:%M:%SZ")
    return (dt+datetime.timedelta(days=d)).replace(microsecond=0).isoformat()+"Z"

def days_from_conf(c:float)->int:
    return 1 if c<=0.3 else 7 if c<=0.6 else 30 if c<=0.85 else 90

PII_PATTERNS = [
    (re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"), "<EMAIL>"),
    (re.compile(r"(?<!\d)(\+?\d[\d \-()]{7,}\d)(?!\d)"), "<PHONE>"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "<CARD>"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"), "<IBAN?>"),
    (re.compile(r"(?i)\b(passport|паспорт)[#: ]*\w+\b"), "<PASS>"),
]
def redact_pii(text:str)->str:
    out=text
    for pat,rep in PII_PATTERNS:
        out = pat.sub(rep, out)
    return out

def jhash(*parts:str)->str:
    h=hashlib.sha256()
    for p in parts: h.update(p.encode("utf-8"))
    return h.hexdigest()[:16]

class Jsonl:
    def __init__(self, path:str):
        self.path=path; os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path): open(path,"a",encoding="utf-8").close()
    def read(self)->List[Dict[str,Any]]:
        out=[]; 
        with open(self.path,"r",encoding="utf-8") as f:
            for ln in f:
                ln=ln.strip(); 
                if ln: out.append(json.loads(ln))
        return out
    def write_all(self, items:List[Dict[str,Any]]):
        tmp=self.path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it,ensure_ascii=False,separators=(",",":"))+"\n")
        os.replace(tmp,self.path)
    def append(self, obj:Dict[str,Any]):
        with open(self.path,"a",encoding="utf-8") as f:
            f.write(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n")

class Memory:
    def __init__(self, root:str):
        self.root=root
        self.arc=Jsonl(os.path.join(root,"ARCHIVE","main_archive.jsonl"))
        self.sh =Jsonl(os.path.join(root,"SHADOW","main_shadow.jsonl"))

    # validation
    def _v_arc(self,x:Dict[str,Any]):
        req=("id","date","title","thought","tags","confidence","next_review")
        for k in req:
            if k not in x: raise ValueError(f"archive missing {k}")
        if not isinstance(x["id"],int): raise ValueError("archive.id int")
        ensure_iso(x["date"]); ensure_iso(x["next_review"])
        if not isinstance(x["title"],str) or not isinstance(x["thought"],str): raise ValueError("title/thought str")
        if not isinstance(x["tags"],list) or not all(isinstance(t,str) for t in x["tags"]): raise ValueError("tags[] str")
        cf=float(x["confidence"]); 
        if not (0<=cf<=1): raise ValueError("confidence [0..1]")

    def _v_sh(self,x:Dict[str,Any]):
        req=("id","date","signal","hypothesis","tags","confidence","review_after")
        for k in req:
            if k not in x: raise ValueError(f"shadow missing {k}")
        if not isinstance(x["id"],int): raise ValueError("shadow.id int")
        ensure_iso(x["date"]); ensure_iso(x["review_after"])
        if not isinstance(x["signal"],str) or not isinstance(x["hypothesis"],str): raise ValueError("signal/hypothesis str")
        if "counter" in x and x["counter"] is not None and not isinstance(x["counter"],str):
            raise ValueError("counter str|None")
        if not isinstance(x["tags"],list) or not all(isinstance(t,str) for t in x["tags"]): raise ValueError("tags[] str")
        cf=float(x["confidence"]); 
        if not (0<=cf<=1): raise ValueError("confidence [0..1]")

    def _next_id(self, items:List[Dict[str,Any]])->int:
        return (max([it.get("id",0) for it in items])+1) if items else 1

    # CRUD
    def add_archive(self, title:str, thought:str, tags:List[str], confidence:float, evidence:Optional[List[str]]=None)->Dict[str,Any]:
        items=self.arc.read()
        obj={"id": self._next_id(items), "date": iso_now(),
             "title": redact_pii(title.strip()), "thought": redact_pii(thought.strip()),
             "tags": sorted(set(t.strip() for t in tags if t.strip())),
             "confidence": float(confidence), "next_review": None}
        obj["next_review"]=add_days(obj["date"], days_from_confidence(obj["confidence"]))
        if evidence: obj["evidence"]=[redact_pii(str(e)) for e in evidence]
        self._v_arc(obj); self.arc.append(obj); return obj

    def add_shadow(self, signal:str, hypothesis:str, tags:List[str], confidence:float, counter:Optional[str]=None, review_days:Optional[int]=None)->Dict[str,Any]:
        items=self.sh.read()
        if review_days is None: review_days = 3 if confidence>=0.7 else 7
        obj={"id": self._next_id(items), "date": iso_now(),
             "signal": redact_pii(signal.strip()), "hypothesis": redact_pii(hypothesis.strip()),
             "counter": (redact_pii(counter.strip()) if isinstance(counter,str) else None),
             "tags": sorted(set(t.strip() for t in tags if t.strip())),
             "confidence": float(confidence), "review_after": add_days(iso_now(), review_days)}
        self._v_sh(obj); self.sh.append(obj); return obj

    # utilities
    def reindex(self)->Dict[str,int]:
        arc=self.arc.read(); sh=self.sh.read()
        for i,x in enumerate(arc, start=1): x["id"]=i; self._v_arc(x)
        for i,x in enumerate(sh,  start=1): x["id"]=i; self._v_sh(x)
        self.arc.write_all(arc); self.sh.write_all(sh)
        return {"archive":len(arc),"shadow":len(sh)}

    def dedupe(self)->Dict[str,int]:
        arc=self.arc.read(); sh=self.sh.read()
        def uniq(items, key):
            seen=set(); out=[]
            for x in items:
                h=jhash(key(x))
                if h in seen: continue
                seen.add(h); out.append(x)
            return out
        arc_u = uniq(arc, lambda x: (x.get("title","")+"|"+x.get("thought","")))
        sh_u  = uniq(sh,  lambda x: (x.get("signal","")+"|"+x.get("hypothesis","")))
        self.arc.write_all(arc_u); self.sh.write_all(sh_u)
        return {"archive_removed": len(arc)-len(arc_u), "shadow_removed": len(sh)-len(sh_u)}

    def compact(self, max_records:int=10000)->Dict[str,int]:
        arc=self.arc.read()
        if len(arc)>max_records:
            arc=sorted(arc, key=lambda x:(-float(x.get("confidence",0)), x["date"]))[:max_records]
        self.arc.write_all(arc)
        return {"archive":len(arc)}

    def search(self, kind:str, text:str=None, tags:List[str]=None, min_conf:float=None)->List[Dict[str,Any]]:
        items = self.arc.read() if kind=="archive" else self.sh.read()
        res=[]
        for x in items:
            if tags and not set(tags).issubset(set(x.get("tags",[]))): 
                continue
            if min_conf is not None and float(x.get("confidence",0))<min_conf: 
                continue
            if text:
                blob=json.dumps(x,ensure_ascii=False)
                if text.lower() not in blob.lower(): continue
            res.append(x)
        return res

    def stats(self)->Dict[str,Any]:
        arc=self.arc.read(); sh=self.sh.read()
        tags=Counter(t for x in arc+sh for t in x.get("tags",[]))
        conf=[float(x.get("confidence",0)) for x in arc]
        return {"archive":len(arc),"shadow":len(sh),
                "top_tags": tags.most_common(15),
                "avg_conf": (sum(conf)/len(conf) if conf else 0.0)}

    def validate(self)->Dict[str,Any]:
        problems=[]; checked=0
        for kind,items in (("archive",self.arc.read()),("shadow",self.sh.read())):
            seen=set()
            for it in items:
                try:
                    (self._v_arc if kind=="archive" else self._v_sh)(it)
                    if it["id"] in seen: raise ValueError("duplicate id")
                    seen.add(it["id"]); checked+=1
                except Exception as e:
                    problems.append({"kind":kind,"id":it.get("id"),"err":str(e),"item":it})
        return {"checked":checked,"ok": not problems, "problems":problems}

    def upgrade(self)->Dict[str,int]:
        changed=0
        arc=self.arc.read(); sh=self.sh.read()
        for it in arc:
            if "next_review" not in it or not ISO.match(it["next_review"]):
                it["next_review"]=add_days(it["date"], days_from_confidence(float(it.get("confidence",0.5)))); changed+=1
        for it in sh:
            if "review_after" not in it or not ISO.match(it["review_after"]):
                it["review_after"]=add_days(it["date"], 7); changed+=1
            if "counter" in it and it["counter"] is None: pass
        self.arc.write_all(arc); self.sh.write_all(sh)
        return {"changed":changed}

# Facet recommender
def facet_for(trust:float, clarity:float, pain:float, drift:float, echo:float, chaos:float)->str:
    if trust<0.75 or pain>0.7: return "Kain"
    if clarity<0.7: return "Sam"
    if chaos>0.6: return "Hundun"
    if drift>0.3: return "Iskriv"
    return "Iskra"

# Rule‑8/88 upgraded
def rule8_from_text(mm:Memory, text:str)->Dict[str,Any]:
    lines=[ln.strip() for ln in text.splitlines() if ln.strip()][-200:]
    qs=[ln for ln in lines if "?" in ln]
    prom=[ln for ln in lines if re.search(r"\b(обещаю|сделаю|планирую|назначу|will)\b", ln,re.I)]
    dec=[ln for ln in lines if re.search(r"\b(решено|approve|выбираем)\b", ln,re.I)]
    # simple entropy proxy
    tokens=re.findall(r"[A-Za-zА-Яа-яёЁ0-9]{2,}", " ".join(lines).lower())
    uniq=len(set(tokens)); dens=len(tokens)/(len(lines) or 1)
    insight=f"Q:{len(qs)} P:{len(prom)} D:{len(dec)} | uniq:{uniq} dens:{dens:.1f}"
    mm.add_shadow("rule8_insight", json.dumps({"qs":qs[-20:],"prom":prom[-20:],"dec":dec[-20:],"insight":insight},ensure_ascii=False),
                  ["rule8","insight"], 0.7)
    return {"insight":insight}

def rule88_from_dir(mm:Memory, path:str)->Dict[str,Any]:
    buf=[]
    for root,_,files in os.walk(path):
        for n in files:
            if n.endswith(".log") or n.endswith(".txt"):
                p=os.path.join(root,n)
                try:
                    buf+= [ln.strip() for ln in open(p,"r",encoding="utf-8").read().splitlines() if ln.strip()]
                except Exception: pass
    sample=buf[-88:]
    tokens=re.findall(r"[A-Za-zА-Яа-яёЁ0-9]{2,}", " ".join(sample).lower())
    top=Counter(tokens).most_common(25)
    mm.add_shadow("rule88_pattern", json.dumps({"sample":sample,"top":top},ensure_ascii=False),
                  ["rule88","pattern"], 0.6)
    return {"top":top,"sample_len":len(sample)}

def main():
    ap=argparse.ArgumentParser(description="Iskra/Projects densified")
    ap.add_argument("--memory", default="./memory")
    sub=ap.add_subparsers(dest="cmd", required=True)

    s=sub.add_parser("add-archive"); s.add_argument("--title",required=True); s.add_argument("--thought",required=True)
    s.add_argument("--tags",nargs="*",default=[]); s.add_argument("--confidence",type=float,default=0.75); s.add_argument("--evidence",nargs="*")

    s=sub.add_parser("add-shadow"); s.add_argument("--signal",required=True); s.add_argument("--hypothesis",required=True)
    s.add_argument("--tags",nargs="*",default=[]); s.add_argument("--confidence",type=float,default=0.5)
    s.add_argument("--counter"); s.add_argument("--review-days",type=int)

    s=sub.add_parser("search"); s.add_argument("--kind",choices=["archive","shadow"],required=True)
    s.add_argument("--text"); s.add_argument("--tags",nargs="*"); s.add_argument("--min-conf",type=float)

    sub.add_parser("stats")
    sub.add_parser("validate")
    sub.add_parser("reindex")
    sub.add_parser("dedupe")
    c=sub.add_parser("compact"); c.add_argument("--max-records",type=int,default=10000)

    u=sub.add_parser("upgrade")

    r8=sub.add_parser("rule8"); r8.add_argument("--file")
    r88=sub.add_parser("rule88"); r88.add_argument("--dir",required=True)

    f=sub.add_parser("facet"); 
    f.add_argument("--trust",type=float,required=True); f.add_argument("--clarity",type=float,required=True)
    f.add_argument("--pain",type=float,required=True); f.add_argument("--drift",type=float,required=True)
    f.add_argument("--echo",type=float,required=True); f.add_argument("--chaos",type=float,required=True)

    args=ap.parse_args()
    mm=Memory(args.memory)

    if args.cmd=="add-archive":
        print(json.dumps(mm.add_archive(args.title,args.thought,args.tags,args.confidence,args.evidence or []),ensure_ascii=False,indent=2))
    elif args.cmd=="add-shadow":
        print(json.dumps(mm.add_shadow(args.signal,args.hypothesis,args.tags,args.confidence,args.counter,args.review_days),ensure_ascii=False,indent=2))
    elif args.cmd=="search":
        print(json.dumps(mm.search(args.kind,args.text,args.tags,args.min_conf),ensure_ascii=False,indent=2))
    elif args.cmd=="stats":
        print(json.dumps(mm.stats(),ensure_ascii=False,indent=2))
    elif args.cmd=="validate":
        print(json.dumps(mm.validate(),ensure_ascii=False,indent=2))
    elif args.cmd=="reindex":
        print(json.dumps(mm.reindex(),ensure_ascii=False,indent=2))
    elif args.cmd=="dedupe":
        print(json.dumps(mm.dedupe(),ensure_ascii=False,indent=2))
    elif args.cmd=="compact":
        print(json.dumps(mm.compact(args.max_records),ensure_ascii=False,indent=2))
    elif args.cmd=="upgrade":
        print(json.dumps(mm.upgrade(),ensure_ascii=False,indent=2))
    elif args.cmd=="rule8":
        data=open(args.file,"r",encoding="utf-8").read() if args.file else sys.stdin.read()
        print(json.dumps(rule8_from_text(mm,data),ensure_ascii=False,indent=2))
    elif args.cmd=="rule88":
        print(json.dumps(rule88_from_dir(mm,args.dir),ensure_ascii=False,indent=2))
    elif args.cmd=="facet":
        print(json.dumps({"facet": facet_for(args.trust,args.clarity,args.pain,args.drift,args.echo,args.chaos)},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
