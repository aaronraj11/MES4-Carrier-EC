"""GND vias v2: every via straight off the end of its pad (along the part's axis, or straight out of an IC pin),
headings 0/90/180/270 only, as close as the rules allow; diode + marks re-placed beside the anodes afterwards."""
import sys, math, pcbnew
P=sys.argv[1]; b=pcbnew.LoadBoard(P); mm=pcbnew.FromMM; T=pcbnew.ToMM; V=lambda x,y: pcbnew.VECTOR2I(mm(x),mm(y))
VR, VD, CL, HH = 0.3, 0.3, 0.2, 0.5
gnd=b.FindNet('GND')
def F(r): return b.FindFootprintByReference(r)
def bb4(bb): return (T(bb.GetLeft()),T(bb.GetTop()),T(bb.GetRight()),T(bb.GetBottom()))
def crt(f):
    f.BuildCourtyardCaches(); c=f.GetCourtyard(pcbnew.F_CrtYd); return bb4(c.BBox()) if c.OutlineCount() else bb4(f.GetBoundingBox(False,False))
def lab_wh(ref):
    t=F(ref).Reference(); a=t.GetTextAngleDegrees(); t.SetTextAngleDegrees(0); bb=t.GetBoundingBox(); w,h=T(bb.GetWidth()),T(bb.GetHeight()); t.SetTextAngleDegrees(a); return w,h
def place(ref, rot, left=None, cx=None, cy=None):
    f=F(ref); f.SetOrientationDegrees(rot); l,t,r,bt=crt(f); f.Move(V((left-l) if left is not None else (cx-(l+r)/2), cy-(t+bt)/2)); return crt(f)
def text(s,x,y,grp):
    t=pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(V(0.8,1.0)); t.SetBold(True)
    t.SetTextThickness(mm(0.16)); t.SetPosition(V(x,y)); b.Add(t)
    if grp: grp.AddItem(t)
    return t
def d_pt_rect(x,y,r): return math.hypot(max(r[0]-x,0,x-r[2]), max(r[1]-y,0,y-r[3]))
def d_seg_rect(a,c,r):
    n=max(2,int(math.hypot(c[0]-a[0],c[1]-a[1])/0.05)+1)
    return min(d_pt_rect(a[0]+(c[0]-a[0])*i/(n-1), a[1]+(c[1]-a[1])*i/(n-1), r) for i in range(n))
def over(a,o,m): return a[0]<o[2]+m and o[0]<a[2]+m and a[1]<o[3]+m and o[1]<a[3]+m

# ---- A. old diode + marks out (re-placed at the end); the LED array's own + stay
for d in b.GetDrawings():
    if d.GetClass()=='PCB_TEXT' and d.GetText()=='+' and not (d.GetParentGroup() and d.GetParentGroup().GetName()=='MOD support'):
        d.SetText('__DEL__')
# ---- B. STDC14 corner: J2 to the left (label above it), ESD cells = via slot | diode (anode left) | ref, + under the anode
dbg=next(g for g in b.Groups() if g.GetName()=='DBG ST-Link + reset')
ads_bot=max(crt(F(r))[3] for r in ('C23','R32'))+0.15+lab_wh('R32')[1]
ymid=(ads_bot+crt(F('J1'))[1])/2
l,t,r,bt=place('J2',180,left=74.25,cy=ymid); w,h=lab_wh('J2'); jt=F('J2').Reference(); jt.SetTextAngleDegrees(90); jt.SetPosition(V(l-0.02-h/2, ymid))
# strip beside J1, top to bottom: SW1, its ref, RESET, C8, room for its via, ref, C9, via room, ref (GND pads face down)
strip_cx=(73.3+77.2)/2; ys=crt(F('SW1'))[1]
l2,t2,r2,b2=place('SW1',90,cx=strip_cx,cy=ys+3.1); w2,h2=lab_wh('SW1'); F('SW1').Reference().SetPosition(V(strip_cx,b2+0.15+h2/2)); yy=b2+0.15+h2+0.3
rs=next(i for i in dbg.GetItems() if i.GetClass()=='PCB_TEXT' and i.GetText()=='RESET'); rh=T(rs.GetBoundingBox().GetHeight())
rs.SetPosition(V(strip_cx, yy+rh/2)); yy+=rh+0.5
for c in ('C8','C9'):
    f=F(c); f.SetOrientationDegrees(90)
    gp=[q for q in f.Pads() if q.GetNetname()=='GND'][0]; op=[q for q in f.Pads() if q.GetNetname()!='GND'][0]
    if gp.GetPosition().y < op.GetPosition().y: f.SetOrientationDegrees(270)
    l3,t3,r3,b3=place(c,f.GetOrientationDegrees(),cx=strip_cx,cy=0); f.Move(V(0, yy-t3)); l3,t3,r3,b3=crt(f)
    w3,h3=lab_wh(c); f.Reference().SetPosition(V(strip_cx, b3+0.95+h3/2)); yy=b3+0.95+h3+0.4
jl=F('J4').Reference(); jl.SetPosition(V(T(jl.GetPosition().x), max(yy+1.2, T(jl.GetPosition().y))))
lw=max(lab_wh(d)[0] for d in ('D1','D2','D3','D4','D5')); cell=0.95+3.29+0.2+lw
grid_plus=[]
for col,refs in enumerate((('D1','D2','D3'),('D4','D5'))):
    x0=r+0.5+col*(cell+0.4)
    for k,d in enumerate(refs):
        y=ymid+(k-1)*3.2; l2,t2,r2,b2=place(d,180,left=x0+0.95,cy=y); w2,h2=lab_wh(d)
        F(d).Reference().SetPosition(V(r2+0.2+w2/2,y))
        an=[p for p in F(d).Pads() if p.GetNumber()=='2'][0]
        grid_plus.append(text('+',T(an.GetPosition().x), b2+0.1+0.5, dbg))
# ---- C. LED array: voltage boxes 0.6 mm further out so each cathode can take its via straight off the pad
mod=next(g for g in b.Groups() if g.GetName()=='MOD support')
for i in mod.GetItems():
    if i.GetClass()=='PCB_SHAPE' and i.GetLayer()==pcbnew.F_SilkS and i.IsFilled(): i.Move(V(0.6,0))
pcbnew.SaveBoard(P,b)

F('D22').Move(V(0,1.5))
# ---- D. vias
copper=[]; holes=[]; courts=[]; lanes=[]; silk=[]; lane_src=[]; labels=[]
fps=list(b.GetFootprints())
for f in fps:
    courts.append((f.GetReference(), crt(f)))
    if f.Reference().IsVisible() and f.Reference().GetLayer()==pcbnew.F_SilkS: labels.append((f.GetReference(), bb4(f.Reference().GetBoundingBox())))
    for g in f.GraphicalItems():
        if g.GetLayer()==pcbnew.F_SilkS: silk.append((f.GetReference(), bb4(g.GetBoundingBox())))
    pads=list(f.Pads())
    for p in pads:
        rr=bb4(p.GetBoundingBox()); net=p.GetNetname(); th=p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH: net='__npth__'
        copper.append((rr, net, p.IsOnLayer(pcbnew.F_Cu) or th, p.IsOnLayer(pcbnew.B_Cu) or th))
        if th and p.GetDrillSize().x>0: holes.append((T(p.GetPosition().x),T(p.GetPosition().y),T(max(p.GetDrillSize().x,p.GetDrillSize().y))/2))
    smd=[p for p in pads if p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD]
    if len(smd)>=6:
        cx,cy=T(f.GetPosition().x),T(f.GetPosition().y)
        for p in smd:
            if p.GetNetname() in ('GND','') or p.GetNetname().startswith('unconnected'): continue
            lane_src.append((bb4(p.GetBoundingBox()), cx, cy))
def make_lanes(L):
    out=[]
    for rr,cx,cy in lane_src:
        px,py=(rr[0]+rr[2])/2,(rr[1]+rr[3])/2; w,h=rr[2]-rr[0],rr[3]-rr[1]
        if w<h: dy=1 if py>cy else -1; out.append((rr[0]-0.05, min(py,py+dy*(h/2+L)), rr[2]+0.05, max(py,py+dy*(h/2+L))))
        else:   dx=1 if px>cx else -1; out.append((min(px,px+dx*(w/2+L)), rr[1]-0.05, max(px,px+dx*(w/2+L)), rr[3]+0.05))
    return out
lanes=make_lanes(1.5)
silk+= [('__board__', bb4(d.GetBoundingBox())) for d in b.GetDrawings() if d.GetLayer()==pcbnew.F_SilkS and not (d.GetClass()=='PCB_TEXT' and d.GetText()=='__DEL__')]
def rr_is_label(fr,rr): return False
vias=[]
def ok_via(x,y,ref,strict):
    if not (50.6<x<249.2 and 50.1<y<148.7): return False
    if any(net!='GND' and d_pt_rect(x,y,rr)<VR+CL for rr,net,_,_ in copper): return False
    if any(math.hypot(x-hx,y-hy)<VD/2+hr+HH for hx,hy,hr in holes): return False
    if any(math.hypot(x-vx,y-vy)<VD+HH for vx,vy in vias): return False
    if any(d_pt_rect(x,y,rr)<VR+0.05 for rr in lanes): return False
    if (strict=='short' or strict>=1) and any(fr!=ref and rr[0]<x<rr[2] and rr[1]<y<rr[3] for fr,rr in courts): return False
    if strict=='short':                                   # close to the pad: other parts' outlines and board silk only;
        return not any(fr!=ref and d_pt_rect(x,y,rr)<VR+0.05 for fr,rr in silk)   # labels move out of the way after
    if strict>=1.5 and any(fr!=ref and d_pt_rect(x,y,rr)<VR+0.05 for fr,rr in silk+labels): return False
    if strict>=2 and any(fr==ref and d_pt_rect(x,y,rr)<VR+0.05 for fr,rr in silk+labels): return False
    return True
def ok_track(a,c,w):
    if any(onF and net!='GND' and d_seg_rect(a,c,rr)<w/2+CL for rr,net,onF,_ in copper): return False
    return not any(d_seg_rect(a,c,rr)<w/2+0.05 for rr in lanes)
def snap4(dx,dy): return (1 if dx>0 else -1, 0) if abs(dx)>=abs(dy) else (0, 1 if dy>0 else -1)
todo=[]
for f in fps:
    pads=list(f.Pads())
    for p in pads:
        if p.GetNetname()!='GND' or p.GetAttribute()!=pcbnew.PAD_ATTRIB_SMD or not p.IsOnLayer(pcbnew.F_Cu): continue
        rr=bb4(p.GetBoundingBox())
        if f.GetReference()=='J1' and min(rr[2]-rr[0],rr[3]-rr[1])<0.35: continue
        fine=len([q for q in pads if q.GetAttribute()==pcbnew.PAD_ATTRIB_SMD])>=6 and min(rr[2]-rr[0],rr[3]-rr[1])<0.8
        todo.append((0 if fine else 1, f, p, rr, pads, fine))
todo.sort(key=lambda t:t[0])
def run(todo):
  failed=[]
  for _,f,p,rr,pads,fine in todo:
      ref=f.GetReference(); px,py=(rr[0]+rr[2])/2,(rr[1]+rr[3])/2; w,h=rr[2]-rr[0],rr[3]-rr[1]
      tw=max(0.25,min(0.5,min(w,h)*0.9))
      others=[q for q in pads if q is not p]
      if len(pads)==2:                                         # two-pad part: straight on, away from the other pad
          q=others[0]; ax=snap4(px-T(q.GetPosition().x), py-T(q.GetPosition().y))
      elif fine:                                              # IC pin: straight out along the pin
          fc=((crt(f)[0]+crt(f)[2])/2,(crt(f)[1]+crt(f)[3])/2)
          ax=(1 if px>fc[0] else -1,0) if w>h else (0,1 if py>fc[1] else -1)
      else:
          fc=((crt(f)[0]+crt(f)[2])/2,(crt(f)[1]+crt(f)[3])/2); ax=snap4(px-fc[0],py-fc[1])
      heads=[ax] if fine else [ax,(ax[1],ax[0]),(-ax[1],-ax[0])]
      done=False
      order=[(h,'short') for h in heads]+[(heads[0],st) for st in (2,1.5,1)]+[(h,st) for h in heads[1:] for st in (2,1.5,1)]+[(h,0) for h in heads]
      for (ux,uy),strict in order:
          if True:
              te=(w/2 if ux else h/2)
              for gap in ([0.1+0.1*i for i in range(6)] if strict=='short' else [0.1+0.1*i for i in range(25)]):
                  s=te+gap+VR; x,y=px+ux*s,py+uy*s
                  if ok_via(x,y,ref,strict) and ok_track((px,py),(x,y),tw):
                      v=pcbnew.PCB_VIA(b); v.SetPosition(V(x,y)); v.SetWidth(mm(2*VR)); v.SetDrill(mm(VD)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
                      t=pcbnew.PCB_TRACK(b); t.SetStart(V(px,py)); t.SetEnd(V(x,y)); t.SetWidth(mm(tw)); t.SetLayer(pcbnew.F_Cu); t.SetNet(gnd); b.Add(t)
                      vias.append((x,y)); added.append((ref,p.GetNumber(),(ux,uy)==ax,round(s,2),strict)); done=True; break
              if done: break
          if done: break
      if not done: failed.append((ref,p.GetNumber()))
  return failed
added=[]
failed=run(todo)
lanes=make_lanes(0.6)
failed=run([t for t in todo if (t[1].GetReference(),t[2].GetNumber()) in failed])

moved=[]; stuck=[]
vb=[(x-VR,y-VR,x+VR,y+VR) for x,y in vias]
def lab_free(bx, ref):
    if not (50.4<bx[0] and bx[2]<249.4 and 49.9<bx[1] and bx[3]<148.9): return False
    if any(over(bx,o,0.12) for o in vb): return False
    if any(over(bx,rr,0.12) for rr,net,onF,_ in copper if onF): return False
    if any(over(bx,rr,0.1) for fr,rr in silk+[(fr2,r2) for fr2,r2 in labels if fr2!=ref]): return False
    return not any(fr!=ref and over(bx,rr,0.0) for fr,rr in courts)
for i,(ref,lb) in enumerate(labels):
    if not any(over(lb,o,0.08) for o in vb): continue
    f=F(ref); rt=f.Reference(); l,t,r,bt=crt(f); w_,h_=lb[2]-lb[0],lb[3]-lb[1]; cx_,cy_=(l+r)/2,(t+bt)/2
    cands=[]
    for d in (0.1,0.4,0.8,1.2):
        cands+=[(cx_,t-d-h_/2),(cx_,bt+d+h_/2),(l-d-w_/2,cy_),(r+d+w_/2,cy_)]
    hit=next(((x,y) for x,y in cands if lab_free((x-w_/2,y-h_/2,x+w_/2,y+h_/2), ref)), None)
    if hit: rt.SetPosition(V(*hit)); labels[i]=(ref,(hit[0]-w_/2,hit[1]-h_/2,hit[0]+w_/2,hit[1]+h_/2)); moved.append(ref)
    else: stuck.append(ref)
silk+=labels
# ---- E. + beside every two-pin diode's anode (pad 2), clear of vias, pads and other silk
vbox=[(x-VR,y-VR,x+VR,y+VR) for x,y in vias]
allsilk=[rr for _,rr in silk]+[bb4(t.GetBoundingBox()) for t in grid_plus]
def free(bx, own):
    if not (50.4<bx[0] and bx[2]<249.4 and 49.9<bx[1] and bx[3]<148.9): return False
    if any(over(bx,o,0.12) for o in vbox): return False
    if any(over(bx,rr,0.12) for rr,net,onF,_ in copper if onF): return False
    if any(over(bx,o,0.1) for o in allsilk): return False
    return not any(fr!=own and over(bx,rr,0.0) for fr,rr in courts)
plus_fail=[]
diodes=[f for f in fps if (f.GetReference().startswith('D') or f.GetReference().startswith('LED')) and len(list(f.Pads()))==2
        and f.GetReference() not in ('D1','D2','D3','D4','D5','LED1','LED2','LED3','LED8') and not (f.GetParentGroup() and f.GetParentGroup().GetName()=='MOD support')]
for f in diodes:
    ref=f.GetReference(); an=[p for p in f.Pads() if p.GetNumber()=='2'][0]; ca=[p for p in f.Pads() if p.GetNumber()=='1'][0]
    ax,ay=T(an.GetPosition().x),T(an.GetPosition().y); ux,uy=snap4(ax-T(ca.GetPosition().x), ay-T(ca.GetPosition().y))
    pb=bb4(an.GetBoundingBox()); hw,hh=0.48,0.5; l,t,r,bt=crt(f)
    cands=[]
    for d in (0.1,0.3,0.5):                                 # beside the anode pad, both sides
        if ux: cands+=[(ax, t-d-hh), (ax, bt+d+hh)]
        else:  cands+=[(l-d-hw, ay), (r+d+hw, ay)]
    for d in (0.15,0.4,0.7):                                # or straight on past the anode
        cands.append((ax+ux*((r-ax if ux>0 else ax-l)+d+hw), ay+uy*((bt-ay if uy>0 else ay-t)+d+hh)))
    hit=next(((x,y) for x,y in cands if free((x-hw,y-hh,x+hw,y+hh), ref)), None)
    if hit is None:
        rt=f.Reference(); lb=bb4(rt.GetBoundingBox()); orig=rt.GetPosition(); lw_,lh_=lb[2]-lb[0],lb[3]-lb[1]
        mine=[o for o in allsilk if o==lb]
        for o in mine: allsilk.remove(o)
        for lx,ly in (((l+r)/2,t-0.1-lh_/2),((l+r)/2,bt+0.1+lh_/2),(l-0.15-lw_/2,(t+bt)/2),(r+0.15+lw_/2,(t+bt)/2),((l+r)/2,t-1.3-lh_/2),((l+r)/2,bt+1.3+lh_/2)):
            nb=(lx-lw_/2,ly-lh_/2,lx+lw_/2,ly+lh_/2)
            if not free(nb, ref): continue
            rt.SetPosition(V(lx,ly)); allsilk.append(nb)
            hit=next(((x,y) for x,y in cands if free((x-hw,y-hh,x+hw,y+hh), ref)), None)
            if hit: break
            allsilk.remove(nb); rt.SetPosition(orig)
        if hit is None: allsilk.extend(mine)
    if hit: tt=text('+',hit[0],hit[1],f.GetParentGroup()); allsilk.append(bb4(tt.GetBoundingBox()))
    else: plus_fail.append(ref)
if 'D25' in plus_fail:
    f=F('D25'); l,t,r,bt=crt(f); rt=f.Reference(); h=T(rt.GetBoundingBox().GetHeight()); rt.SetPosition(V((l+r)/2, t-0.02-h/2))
    text('+',(l+r)/2, bt+0.7, f.GetParentGroup()); plus_fail.remove('D25')
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(P,b)
print('vias', len(added), 'not straight-on:', [(a[0],a[1]) for a in added if not a[2]], ' relaxed:', [(a[0],a[1],a[4]) for a in added if a[4]!=2 and a[4]!='short'], ' failed:', failed)
print('+ marks failed:', plus_fail); print('labels moved:', moved, ' label still under a via:', stuck)
