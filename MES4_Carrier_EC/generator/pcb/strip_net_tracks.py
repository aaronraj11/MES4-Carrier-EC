"""Remove every via and track segment on the named nets from a .kicad_pcb (text level)."""
import sys,re
p=sys.argv[1]; names=sys.argv[2].split(','); s=open(p).read()
def blk(i):
    d=0
    for j in range(i,len(s)):
        if s[j]=='(': d+=1
        elif s[j]==')':
            d-=1
            if d==0: return j+1
netmap=dict((m.group(1),m.group(2)) for m in re.finditer(r'\n\t\(net (\d+) "([^"]*)"\)', s))
cut=[]
for m in re.finditer(r'\n\t\((via|segment)\n', s):
    e=blk(m.start()+1); body=s[m.start():e]
    nm=re.search(r'\(net (?:\d+ )?"([^"]*)"\)', body) or re.search(r'\(net (\d+)\)', body)
    netname=netmap.get(nm.group(1), nm.group(1)) if nm else None
    if netname in names: cut.append((m.start(),e))
for i,e in reversed(cut): s=s[:i]+s[e:]
open(p,'w').write(s); print('removed', len(cut), 'items on', names)
