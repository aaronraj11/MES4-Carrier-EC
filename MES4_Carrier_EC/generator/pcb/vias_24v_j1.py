"""+24V vias with one pattern per part type, and GND vias for the M.2 (J1) fingers.
Run after strip_net_tracks.py has removed the old +24V vias."""
import sys, math, pcbnew
P=sys.argv[1]; b=pcbnew.LoadBoard(P); mm=pcbnew.FromMM; T=pcbnew.ToMM; V=lambda x,y: pcbnew.VECTOR2I(mm(x),mm(y))
def F(r): return b.FindFootprintByReference(r)
def bb4(bb): return (T(bb.GetLeft()),T(bb.GetTop()),T(bb.GetRight()),T(bb.GetBottom()))
def crt(f):
    f.BuildCourtyardCaches(); c=f.GetCourtyard(pcbnew.F_CrtYd); return bb4(c.BBox()) if c.OutlineCount() else bb4(f.GetBoundingBox(False,False))
def d_pt_rect(x,y,r): return math.hypot(max(r[0]-x,0,x-r[2]), max(r[1]-y,0,y-r[3]))
def d_seg_rect(a,c,r):
    n=max(2,int(math.hypot(c[0]-a[0],c[1]-a[1])/0.05)+1)
    return min(d_pt_rect(a[0]+(c[0]-a[0])*i/(n-1), a[1]+(c[1]-a[1])*i/(n-1), r) for i in range(n))
def over(a,o,m): return a[0]<o[2]+m and o[0]<a[2]+m and a[1]<o[3]+m and o[1]<a[3]+m
def clr(nm): return 0.6 if nm.startswith('/Winch/') else 0.3 if nm in ('/Power/+24V_IN','/Power/+24V_F') else 0.2
HH=0.5
copper=[]; holes=[]; courts=[]; silk=[]; labels=[]; lanes=[]; vias=[]
for f in b.GetFootprints():
    courts.append((f.GetReference(), crt(f)))
    if f.Reference().IsVisible() and f.Reference().GetLayer()==pcbnew.F_SilkS: labels.append((f.GetReference(), bb4(f.Reference().GetBoundingBox())))
    silk+=[(f.GetReference(), bb4(g.GetBoundingBox())) for g in f.GraphicalItems() if g.GetLayer()==pcbnew.F_SilkS]
    pads=list(f.Pads())
    for p in pads:
        th=p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH); nm='__npth__' if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH else p.GetNetname()
        copper.append((bb4(p.GetBoundingBox()), nm, p.IsOnLayer(pcbnew.F_Cu) or th))
        if th and p.GetDrillSize().x>0: holes.append((T(p.GetPosition().x),T(p.GetPosition().y),T(max(p.GetDrillSize().x,p.GetDrillSize().y))/2))
    smd=[p for p in pads if p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD]
    if len(smd)>=6:
        cx,cy=T(f.GetPosition().x),T(f.GetPosition().y)
        for p in smd:
            if p.GetNetname() in ('GND','+24V','') or p.GetNetname().startswith('unconnected'): continue
            rr=bb4(p.GetBoundingBox()); px,py=(rr[0]+rr[2])/2,(rr[1]+rr[3])/2; w,h=rr[2]-rr[0],rr[3]-rr[1]
            if w<h: dy=1 if py>cy else -1; lanes.append((rr[0]-0.05, min(py,py+dy*(h/2+1.5)), rr[2]+0.05, max(py,py+dy*(h/2+1.5))))
            else:   dx=1 if px>cx else -1; lanes.append((min(px,px+dx*(w/2+1.5)), rr[1]-0.05, max(px,px+dx*(w/2+1.5)), rr[3]+0.05))
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA':
        x,y=T(t.GetPosition().x),T(t.GetPosition().y); r=T(t.GetWidth(pcbnew.F_Cu))/2
        copper.append(((x-r,y-r,x+r,y+r), t.GetNetname(), True)); holes.append((x,y,T(t.GetDrillValue())/2)); vias.append((x,y,t.GetNetname()))
    else:
        a=(T(t.GetStart().x),T(t.GetStart().y)); c=(T(t.GetEnd().x),T(t.GetEnd().y)); hw=T(t.GetWidth())/2
        copper.append(((min(a[0],c[0])-hw,min(a[1],c[1])-hw,max(a[0],c[0])+hw,max(a[1],c[1])+hw), t.GetNetname(), True))
silk+=[('__board__', bb4(d.GetBoundingBox())) for d in b.GetDrawings() if d.GetLayer()==pcbnew.F_SilkS]
def ok_via(x,y,vr,vd,net,ref,mode):
    if not (50.7<x<249.1 and 50.2<y<148.6): return False
    if any(nm!=net and d_pt_rect(x,y,rr)<vr+clr(nm) for rr,nm,_ in copper): return False
    if any(math.hypot(x-hx,y-hy)<vd/2+hr+HH for hx,hy,hr in holes): return False
    if any(d_pt_rect(x,y,rr)<vr+0.05 for rr in lanes): return False
    if any(fr!=ref and rr[0]<x<rr[2] and rr[1]<y<rr[3] for fr,rr in courts): return False
    if mode=='strict' and any(d_pt_rect(x,y,rr)<vr+0.05 for fr,rr in labels): return False
    return not any(fr!=ref and d_pt_rect(x,y,rr)<vr+0.05 for fr,rr in silk)
def ok_track(a,c,w,net):
    if any(onF and nm!=net and d_seg_rect(a,c,rr)<w/2+clr(nm) for rr,nm,onF in copper): return False
    return not any(d_seg_rect(a,c,rr)<w/2+0.05 for rr in lanes)
def add(net,pts,tracks,vr,vd,tw):
    ni=b.FindNet(net)
    for x,y in pts:
        v=pcbnew.PCB_VIA(b); v.SetPosition(V(x,y)); v.SetWidth(mm(2*vr)); v.SetDrill(mm(vd)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(ni); b.Add(v)
        copper.append(((x-vr,y-vr,x+vr,y+vr),net,True)); holes.append((x,y,vd/2)); vias.append((x,y,net))
    for a,c in tracks:
        t=pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(tw)); t.SetLayer(pcbnew.F_Cu); t.SetNet(ni); b.Add(t)
        copper.append(((min(a[0],c[0])-tw/2,min(a[1],c[1])-tw/2,max(a[0],c[0])+tw/2,max(a[1],c[1])+tw/2),net,True))
def snap4(dx,dy): return (1 if dx>0 else -1,0) if abs(dx)>=abs(dy) else (0,1 if dy>0 else -1)
def pad_geo(f,p):
    rr=bb4(p.GetBoundingBox()); px,py=(rr[0]+rr[2])/2,(rr[1]+rr[3])/2; w,h=rr[2]-rr[0],rr[3]-rr[1]; pads=list(f.Pads())
    if len(pads)==2: q=[x for x in pads if x is not p][0]; ax=snap4(px-T(q.GetPosition().x),py-T(q.GetPosition().y))
    else: c=crt(f); ax=snap4(px-(c[0]+c[2])/2, py-(c[1]+c[3])/2)
    return px,py,w,h,ax
def plan(f,p,pattern,net,vr,vd,heads_all=True):
    """vias + tracks for one pad in a pattern, or None. Patterns: single / across2 / inline2."""
    ref=f.GetReference(); px,py,w,h,ax=pad_geo(f,p)
    heads=[ax,(ax[1],ax[0]),(-ax[1],-ax[0])] if heads_all else [ax]
    for mode in ('strict','loose'):
        for ux,uy in heads:
            te=w/2 if ux else h/2; across=h if ux else w
            for gap in [0.1+0.1*i for i in range(12)]:
                s=te+gap+vr
                if pattern=='across2':
                    if across<2*vr+0.5: break
                    o=max(vr+0.2,(vd+HH)/2); src=[(px-uy*k,py+ux*k) for k in (-o,o)]
                    pts=[(sx+ux*s,sy+uy*s) for sx,sy in src]; trk=list(zip(src,pts)); tw=min(0.7,across/2)
                elif pattern in ('pairR','pairL'):
                    k=(vd+HH+0.0)*(1 if pattern=='pairR' else -1); src=[(px,py),(px-uy*k,py+ux*k)]
                    if abs(k)>across/2+0.05: break
                    pts=[(sx+ux*s,sy+uy*s) for sx,sy in src]; trk=list(zip(src,pts)); tw=min(0.7,across/2)
                elif pattern=='inline2':
                    d2=vd+HH+0.05; pts=[(px+ux*s,py+uy*s),(px+ux*(s+d2),py+uy*(s+d2))]; trk=[((px,py),pts[1])]; tw=min(1.0,across*0.9)
                else:
                    pts=[(px+ux*s,py+uy*s)]; trk=[((px,py),pts[0])]; tw=min(1.0,max(0.3,across*0.9))
                edge=lambda a,c: ((a[0]+ux*te, a[1]+uy*te), c)
                if all(ok_via(x,y,vr,vd,net,ref,mode) for x,y in pts) and all(ok_track(*edge(a,c),tw,net) for a,c in trk):
                    return pts,trk,tw,(ux,uy)==ax
    return None
log=[]
# ---- +24V: one pattern per part type (first that fits every member), 0.8/0.4 vias
GROUPS=[(['R8','R11','R16','R19'],['across2','pairR','pairL','inline2','single']),     # 30 mOhm current shunts, 3 A
        (['L1','L2'],['across2','inline2','single']),                  # pi-filter inductors
        (['F9'],['across2','inline2','single']), (['C1'],['across2','inline2','single']), (['D9'],['across2','inline2','single']),
        (['C2','C3'],['single']), (['F7','F8'],['single']), (['D8'],['single']), (['R7'],['single'])]
for refs,patterns in GROUPS:
    pads=[(F(r),p) for r in refs for p in F(r).Pads() if p.GetNetname()=='+24V' and p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD]
    for pat in patterns:                                   # plan every member first; add only if all fit
        plans=[(f.GetReference(),plan(f,p,pat,'+24V',0.4,0.4)) for f,p in pads]
        if all(pl is not None for _,pl in plans):
            for r,pl in plans: add('+24V',pl[0],pl[1],0.4,0.4,pl[2])
            log.append((refs,pat,[(r,'straight' if pl[3] else 'side') for r,pl in plans])); break
    else: log.append((refs,'NONE',[]))
# ---- J1 (M.2) GND fingers: 0.5/0.3 vias straight out of each finger; consecutive GND fingers alternate near / far
j1=F('J1'); fingers=[p for p in j1.Pads() if p.GetNetname()=='GND' and min(T(p.GetSize().x),T(p.GetSize().y))<0.35]
rows={}
for p in fingers: rows.setdefault(round(T(p.GetPosition().y),1),[]).append(p)
allp=sorted([p for p in j1.Pads() if min(T(p.GetSize().x),T(p.GetSize().y))<0.35], key=lambda p:T(p.GetPosition().x))
j1fail=[]; j1n=0; j1dir=[]
for y,ps in rows.items():
    ps.sort(key=lambda p:T(p.GetPosition().x)); out=-1 if y<T(j1.GetPosition().y) else 1
    rowpads=[p for p in allp if round(T(p.GetPosition().y),1)==y]
    k=0
    for i,p in enumerate(ps):
        idx=rowpads.index(p); prev=rowpads[idx-1] if idx>0 else None
        k = k+1 if (prev is not None and prev.GetNetname()=='GND') else 0
        rr=bb4(p.GetBoundingBox()); px,py=(rr[0]+rr[2])/2,(rr[1]+rr[3])/2; te=(rr[3]-rr[1])/2
        gaps=([0.1] if k%2==0 else [0.8])+[0.1+0.1*j for j in range(20)]
        hit=None
        for d in (-out,out):                               # inward (under the socket body) first: keeps the escape side free
            for mode in ('strict','loose'):
                for g in gaps:
                    s=te+g+0.25; x,yy=px,py+d*s
                    if ok_via(x,yy,0.25,0.3,'GND','J1',mode) and ok_track((px,py+d*te),(x,yy),0.25,'GND'): hit=(x,yy); break
                if hit: break
            if hit: break
        if hit: add('GND',[hit],[((px,py),hit)],0.25,0.3,0.25); j1n+=1; j1dir.append(p.GetNumber() if d==out else None)
        else: j1fail.append(p.GetNumber())
# ---- labels a new via sits under move to the nearest free side of their part
newv=[(x,y) for x,y,nm in vias]
def lab_free(bx, ref):
    if not (50.4<bx[0] and bx[2]<249.4 and 49.9<bx[1] and bx[3]<148.9): return False
    if any(math.hypot(min(max(x,bx[0]),bx[2])-x, min(max(y,bx[1]),bx[3])-y)<0.45 for x,y in newv): return False
    if any(over(bx,rr,0.12) for rr,nm,onF in copper if onF): return False
    if any(over(bx,rr,0.1) for fr,rr in silk+[(f2,r2) for f2,r2 in labels if f2!=ref]): return False
    return not any(fr!=ref and over(bx,rr,0.0) for fr,rr in courts)
moved=[]; stuck=[]
for i,(ref,lb) in enumerate(labels):
    if not any(math.hypot(min(max(x,lb[0]),lb[2])-x, min(max(y,lb[1]),lb[3])-y)<0.4 for x,y in newv): continue
    f=F(ref); l,t,r,bt=crt(f); w_,h_=lb[2]-lb[0],lb[3]-lb[1]; cx_,cy_=(l+r)/2,(t+bt)/2
    cands=[(cx_,t-d-h_/2) for d in (0.1,0.4,0.8,1.2)]+[(cx_,bt+d+h_/2) for d in (0.1,0.4,0.8,1.2)]+[(l-d-w_/2,cy_) for d in (0.1,0.4,0.8)]+[(r+d+w_/2,cy_) for d in (0.1,0.4,0.8)]
    if ref=='J1': cands=[(l+1.6+w_/2, bt+d+h_/2) for d in (0.8,1.2,1.6,2.0)]+cands
    hit=next(((x,y) for x,y in cands if lab_free((x-w_/2,y-h_/2,x+w_/2,y+h_/2), ref)), None)
    if hit: f.Reference().SetPosition(V(*hit)); labels[i]=(ref,(hit[0]-w_/2,hit[1]-h_/2,hit[0]+w_/2,hit[1]+h_/2)); moved.append(ref)
    else: stuck.append(ref)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(P,b)
for refs,pat,how in log: print('%-22s %-8s %s' % (','.join(refs), pat, how))
print('J1 GND finger vias', j1n, 'of', len(fingers), '| no spot:', j1fail, '| outward:', [n for n in j1dir if n])
print('labels moved', moved, 'stuck', stuck)
