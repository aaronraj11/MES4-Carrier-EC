"""Local nets (short hops between neighbouring parts), hand-routed. Run after route_mcu.py.

    route_local.py <pcb> [group,group,...]

drive: relay CH1-CH4 low-side drive, the same on all four channels (17.6 mm apart). Gate: R9.2 (series from the MCU)
-> Q2.1, with the R10 pull-down tapped by a 45 deg leg past R9.1. Coil drive (0.3 mm): Q2's drain straight east to
the coil's low side K1.2; the flyback diode D10 sits 12 mm north by the coil's high side, boxed in by U2, the shunt
and the K1 load path, so its anode drops by a via off the pad's lower end, runs B.Cu east at y 81.2 and down x 117.44
between K1's pins onto K1.2's through-hole pad.
wingate: winch relay gates (low voltage, kept off the 48 V copper). Q7: R45 (series) straight into the R46 pull-down,
then over R46's GND pad and via to Q7's gate. Q6: R44 (pull-down) straight west into Q6's gate; R43 (series) reaches
R44 over the top, since PA0 comes up into R43 from below and R44's GND via sits between them.
sensors: J10 / J11 SIG -> R24 / R26 -> opto LED (U6 / U7 pin 1), D18 / D19 across it. The opto link (one net) runs
from R24.2 diagonally under R24.1, west below D18's pads into D18.1, and by a 45 deg branch down the inside of U6
(its GND pin sits right above pin 1) into pin 1; the same on R26 / D19 / U7. SENS1 / SENS2 come 48 mm down from the
top edge through the DC-DC area, where U1's output (F.Cu, diagonal to y 85 then west) and U9's feed (B.Cu, diagonal
to y 81 then west) cross every lane west of the modules' pins; east of them only one track per layer fits between
the pin rows (x 199.2 on B.Cu, x 201.72 on F.Cu). SENS1 leaves J10 on B.Cu under SENS1_PWR, runs F.Cu down x 191
and east at y 74.6, then B.Cu down x 199.2; SENS2 runs F.Cu straight down from J11, east at y 73.9 and down x 201.72.
Both come back west on B.Cu at y 97.1 / 97.75 (the one clear row under U9) and up to F.Cu into R24.1 / R26.1 from
above.
leds: each LED resistor's pad 2 sits level with its LED's anode, so a straight F.Cu hop (power LEDs by the IMU switch,
relay LEDs by the output fuses).
usb: the screen's USB-C (J16). CC1 / CC2 sit between the two VBUS pins, whose tracks both fan out into F11 and box
them in on F.Cu, so each leaves by a via off its pad end and runs B.Cu NE to a via beside its 5.1k (CC1 -> R41's east
end, CC2 -> R40's west end, so neither passes the other's via). The shield: the four shell pads tied on B.Cu, and one
0.4 mm F.Cu line over the top of F11 and the CC resistors (crossing the CC lines on the other layer) that comes round
into C37 from the east and on to R42.
guard: analog GND guard on F.Cu around the load-cell block (J12 -> R28 / R29 -> C16-C18 -> D20 / D21 -> C17 / C22 ->
ADS1232, REF / CAP caps, C23-C25). A priority-2 GND zone (above any later general fill) with a 0.3 mm gap so it sits
evenly beside the analog lines, notched out of the ADS1232's digital corner (pins 22-24, R32-R34) and off J3 (CAN cable / shield currents stay out); 40 GND stitching
vias (2 mm grid, at least 0.7 mm from the analog lines, clear of other nets on both layers and of part bodies) tie it
to In1 so the input traces run in a grounded trough.
fill: GND on both outer layers over the whole board, priority 0 (below the 24 V-input pours, raised to 1, and the
analog guard, 2), 0.3 mm gap, thermal reliefs, islands removed; the winch rule area keeps it off the 48 V copper. On F.Cu it
leaves a 0.5 mm moat round the analog guard, so the guard meets the rest of GND only through its vias to In1.
A 5 mm stitching-via grid ties it to In1: worked out at build time, each via clear of other nets on both layers, of
holes and of part bodies, and kept out of the guard, the winch area and the input pours."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from handroute import Board

B = Board(sys.argv[1]); only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
G = {}

G['drive'] = []
for q, d, dy in ((2, 10, 0.0), (3, 11, 17.6), (4, 14, 35.2), (5, 15, 52.8)):
    y = lambda v: round(v + dy, 2)
    G['drive'] += [
        (f'Net-(Q{q}-G)', 0.2, [('F', [(106.39, y(91.82)), (106.39, y(91.50)), (107.41, y(90.48)), (107.41, y(89.82)),
                                       (109.31, y(89.82)), (110.16, y(90.67))])]),
        (f'Net-(D{d}-A)', 0.3, [('F', [(112.03, y(91.62)), (117.44, y(91.62))])]),
        (f'Net-(D{d}-A)', 0.3, [('F', [(109.05, y(79.02)), (109.05, y(80.02))]),
                                ('B', [(109.05, y(80.02)), (110.25, y(81.22)), (116.64, y(81.22)), (117.44, y(82.02)), (117.44, y(91.47))])]),
    ]
G['wingate'] = [
    ('Net-(Q7-G)', 0.2, [('F', [(150.64, 72.34), (152.47, 72.34), (152.47, 71.84), (152.97, 71.34), (156.37, 71.34), (157.02, 71.99),
                                (157.72, 71.99)])]),
    ('Net-(Q6-G)', 0.2, [('F', [(185.90, 73.54), (183.60, 73.54), (183.25, 73.89), (182.60, 73.89)])]),
    ('Net-(Q6-G)', 0.2, [('F', [(189.77, 73.54), (189.77, 73.00), (189.27, 72.50), (186.40, 72.50), (185.90, 73.00), (185.90, 73.54)])]),
]
G['sensors'] = [
    ('/Sensors/SENS1', 0.2, [('B', [(182.99, 55.27), (182.99, 57.60), (183.39, 58.00), (191.00, 58.00)]),
                             ('F', [(191.00, 58.00), (191.00, 74.20), (191.40, 74.60), (199.20, 74.60)]),
                             ('B', [(199.20, 74.60), (199.20, 96.70), (198.80, 97.10), (160.60, 97.10)]),
                             ('F', [(160.60, 97.10), (160.60, 99.50), (158.80, 101.30), (158.80, 103.16)])]),
    ('/Sensors/SENS2', 0.2, [('F', [(195.82, 55.27), (195.82, 56.90), (195.50, 57.22), (195.50, 73.50), (195.90, 73.90), (201.32, 73.90),
                                    (201.72, 74.30), (201.72, 97.75)]),
                             ('B', [(201.72, 97.75), (162.40, 97.75), (162.00, 98.15), (162.00, 115.80)]),
                             ('F', [(162.00, 115.80), (159.20, 115.80), (158.80, 116.20), (158.80, 117.43)])]),
]
for d, dy in ((18, 0.0), (19, 14.27)):                       # opto link: R24.2 -> D18.1, branch -> U6.1
    y = lambda v: round(v + dy, 2)
    n = f'Net-(D{d}-K)'; xd = 153.50 if d == 18 else 153.51
    G['sensors'] += [
        (n, 0.2, [('F', [(160.45, y(103.16)), (160.45, y(103.65)), (158.40, y(105.70)), (xd + 0.50, y(105.70)), (xd, y(105.20)), (xd, y(103.58))])]),
        (n, 0.2, [('F', [(157.90, y(105.70)), (158.40, y(106.20)), (158.40, y(110.42)), (159.10, y(111.12))])]),
    ]
G['leds'] = [(n, 0.2, [('F', [(x0, y), (x1, y)])]) for n, x0, x1, y in (
    ('Net-(LED3-A)', 136.74, 139.58, 64.60), ('Net-(LED8-A)', 136.43, 139.58, 67.50), ('/Main/LED_5V_A', 136.43, 139.58, 70.40),
    ('/Main/LED_3V3_A', 136.43, 139.58, 73.30), ('Net-(LED4-A)', 138.71, 141.16, 79.32), ('Net-(LED5-A)', 138.71, 141.16, 96.92),
    ('Net-(LED6-A)', 138.71, 141.16, 114.52), ('Net-(LED7-A)', 138.71, 141.16, 132.12))]
G['usb'] = [
    ('/AuxPower/SCR_CC1', 0.2, [('F', [(57.68, 131.92), (58.68, 131.92)]), ('B', [(58.68, 131.92), (63.70, 126.90), (72.51, 126.90), (73.30, 127.69)]),
                                ('F', [(73.30, 127.69), (72.58, 127.69)])]),
    ('/AuxPower/SCR_CC2', 0.2, [('F', [(57.68, 132.92), (58.68, 132.92)]), ('B', [(58.68, 132.92), (63.91, 127.69), (70.03, 127.69)]),
                                ('F', [(70.03, 127.69), (70.75, 127.69)])]),
    ('/AuxPower/SCR_SHIELD', 0.4, [('F', [(57.43, 128.10), (57.43, 127.30), (58.53, 126.20), (77.60, 126.20), (78.00, 126.60), (78.00, 128.26),
                                          (77.60, 128.66), (76.75, 128.66), (75.84, 129.57), (74.67, 129.57)])]),
    ('/AuxPower/SCR_SHIELD', 0.4, [('B', [(57.43, 128.10), (53.62, 128.10), (53.62, 136.74), (57.43, 136.74)])]),
]
GUARD = [(90.3, 50.0), (103.0, 50.0), (103.0, 79.3), (96.6, 79.3), (96.6, 84.2), (78.6, 84.2), (78.6, 62.2), (90.3, 62.2)]   # J3 (CAN) corner left out
GUARD_MOAT = [(89.8, 49.5), (103.5, 49.5), (103.5, 79.8), (97.1, 79.8), (97.1, 84.7), (78.1, 84.7), (78.1, 61.7), (89.8, 61.7)]   # GUARD + 0.5
GUARD_VIAS = [(92.2, 50.6), (92.2, 52.6), (92.2, 54.6), (92.2, 56.6), (92.2, 58.6), (92.2, 60.6), (94.2, 60.6), (96.2, 60.6),
              (100.2, 60.6), (79.2, 63.6), (83.2, 63.6), (100.2, 64.6), (102.2, 64.6), (79.2, 65.6), (89.2, 65.6), (98.2, 66.6),
              (100.2, 66.6), (102.2, 66.6), (79.2, 67.6), (85.2, 67.6), (102.2, 68.6), (79.2, 70.6), (79.2, 72.6), (100.2, 73.6),
              (81.2, 74.6), (102.2, 74.6), (100.2, 75.6), (81.2, 76.6), (84.2, 76.6), (87.2, 76.6), (89.2, 76.6), (102.2, 76.6),
              (101.2, 78.6), (79.2, 81.6), (85.2, 81.6), (90.2, 81.6), (89.2, 83.6), (91.2, 83.6), (93.2, 83.6), (95.2, 83.6)]

for k, paths in G.items():
    if only and k not in only: continue
    for net, w, runs in paths: B.path(net, w, runs)
    print(k, len(paths), 'paths')
if not only or 'guard' in only:
    import pcbnew
    b = B.b; mm = pcbnew.FromMM; g = b.FindNet('GND')
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(g); z.SetZoneName('Analog guard'); z.SetAssignedPriority(2)
    z.Outline().NewOutline()
    for x, y in GUARD: z.Outline().Append(mm(x), mm(y))
    z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4)); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)
    for x, y in GUARD_VIAS:
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(g); b.Add(v)
    print('guard zone +', len(GUARD_VIAS), 'vias')
if not only or 'fill' in only:
    import pcbnew, math
    b = B.b; mm = pcbnew.FromMM; T = pcbnew.ToMM; g = b.FindNet('GND'); V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
    outer = (pcbnew.F_Cu, pcbnew.B_Cu)
    for z in b.Zones():                                     # the 24 V-input pours sit above the general fill
        if not z.GetIsRuleArea() and z.GetZoneName() != 'Analog guard' and any(z.IsOnLayer(L) for L in outer):
            z.SetAssignedPriority(max(z.GetAssignedPriority(), 1))
    bb = b.GetBoardEdgesBoundingBox(); x0, y0, x1, y1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
    for L, name in ((pcbnew.F_Cu, 'GND fill F'), (pcbnew.B_Cu, 'GND fill B')):
        z = pcbnew.ZONE(b); z.SetLayer(L); z.SetNet(g); z.SetZoneName(name); z.SetAssignedPriority(0)
        z.Outline().NewOutline()
        for x, y in ((x0 - 1, y0 - 1), (x1 + 1, y0 - 1), (x1 + 1, y1 + 1), (x0 - 1, y1 + 1)): z.Outline().Append(mm(x), mm(y))
        if L == pcbnew.F_Cu:                                # 0.5 mm moat round the analog guard: it reaches GND only by its vias
            h = z.Outline().NewHole()
            for x, y in GUARD_MOAT: z.Outline().Append(mm(x), mm(y), 0, h)
        z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4)); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        b.Add(z)
    for f in b.GetFootprints():                             # U7's GND pad is hemmed in by tracks (one spoke fits): solid
        if f.GetReference() == 'U7':
            for p in f.Pads():
                if p.GetNumber() == '2': p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    for p in b.GetPads():                                   # bare holes (H2-H5, J1 / J4 pegs): every pour and plane 0.4 mm off
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH: p.SetLocalClearance(mm(0.4))   # the wall (JLC: 0.3 inner)
    keep_out = [(GUARD_BOX := (77.6, 49.0, 104.0, 85.2)), (159.1, 0.0, 181.2, 76.9), (203.0, 0.0, 999.0, 76.0)]
    items = [t for t in b.GetTracks() if t.GetNetname() != 'GND' or t.GetClass() == 'PCB_VIA'] + list(b.GetPads())
    for f in b.GetFootprints(): f.BuildCourtyardCaches()
    crt = [f.GetCourtyard(L) for f in b.GetFootprints() for L in outer]
    placed = []; y = y0 + 2.5
    while y < y1 - 2.0:
        x = x0 + 2.5
        while x < x1 - 2.0:
            P = V(x, y); ok = not any(a <= x <= c and bb_ <= y <= d for a, bb_, c, d in keep_out)
            for i in items if ok else []:
                ib = i.GetBoundingBox()
                if not (T(ib.GetLeft()) - 2 < x < T(ib.GetRight()) + 2 and T(ib.GetTop()) - 2 < y < T(ib.GetBottom()) + 2): continue
                if i.GetClass() == 'PCB_VIA':
                    if math.hypot(T(i.GetPosition().x) - x, T(i.GetPosition().y) - y) < 0.3 + T(i.GetWidth()) / 2 + 0.35: ok = False; break
                    continue
                if i.GetNetname() == 'GND' and i.GetClass() == 'PAD' and i.GetDrillSize().x == 0: continue
                need = 0.3 + (0.6 if i.GetClass() == 'PAD' and i.GetDrillSize().x > 0 else 0.3)
                if i.HitTest(P, mm(need)): ok = False; break
            if ok and not any(c.Contains(P) for c in crt if c.OutlineCount()):
                v = pcbnew.PCB_VIA(b); v.SetPosition(P); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(g); b.Add(v); placed.append((x, y))
            x += 5.0
        y += 5.0
    print('GND fill F / B +', len(placed), 'stitching vias')
B.save()
