"""Servo +24V_SRV and screen +5V_SCR / VBUS_SCR. 45-degree bends only; one width per run, width
changes only at pads (F.Cu bus over the screen caps' pads instead of stubs)."""
import sys, pcbnew
P=sys.argv[1]; b=pcbnew.LoadBoard(P); mm=pcbnew.FromMM; V=lambda x,y: pcbnew.VECTOR2I(mm(x),mm(y))
F,Bc=pcbnew.F_Cu,pcbnew.B_Cu
def track(net,pts,w,layer=F):
    for a,c in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(b.FindNet(net)); b.Add(t)
def via(net,x,y):
    v=pcbnew.PCB_VIA(b); v.SetPosition(V(x,y)); v.SetWidth(mm(0.8)); v.SetDrill(mm(0.4)); v.SetLayerPair(F,Bc); v.SetNet(b.FindNet(net)); b.Add(v)
SRV,SCR,VB='/AuxPower/+24V_SRV','/AuxPower/+5V_SCR','/AuxPower/VBUS_SCR'
# servo 24 V (1.5): F9 -> J15 above J17, C31 off a 45-degree branch; F9 -> C32 bulk
track(SRV,[(212.66,135.66),(232.72,135.66),(235.79,135.66),(236.79,136.66),(236.79,140.76)],1.5)
track(SRV,[(232.72,135.66),(234.52,133.86)],1.5)
track(SRV,[(212.66,137.90),(212.66,139.30),(211.66,140.30),(207.02,140.30),(206.02,141.30),(206.02,143.73)],1.5)
# screen 5 V (2.0): U10 pin 4 -> F.Cu bus running over the + pads of C35 / C33 / C34 -> C38
track(SCR,[(202.31,124.12),(199.38,127.05),(170.50,127.05),(169.00,125.55),(169.00,123.36)],2.0)
# B.Cu trunk: U10 pin 4 -> above the TP row -> below H1 / K4 -> TP9
track(SCR,[(202.31,124.12),(198.50,127.93),(198.50,142.60),(197.50,143.60),(152.40,143.60),(148.10,147.90),
           (64.82,147.90),(63.82,146.90),(63.82,142.75)],2.0,Bc)
via(SCR,192.91,143.78); track(SCR,[(192.91,145.15),(192.91,143.78)],1.0)   # F10 tap: via off the pad end, onto the trunk
track(SCR,[(63.82,142.75),(63.22,142.15),(63.22,135.25)],2.0)               # TP9 -> F11
# VBUS: one 0.7 track per J16 VBUS pad straight from F11 (J16's pads are 0.7 mm on a 1 mm pitch)
track(VB,[(57.68,130.92),(58.90,130.92),(60.90,128.92)],0.7)                                   # B9
track(VB,[(57.68,133.92),(59.10,133.92),(60.30,132.72),(60.30,131.12),(61.60,129.82),(61.60,129.00)],0.7)  # A9
track(VB,[(65.30,129.00),(66.60,130.30),(66.60,131.60),(67.57,132.57),(68.24,132.57)],1.0)    # TVS D22
track(VB,[(68.60,132.57),(70.00,132.57),(70.75,131.82),(70.75,128.71)],0.3)                   # CC pull-ups
track(VB,[(70.75,131.82),(72.58,129.99),(72.58,128.71)],0.3)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P,b)
