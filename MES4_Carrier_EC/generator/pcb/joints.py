import pcbnew, math, collections, sys
b=pcbnew.LoadBoard(sys.argv[1]); T=pcbnew.ToMM
ends=collections.defaultdict(list)
for t in b.GetTracks():
    if t.GetClass()!='PCB_TRACK' or t.GetNetname()=='GND': continue
    a=(round(T(t.GetStart().x),2),round(T(t.GetStart().y),2)); c=(round(T(t.GetEnd().x),2),round(T(t.GetEnd().y),2))
    for p,q in ((a,c),(c,a)): ends[(p,t.GetLayer(),t.GetNetname())].append((math.degrees(math.atan2(q[1]-p[1],q[0]-p[0])),round(T(t.GetWidth()),2)))
pads={}
for f in b.GetFootprints():
    for p in f.Pads(): pads[(round(T(p.GetPosition().x),2),round(T(p.GetPosition().y),2))]=1
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': pads[(round(T(t.GetPosition().x),2),round(T(t.GetPosition().y),2))]=1   # vias are junctions too
n90=nw=0
for (p,l,n),v in ends.items():
    if len(v)<2: continue
    for i in range(len(v)):
        for j in range(i+1,len(v)):
            if abs(abs((v[i][0]-v[j][0]+180)%360-180)-90)<1 and p not in pads: n90+=1; print('90',n,p)
    if len({w for _,w in v})>1 and p not in pads: nw+=1; print('width',n,p,[w for _,w in v])
print('non-GND 90-degree joints off pads/vias:',n90,' width steps off pads/vias:',nw)
