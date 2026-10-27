import sys
sys.path.insert(0, sys.argv[0].rsplit('/',1)[0])
from sexp import *
d=parse(open(sys.argv[1]).read())[0]
comps=first(d,'components')
info={}
for c in find(comps,'comp'):
    ref=first(c,'ref')[1]; val=first(c,'value')[1]
    sp=first(c,'sheetpath'); sheet=first(sp,'names')[1] if sp else ''
    fields={f[1][1]:(f[2] if len(f)>2 else '') for f in find(first(c,'fields') or [],'field')}
    info[ref]=(val,sheet)
nets=first(d,'nets')
pins={}
for n in find(nets,'net'):
    name=first(n,'name')[1]
    for nd in find(n,'node'):
        r=first(nd,'ref')[1]; p=first(nd,'pin')[1]; pf=first(nd,'pinfunction')
        pins.setdefault(r,[]).append((p, pf[1] if pf else '', name))
sel=sys.argv[2] if len(sys.argv)>2 else None
import re
def key(r):
    m=re.match(r'([A-Za-z]+)(\d+)',r); return (m.group(1),int(m.group(2))) if m else (r,0)
for r in sorted(info,key=key):
    v,s=info[r]
    if sel and sel not in s: continue
    ps=sorted(pins.get(r,[]),key=lambda x:(len(x[0]),x[0]))
    print(f"{r} [{v}] {s}: " + "; ".join(f"{p}{'('+f+')' if f else ''}={n}" for p,f,n in ps))
