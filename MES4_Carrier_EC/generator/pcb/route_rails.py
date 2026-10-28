"""Supply rails, hand-routed: every path below is placed by hand (45-degree bends only, one width per
run, width changes only at a pad or via). Run after route_relays.py and route_srv_scr.py.

    route_rails.py <pcb> [group,group,...]

A path is (net, width, runs); runs = [('F'|'B', [(x, y), ...]), ...]. A via joins consecutive runs at the
last point of a run; a run with a single point only places that via. A route that ends on the middle of
another track gets a vertex there (KiCad wants an anchor)."""
import sys, math, pcbnew

P = sys.argv[1]; only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
b = pcbnew.LoadBoard(P); mm = pcbnew.FromMM; T = pcbnew.ToMM; V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
LAY = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}
added = []

def path(net, w, runs):
    ni = b.FindNet(net)
    for k, (lc, pts) in enumerate(runs):
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(w)); t.SetLayer(LAY[lc]); t.SetNet(ni); b.Add(t); added.append(t)
        if k < len(runs) - 1:
            v = pcbnew.PCB_VIA(b); v.SetPosition(V(*pts[-1])); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(ni); b.Add(v)

def d_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)

def split_tees():
    for t0 in added:
        for q in (t0.GetStart(), t0.GetEnd()):
            px, py = T(q.x), T(q.y)
            for t in list(b.GetTracks()):
                if t.GetClass() != 'PCB_TRACK' or t is t0 or t.GetLayer() != t0.GetLayer() or t.GetNetname() != t0.GetNetname(): continue
                a, c = t.GetStart(), t.GetEnd(); ax, ay, cx, cy = T(a.x), T(a.y), T(c.x), T(c.y)
                if min(math.hypot(px - ax, py - ay), math.hypot(px - cx, py - cy)) < 0.005 or d_seg(px, py, ax, ay, cx, cy) > 0.005: continue
                n = pcbnew.PCB_TRACK(b); n.SetStart(q); n.SetEnd(c); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNet(t.GetNet())
                t.SetEnd(q); b.Add(n); break

DC, AUX, P5, P524, P33 = '/Power/+24V_DC', '/AuxPower/+24V_AUX', '+5V', '+5V_24', '+3V3_MOD'
G = {}

# +24V_DC / +24V_AUX: L -> over the bulk cap's GND pad -> bulk cap -> through the small cap -> under the module's GND pin -> module input
G['dc'] = [
    (DC, 1.0, [('F', [(160.53, 80.88), (162.72, 78.68), (169.06, 78.68), (171.26, 80.88)])]),
    (DC, 1.0, [('F', [(171.26, 80.88), (172.36, 79.78), (180.84, 79.78), (181.64, 80.58), (186.01, 80.58), (187.75, 78.83)])]),
]
G['aux'] = [
    (AUX, 1.0, [('F', [(160.53, 93.32), (162.72, 91.12), (169.06, 91.12), (171.26, 93.32)])]),
    (AUX, 1.0, [('F', [(171.26, 93.32), (172.81, 91.77), (180.84, 91.77), (181.64, 92.57), (186.01, 92.57), (187.75, 90.82)])]),
    (AUX, 1.0, [('F', [(171.26, 93.32), (171.26, 104.04), (171.26, 114.13), (179.62, 114.13), (181.99, 116.50)])]),   # C30, C27 -> U10
]

# +5V_24: U1 -> C6 -> trunk (over C7's pad) -> K1; coil chain K1-K4 beside the coil pins; flyback diodes; module 5 V fuse F2
G['5v24'] = [
    (P524, 1.0, [('F', [(197.91, 78.83), (191.85, 84.89), (180.84, 84.89)])]),
    (P524, 1.0, [('F', [(180.84, 84.89), (152.04, 84.89), (144.20, 77.05), (119.86, 77.05), (117.44, 79.47)])]),
    (P524, 1.0, [('F', [(117.44, 79.47), (119.64, 81.67), (119.64, 94.87), (117.44, 97.07), (119.64, 99.27), (119.64, 112.47),
                        (117.44, 114.67), (119.64, 116.87), (119.64, 130.07), (117.44, 132.27)])]),
] + [(P524, 0.5, [('F', [(112.34, yd), (116.99, yd), (117.44, yd + 0.45)])]) for yd in (79.02, 96.62, 114.22, 131.82)] + [
    (P524, 1.0, [('F', [(102.12, 72.30), (107.32, 77.50), (110.82, 77.50), (112.34, 79.02)])]),                      # F2 -> D10, over D10's anode pad
    # winch coils: coil <-> diode on F.Cu, a via off each diode's pad end, B.Cu feed from U1 pin 6 (nothing under the 48 V pads)
    (P524, 0.5, [('F', [(180.00, 64.15), (181.89, 64.15), (183.24, 65.50)])]),
    (P524, 0.5, [('F', [(157.08, 68.80), (158.97, 68.80), (160.32, 70.15)])]),
    (P524, 0.5, [('F', [(183.24, 65.50), (183.24, 64.65)]), ('B', [(183.24, 64.65)])]),
    (P524, 0.5, [('F', [(157.08, 68.80), (157.08, 69.65)]), ('B', [(157.08, 69.65), (161.08, 73.65), (178.08, 73.65), (183.24, 68.49), (183.24, 64.65)])]),
    (P524, 0.5, [('B', [(197.91, 78.83), (189.51, 70.43), (181.30, 70.43)])]),                                    # tees into the diagonal
]

# module 5 V: F2 -> FB1 -> via -> B.Cu under the ADC / J1 -> via under J1 pin 22 (pin 20 at 45 deg); C8 / C9 on B.Cu below the
# pin 2-10 escapes; FB2 (load-cell excitation) fed over the top on B.Cu so nothing crosses the load-cell inputs; 5V LED R1
G['mod5v'] = [
    ('Net-(F2-Pad2)', 0.8, [('F', [(104.92, 72.30), (107.10, 72.30), (107.38, 72.02)])]),
    (P5, 0.8, [('F', [(109.50, 72.02), (110.34, 72.02)]), ('B', [(110.34, 72.02), (109.94, 72.02), (83.34, 98.62), (83.34, 105.46), (84.55, 106.67)])]),
    (P5, 0.3, [('F', [(84.55, 105.40), (84.55, 106.67)]), ('B', [(84.55, 106.67)])]),
    (P5, 0.3, [('F', [(84.05, 105.40), (84.05, 106.17), (84.55, 106.67)])]),
    (P5, 0.8, [('F', [(75.25, 110.56), (75.25, 109.66)]), ('B', [(75.25, 109.66)])]),
    (P5, 0.5, [('F', [(75.25, 116.77), (75.25, 116.09)]), ('B', [(75.25, 116.09)])]),
    (P5, 0.8, [('B', [(84.55, 106.67), (84.55, 107.50), (82.39, 109.66), (75.25, 109.66)])]),
    (P5, 0.8, [('B', [(75.25, 116.09), (74.25, 115.09), (74.25, 110.66), (75.25, 109.66)])]),
    (P5, 0.5, [('F', [(110.34, 72.02), (110.84, 71.52), (110.84, 62.80)]), ('B', [(110.84, 62.80), (84.95, 62.80), (84.25, 63.50)]),
               ('F', [(84.25, 63.50), (84.25, 64.50)])]),
    (P5, 0.5, [('F', [(135.41, 70.40), (112.46, 70.40), (110.84, 68.78)])]),
]

# IMU 9 V: U9 -> C29; U9 -> SW2 (F.Cu between the LED rows and across the relay lanes, B.Cu below the winch relays); SW2 -> J14, 9V LED
G['imu'] = [
    ('/AuxPower/+9V_IMU', 0.5, [('F', [(197.91, 90.82), (191.15, 97.58), (180.84, 97.58)])]),
    ('/AuxPower/+9V_IMU', 0.5, [('F', [(122.00, 66.73), (124.00, 68.73), (155.00, 68.73), (157.21, 70.94)]),
                                ('B', [(157.21, 70.94), (167.41, 81.14), (188.23, 81.14), (197.91, 90.82)])]),
    ('/AuxPower/IMU_9V', 0.5, [('F', [(126.80, 66.73), (126.80, 58.58), (123.49, 55.27)])]),
    ('/AuxPower/IMU_9V', 0.3, [('F', [(135.41, 67.50), (127.56, 67.50), (126.80, 66.74)])]),
]

# servo 5 V: F10 -> C36 (0.5), F10 -> J17 pin 2 (0.8) along the bottom
G['srv5'] = [
    ('/AuxPower/+5V_SRV', 0.5, [('F', [(195.71, 145.15), (198.23, 145.15)])]),
    ('/AuxPower/+5V_SRV', 0.8, [('F', [(195.71, 145.15), (196.71, 146.15), (218.65, 146.15), (224.04, 140.76)])]),
]

# sensor supplies: fuse -> terminal straight up, decoupling cap at 45 deg
G['sens'] = [
    ('/Sensors/SENS1_PWR', 0.3, [('F', [(186.49, 64.42), (186.49, 55.27)])]),
    ('/Sensors/SENS1_PWR', 0.3, [('F', [(189.10, 65.80), (187.72, 64.42), (186.49, 64.42)])]),
    ('/Sensors/SENS2_PWR', 0.3, [('F', [(199.32, 64.42), (199.32, 55.27)])]),
    ('/Sensors/SENS2_PWR', 0.3, [('F', [(196.40, 65.80), (197.78, 64.42), (199.32, 64.42)])]),
]

# +3V3_MOD (0.3): B.Cu between areas, F.Cu only locally
G['3v3'] = [
    # J1 pin 4 -> via -> B.Cu under J1 -> via off J2 pin 3
    (P33, 0.3, [('F', [(80.05, 105.40), (80.05, 106.50), (79.55, 107.00)]), ('B', [(79.55, 107.00), (79.55, 105.20), (81.58, 103.17), (81.58, 87.44)]),
                ('F', [(81.58, 87.44), (81.58, 89.23)])]),
    # ADC: pins 19 / 20 tied; via off pin 19 -> B.Cu to the J2 line; via off pin 1 -> B.Cu to pin 19's via; C25 by a via
    (P33, 0.3, [('F', [(95.53, 80.33), (96.18, 80.33)])]),
    (P33, 0.3, [('F', [(95.53, 80.33), (95.53, 81.47)]), ('B', [(95.53, 81.47), (94.73, 80.67), (89.53, 80.67), (81.58, 88.62)])]),
    (P33, 0.3, [('F', [(98.78, 74.61), (98.78, 73.60), (99.38, 73.00)]), ('B', [(99.38, 73.00), (99.38, 74.15), (95.53, 78.00), (95.53, 81.47)])]),
    (P33, 0.3, [('F', [(87.84, 82.89), (88.52, 82.89)]), ('B', [(88.52, 82.89), (87.31, 82.89)])]),
    # INA236s: cap -> VS over the top of the IC; U3 A0 = VS; a via beside each cap; B.Cu spine x 103.38
    *[(P33, 0.3, [('F', [(104.06, y), (104.06, y - 0.40), (106.26, y - 2.60), (108.77, y - 2.60), (109.50, y - 1.87)])]) for y in (86.32, 103.92, 121.52, 139.12)],
    (P33, 0.3, [('F', [(106.89, 103.35), (106.07, 103.35), (105.82, 103.10), (104.48, 103.10)])]),
    *[(P33, 0.3, [('F', [(104.06, y), (103.38, y)]), ('B', [(103.38, y)])]) for y in (86.32, 103.92, 121.52, 139.12)],
    (P33, 0.3, [('B', [(103.38, 86.32), (103.38, 139.12)])]),
    (P33, 0.3, [('B', [(103.38, 86.32), (103.38, 80.12), (112.42, 71.08)])]),
    # B.Cu bus north of FB1's via: ADC pin 1 <-> via off R3
    (P33, 0.3, [('F', [(118.99, 73.00), (118.99, 72.28)]), ('B', [(118.99, 72.28), (117.79, 71.08), (101.30, 71.08), (99.38, 73.00)])]),
    # pull-up rail above R3 / R4 / R5 (their I2C / PA15 pads stay open from below) -> 3V3 LED R2
    (P33, 0.3, [('F', [(118.99, 72.60), (119.39, 72.20), (134.31, 72.20), (135.41, 73.30)])]),
    (P33, 0.3, [('F', [(121.59, 73.00), (121.59, 72.60), (121.99, 72.20)])]),
    (P33, 0.3, [('F', [(124.20, 73.00), (124.20, 72.60), (124.60, 72.20)])]),
    # optos -> R2: F.Cu east of the relay lanes, B.Cu hop under the +5V_24 trunk, across the lanes above the relays
    (P33, 0.3, [('F', [(150.39, 111.12), (152.59, 113.32), (152.59, 123.19), (150.39, 125.39)])]),
    (P33, 0.3, [('F', [(150.39, 111.12), (152.59, 108.92), (152.59, 86.30)]), ('B', [(152.59, 86.30), (152.59, 83.50)]),
                ('F', [(152.59, 83.50), (143.59, 74.50), (136.61, 74.50), (135.41, 73.30)])]),
    # servo UART pull-ups -> U7
    (P33, 0.3, [('F', [(193.05, 133.63), (193.05, 139.30)])]),
    (P33, 0.3, [('F', [(193.05, 133.63), (158.63, 133.63), (150.39, 125.39)])]),
]

# test points (bottom row, 0.3): straight up on F.Cu over the screen trunk, a via, B.Cu columns north
G['tp'] = [
    (DC, 0.3, [('F', [(154.50, 147.20), (154.50, 141.80)]), ('B', [(154.50, 141.80), (154.50, 88.10), (161.72, 80.88)]),
               ('F', [(161.72, 80.88), (160.53, 80.88)])]),                                                         # TP2 -> via off L1 pin 2
    (P524, 0.3, [('F', [(161.50, 147.20), (161.50, 143.80), (159.50, 141.80)]), ('B', [(159.50, 141.80), (159.50, 84.89)]),
                 ('F', [(159.50, 84.89)])]),                                                                         # TP3 -> via on the trunk
    (P33, 0.3, [('F', [(175.50, 147.20), (175.50, 135.13), (177.00, 133.63)])]),                                    # TP5
    ('/AuxPower/+9V_IMU', 0.3, [('F', [(182.50, 147.20), (182.50, 144.50), (179.80, 141.80)]),
                                ('B', [(179.80, 141.80), (179.80, 99.52), (180.84, 98.48)]), ('F', [(180.84, 98.48), (180.84, 97.58)])]),   # TP8
    (P5, 0.3, [('F', [(168.50, 147.20), (166.90, 148.80), (95.60, 148.80), (93.60, 146.80), (93.60, 115.72), (84.55, 106.67)])]),    # TP4: bottom edge, under the module
]

for k, paths in G.items():
    if only and k not in only: continue
    for net, w, runs in paths: path(net, w, runs)
    print(k, len(paths), 'paths')
split_tees()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
