"""Relay load paths CH1-CH4 (Out_3A, 1.5 mm, 45-degree bends only): shunt -> COM, NO -> fuse,
fuse -> TVS / LED resistor -> output. Every output drops through a diagonal via pair to B.Cu:
CH1 up the x 132.8 column to J6, CH2-CH4 in lanes up to J7-J9."""
import sys, pcbnew
P=sys.argv[1]; b=pcbnew.LoadBoard(P); mm=pcbnew.FromMM; V=lambda x,y: pcbnew.VECTOR2I(mm(x),mm(y))
W=1.5
def track(net,pts,layer=pcbnew.F_Cu,w=W):
    for a,c in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)
def via(net,x,y):
    v=pcbnew.PCB_VIA(b); v.SetPosition(V(x,y)); v.SetWidth(mm(0.8)); v.SetDrill(mm(0.4)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)
Bc=pcbnew.B_Cu
CH=[(1,0.0,'/Relays1-2/RLY1_OUT','U2','F3'),(2,17.6,'/Relays1-2/RLY2_OUT','U3','F4'),
    (3,35.2,'/Relays3-4/RLY3_OUT','U4','F5'),(4,52.8,'/Relays3-4/RLY4_OUT','U5','F6')]
for n,dy,out,u,fu in CH:
    track(f'Net-({u}-IN-)',[(111.89,86.89+dy),(114.03,86.89+dy),(115.50,85.42+dy)])   # shunt -> COM
    track(f'Net-({fu}-Pad1)',[(129.65,91.47+dy),(137.90,91.47+dy)])                    # NO -> fuse
    yF=84.70+dy
    track(out,[(137.90,yF),(142.12,yF),(143.50,yF+1.38)])                              # fuse -> TVS, 45 deg into the pad
    track(out,[(135.78,yF),(135.78,79.32+dy)])                                          # fuse -> LED resistor
# CH1 output: via pair on the LED-resistor branch below R14, B.Cu up the column left of the LED resistors
# (keeps F.Cu free above the relays for the rails and the MCU signals going east)
a,c=(135.78,82.60),(134.78,81.60)
track(CH[0][2],[a,c]); via(CH[0][2],*a); via(CH[0][2],*c)
track(CH[0][2],[a,c,(134.78,76.40),(132.83,74.45),(132.83,55.27)],Bc)
# CH2-CH4: F.Cu on from the TVS tee to a via pair on a 45-degree line, B.Cu lane up, fan out to the terminal
lanes={2:146.1,3:147.9,4:149.7}
fan={2:[(146.1,60.10),(142.16,56.16),(142.16,55.27)],
     3:[(147.9,60.90),(151.49,57.31),(151.49,55.27)],
     4:[(149.7,66.00),(152.5,63.20),(158.0,63.20),(160.83,60.37),(160.83,55.27)]}
for n,dy,out,u,fu in CH[1:]:
    yF=84.70+dy; x=lanes[n]; a=(x-1.0,yF); c=(x,yF-1.0)
    track(out,[(142.12,yF),a,c]); via(out,*a); via(out,*c)
    track(out,[a,c]+fan[n],Bc)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P,b)
