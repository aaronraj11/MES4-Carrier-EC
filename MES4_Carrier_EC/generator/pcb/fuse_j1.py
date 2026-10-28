"""J1 (M.2): runs of >=3 neighbouring GND fingers are fused by one F.Cu bar across their inner ends, with a few
0.5/0.3 vias hanging straight off the bar, instead of one via per finger."""
import sys, math
src=open(sys.argv[2]).read().split("log=[]")[0]; exec(src)
j1=F('J1'); cy=T(j1.GetPosition().y); BW=0.6; VR,VD=0.25,0.3
allp=sorted([p for p in j1.Pads() if min(T(p.GetSize().x),T(p.GetSize().y))<0.35], key=lambda p:T(p.GetPosition().x))
rows={}
for p in allp: rows.setdefault(round(T(p.GetPosition().y),1),[]).append(p)
runs=[]
for y,ps in rows.items():
    cur=[]
    for p in ps+[None]:
        if p is not None and p.GetNetname()=='GND': cur.append(p)
        else:
            if len(cur)>=3: runs.append(cur)
            cur=[]
def ctr(p): rr=bb4(p.GetBoundingBox()); return (rr[0]+rr[2])/2,(rr[1]+rr[3])/2,(rr[3]-rr[1])/2
# remove the per-finger vias + stubs of those fingers
gone=[]; kill=[]
trk=[(t,(T(t.GetStart().x),T(t.GetStart().y)),(T(t.GetEnd().x),T(t.GetEnd().y))) for t in b.GetTracks() if t.GetNetname()=='GND' and t.Type()==pcbnew.PCB_TRACE_T]
vv=[(v,(T(v.GetPosition().x),T(v.GetPosition().y))) for v in b.GetTracks() if v.Type()==pcbnew.PCB_VIA_T and v.GetNetname()=='GND']
for run in runs:
    for p in run:
        px,py,te=ctr(p)
        for t,a,c in trk:
            for s_,e_ in ((a,c),(c,a)):
                if math.hypot(s_[0]-px,s_[1]-py)<0.01 and abs(e_[0]-px)<0.01:
                    kill.append(t); kill+=[v for v,q in vv if math.hypot(q[0]-e_[0],q[1]-e_[1])<0.01]; gone.append(e_); break
for it in kill: b.Remove(it)
holes[:]=[h for h in holes if not any(math.hypot(h[0]-g[0],h[1]-g[1])<0.01 for g in gone)]
def seg(a,c,w):
    t=pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(b.FindNet('GND')); b.Add(t)
report=[]
for run in runs:
    pts=[ctr(p) for p in run]; py,te=pts[0][1],pts[0][2]; d=1 if py<cy else -1   # d: inward (under the socket body)
    ye=py+d*te; yb=ye+d*(BW/2-0.1); yv=ye+d*(BW-0.1+0.1+VR)
    xs=[x for x,_,_ in pts]; fw=min(T(run[0].GetSize().x),T(run[0].GetSize().y))
    for x in xs: seg((x,py),(x,yb),fw)                          # finger -> bar, inside the finger
    ins=BW/2-fw/2                                              # round bar ends stop at the end fingers' outer edges
    bx=[xs[0]+ins]+xs[1:-1]+[xs[-1]-ins]
    for x0,x1 in zip(bx,bx[1:]): seg((x0,yb),(x1,yb),BW)        # the bar
    n=max(2,round(len(xs)/4)); want=sorted(set(round(i*(len(xs)-1)/(n-1)) for i in range(n)))
    put=[]
    for i in want:                                              # nearest finger to the even spot that is free
        for j in sorted(range(len(xs)), key=lambda j:abs(j-i)):
            if abs(j-i)>2 or j in put: continue
            if ok_via(xs[j],yv,VR,VD,'GND','J1','loose') and all(abs(xs[j]-xs[k])>1.2 for k in put):
                put.append(j); break
    for j in put:
        seg((xs[j],yb),(xs[j],yv),fw)
        v=pcbnew.PCB_VIA(b); v.SetPosition(V(xs[j],yv)); v.SetWidth(mm(2*VR)); v.SetDrill(mm(VD)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(b.FindNet('GND')); b.Add(v)
        holes.append((xs[j],yv,VD/2))
    report.append(('pins %s-%s' % (run[0].GetNumber(), run[-1].GetNumber()), len(run), 'fingers ->', len(put), 'vias', [run[j].GetNumber() for j in sorted(put)]))
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(P,b)
print('removed vias', len(gone)); [print(*r) for r in report]
