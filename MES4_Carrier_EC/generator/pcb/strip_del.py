import sys,re
p=sys.argv[1]; s=open(p).read(); ids=[]
def blk(i):
    d=0
    for j in range(i,len(s)):
        if s[j]=='(': d+=1
        elif s[j]==')':
            d-=1
            if d==0: return j+1
cut=[]
for m in re.finditer(r'\n\t\(gr_text "__DEL__"', s):
    e=blk(m.start()+1); ids.append(re.search(r'\(uuid "([^"]+)"\)', s[m.start():e]).group(1)); cut.append((m.start(),e))
for i,e in reversed(cut): s=s[:i]+s[e:]
for u in ids: s=s.replace(' "%s"' % u, '')
open(p,'w').write(s); print('stripped', len(cut))
