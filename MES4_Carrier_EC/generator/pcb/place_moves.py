"""Placement moves made for routing (user-approved 2026-10-28). Run first in the routing chain.

R3 / R4 / R5 (I2C SDA / SCL and PA15 pull-ups) leave their spot by the IMU switch, where the tracks around FB1,
F2, D10 and K1 boxed them in: they stack just above U2 (INA236), signal pads west toward the I2C bus, 3V3 pads
east over U2's VS link, 1.25 mm apart so their refs (1 mm, the board minimum) fit west of each row.
D4 / D5 (VCP ESD) leave the ADC-control lane between D3 and the INA236 column: they sit side by side above J2's
left column (courtyards touching), between the CAN bus and C23, refs above their GND vias. Their GND vias move
with them.
MCU escape (west corner): D1 / D2 (SWDIO / SWCLK ESD) swap places so each meets its net's lane out of J2's
inter-row channel without a crossing. Three GND vias leave the J1 / J2 corridor: J1's tab via goes to the tab's
west end, SW1 pin 2's via to the pad's inner end, J1 pin 10's via to the finger's outer end (frees pin 8's escape).
MCU escape (ADC lane, user-approved): R32 / R33 / R34 move off the row under U8, where R32 blocked pins 22 / 23. PA6,
PA5 and LC_DOUT now drop straight from U8 pins 22-24: R34 (PA6 pull-down) sits on PA6's line, R33 (PA5) on PA5's
with its GND via east, R32 (DOUT -> PA4) stands upright east of them so PA4 leaves on the east side, in J1's order.
J16 (screen USB-C, review B2): its mouth sat 1.13 mm inside the board edge (3D model front at x 51.03, edge 49.9), so
a cable's overmould would hit the board before the plug seats. It moves 1.25 mm west (mouth 0.12 mm past the edge)
with its pad stubs and GND vias; route_srv_scr.py / route_local.py start J16's tracks 1.25 mm further west."""
import sys, pcbnew

P = sys.argv[1]; b = pcbnew.LoadBoard(P); mm, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
MOVES = {'R5': (105.00, 80.75, 180), 'R4': (105.00, 82.00, 180), 'R3': (105.00, 83.25, 180),
         'D4': (74.00, 84.90, 90), 'D5': (76.00, 84.90, 90), 'D1': (86.94, 91.27, 180), 'D2': (86.94, 88.07, 180),
         'R32': (100.50, 83.21, 270), 'R33': (98.64, 84.40, 0), 'R34': (96.97, 82.40, 180)}
REFS = {'R5': (103.85, 80.75, 1.0), 'R4': (103.85, 82.00, 1.0), 'R3': (103.85, 83.25, 1.0),   # right-justified
        'D4': (74.00, 82.10, 1.0, 'C'), 'D5': (76.00, 82.10, 1.0, 'C'),
        'R32': (100.50, 81.60, 1.0, 'C'), 'R33': (98.90, 85.70, 1.0, 'C'), 'R34': (95.85, 83.60, 1.0, 'C')}
OLD_GND_VIAS = [(92.23, 88.07), (92.23, 91.27), (93.96, 83.61), (89.73, 82.89)]   # D4 / D5 / R33 / R34 pad 2 vias at the old spot
NEW_GND = {'D4': ((0, -1), 0.4), 'D5': ((0, -1), 0.4), 'R34': ((-1, 0), 0.49), 'R33': ((1, 0), 0.49)}   # pad 2's end, stub width
VIA_MOVES = {(78.20, 96.85): (77.20, 98.63), (75.25, 96.89): (75.25, 98.91), (81.55, 104.27): (81.55, 106.575),
             (87.30, 98.98): (87.30, 96.685)}   # J1 pin 33: frees PA8 / PA7's south escapes
SHIFTS = {'J16': ((-1.25, 0.0), (50.0, 126.5, 59.5, 138.0))}   # ref: (dx, dy), box of the tracks / vias that go along
VIA_BENDS = {(85.80, 98.98): ((85.80, 99.20), (85.30, 99.70))}   # J1 pin 27 (its north end sits on the +5V B.Cu diagonal): via SW,
                                                                 # behind the unused pin 25, frees PC6's escape

fps = {f.GetReference(): f for f in b.GetFootprints()}       # look up before removing anything (SWIG loses the type after Remove)
for ref, (x, y, rot) in MOVES.items():
    f = fps[ref]; f.SetPosition(V(x, y)); f.SetOrientationDegrees(rot)
    if ref not in REFS: continue                            # the ref keeps its offset
    t = f.Reference(); (rx, ry, h, *j) = REFS[ref]; t.SetTextAngleDegrees(0); t.SetPosition(V(rx, ry))
    t.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h))); t.SetTextThickness(mm(0.15 * h))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER if j else pcbnew.GR_TEXT_H_ALIGN_RIGHT)
old = [t for t in b.GetTracks() if t.GetNetname() == 'GND' and any(
       abs(T(p.x) - x) < 0.01 and abs(T(p.y) - y) < 0.01
       for p in ([t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]) for x, y in OLD_GND_VIAS)]
for ref, ((dx, dy), w) in NEW_GND.items():                 # GND via straight off pad 2's end, gap 0.1
    p = next(p for p in fps[ref].Pads() if p.GetNumber() == '2'); bb = p.GetBoundingBox()
    x, y = T(p.GetPosition().x), T(p.GetPosition().y); g = b.FindNet('GND')
    hw, hh = T(bb.GetWidth()) / 2, T(bb.GetHeight()) / 2
    vx, vy = round(x + dx * (hw + 0.4), 2), round(y + dy * (hh + 0.4), 2)
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(x, y)); t.SetEnd(V(vx, vy)); t.SetWidth(mm(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(g); b.Add(t)
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(vx, vy)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(g); b.Add(v)
for ref, ((dx, dy), (x0, y0, x1, y1)) in SHIFTS.items():  # rigid moves: the part and its stubs / vias
    d = V(dx, dy); fps[ref].Move(d)
    for t in b.GetTracks():
        pts = [t.GetPosition()] if t.GetClass() == 'PCB_VIA' else [t.GetStart(), t.GetEnd()]
        if all(x0 < T(p.x) < x1 and y0 < T(p.y) < y1 for p in pts): t.Move(d)
for t in b.GetTracks():                                    # GND via moves: the via and its stub's end
    for (ox, oy), (nx, ny) in VIA_MOVES.items():
        hit = lambda p: abs(T(p.x) - ox) < 0.01 and abs(T(p.y) - oy) < 0.01
        if t.GetClass() == 'PCB_VIA':
            if hit(t.GetPosition()): t.SetPosition(V(nx, ny))
        elif hit(t.GetEnd()): t.SetEnd(V(nx, ny))
        elif hit(t.GetStart()): t.SetStart(V(nx, ny))
for t in list(b.GetTracks()):                              # GND via bends: stub to the bend, a 45 deg leg on to the moved via
    for (ox, oy), ((mx, my), (nx, ny)) in VIA_BENDS.items():
        hit = lambda p: abs(T(p.x) - ox) < 0.01 and abs(T(p.y) - oy) < 0.01
        if t.GetClass() == 'PCB_VIA':
            if hit(t.GetPosition()): t.SetPosition(V(nx, ny))
        elif hit(t.GetEnd()):
            t.SetEnd(V(mx, my)); n = pcbnew.PCB_TRACK(b); n.SetStart(V(mx, my)); n.SetEnd(V(nx, ny))
            n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNet(t.GetNet()); b.Add(n)
# J1's fused GND fingers: the bars sat just past the finger ends with a stub from every finger teeing in at 90 deg.
# Restyled as a 0.3 mm bar through the finger ends with a vertex inside every finger, so every joint is inside a pad;
# the vias and their stubs stay where they were (bottom row pins 24-74, top row pins 65-75).
BARS = [((85.0, 97.7), (103.6, 105.5), [round(85.05 + 0.5 * k, 2) for k in range(26)], 104.75, 103.77,
         (85.05, 87.55, 90.05, 92.55, 95.05, 97.05), 85.10),
        ((95.1, 98.0), (97.8, 99.6), [round(95.30 + 0.5 * k, 2) for k in range(6)], 98.50, 99.48, (95.30, 97.80), 95.35)]
for (x0, x1), (y0, y1), xs, yb, yv, vx, xstart in BARS:
    inside = lambda p: x0 <= T(p.x) <= x1 and y0 <= T(p.y) <= y1
    for t in [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'GND'
              and inside(t.GetStart()) and inside(t.GetEnd())]: old.append(t)
    g = b.FindNet('GND'); pts = [(xstart, yb)] + [(x, yb) for x in xs if x > xstart]
    def seg(a, c):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(0.3)); t.SetLayer(pcbnew.F_Cu); t.SetNet(g); b.Add(t)
    for a, c in zip(pts, pts[1:]): seg(a, c)
    for x in vx: seg((x, yb), (x, yv))
for t in old: b.Remove(t)                                   # drop the old GND via stubs and vias
pcbnew.SaveBoard(P, b)
for ref in MOVES:
    f = fps[ref]
    print(ref, [(p.GetNumber(), round(T(p.GetPosition().x), 2), round(T(p.GetPosition().y), 2), p.GetNetname()) for p in f.Pads()])
