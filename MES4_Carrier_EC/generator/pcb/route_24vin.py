"""24 V input: F.Cu pours J5 -> F1 -> Q1 -> +24V, Q1 drain copper on F/B.Cu with thermal vias,
+24V via field into In2, GND pour + via field at J5 pin 2, gate tracks R6 -> D8 -> Q1."""
import sys, pcbnew
P=sys.argv[1]; b=pcbnew.LoadBoard(P); mm=pcbnew.FromMM; V=lambda x,y: pcbnew.VECTOR2I(mm(x),mm(y))
FULL=pcbnew.ZONE_CONNECTION_FULL
def zone(net, layer, pts, name):
    z=pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet(net)); z.SetZoneName(name)
    o=z.Outline(); o.NewOutline()
    for x,y in pts: o.Append(mm(x),mm(y))
    z.SetPadConnection(FULL); z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25))
    z.SetIsFilled(False); b.Add(z)
def via(net,x,y,d=0.8,h=0.4):
    v=pcbnew.PCB_VIA(b); v.SetPosition(V(x,y)); v.SetWidth(mm(d)); v.SetDrill(mm(h)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)
def track(net,pts,w):
    for a,c in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(b.FindNet(net)); b.Add(t)
F,B=pcbnew.F_Cu,pcbnew.B_Cu
IN,FU='/Power/+24V_IN','/Power/+24V_F'
zone(IN,F,[(225.7,59.5),(234.9,59.5),(234.9,66.4),(230.5,66.4),(230.5,72.5),(221.4,72.5),(221.4,65.7),(225.7,65.7)],'24V IN')
zone(FU,F,[(212.3,57.9),(225.2,57.9),(225.2,65.2),(220.9,65.2),(220.9,74.2),(212.3,74.2)],'24V FUSED F')
zone(FU,B,[(212.3,57.9),(229.5,57.9),(229.5,74.5),(212.3,74.5)],'24V FUSED B')
zone('+24V',F,[(204.5,66.2),(211.8,66.2),(211.8,74.2),(204.5,74.2)],'24V OUT')
zone('GND',F,[(235.3,57.5),(248.7,57.5),(248.7,74.5),(235.3,74.5)],'GND IN F')
zone('GND',B,[(234.2,57.5),(248.7,57.5),(248.7,74.5),(234.2,74.5)],'GND IN B')
for y in (58.9,60.7):                                   # Q1 drain: thermal vias above the tab and F1
    for x in (213.6,215.6,217.6,219.6,221.6,223.6): via(FU,x,y)
for y in (70.2,72.2):                                   # Q1 drain: below the tab
    for x in (213.6,215.6,217.6,219.6): via(FU,x,y)
for y in (69.8,71.6,73.4):                              # Q1 source: +24V field into In2
    for x in (205.3,207.1,208.9,210.7): via('+24V',x,y)
for y in (61.5,64.5,67.5):                              # J5 pin 2: GND field into In1 / B.Cu
    for x in (241.0,243.0,245.0,247.0): via('GND',x,y)
track('Net-(D8-A)',[(203.57,64.60),(204.40,63.77),(206.75,63.77)],0.3)
track('Net-(D8-A)',[(206.75,63.77),(207.37,63.15),(210.53,63.15)],0.3)
for p in b.FindFootprintByReference('J5').Pads():
    if p.GetNumber() in ('1','2'): p.SetLocalZoneConnection(FULL)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P,b)
