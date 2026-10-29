"""Silkscreen tidy, run last (after teardrops.py).

    silk.py <pcb>

- Remove the 0.12 mm pin-1 dots (radius 0.03, 0.06 stroke) the footprints carry: far below JLC's 0.15 mm minimum, so
  they never print, and they sat on the board edge / on J1's pad (12 of the old DRC notes). Every part they marked has
  its orientation shown otherwise (printed pin labels, a key, or a filled pin-1 dot).
- Widen every silk stroke under 0.15 mm (KiCad's library 0.12 mm outlines, test-point rings) to 0.15 mm.
- Move the reference labels that crowded each other, sat on another part's pads / outline, or sat on a via, to a clear
  spot next to their part (found with generator/pcb/silk_audit.py and a candidate search; text size stays 1 mm, the
  board minimum). Angle None keeps the label's angle.
- Put the 19 references the footprints kept on F.Fab only (J5, SW2, the test points, the standoffs, the power-LED
  column) on the silkscreen. The power LEDs are packed between their resistors and the 24V / 9V / 5V / 3V3 tags, so
  the tags step 0.5 mm left and each LED's reference sits right of its tag, in the LED's row. H2-H5 are bare mounting
  holes and stay unlabelled.
- "5V LOAD CELL" (review M2): J12 / J13's name cells ("LOAD CELL SIG" / "LOAD CELL EXC") merge into one cell across
  both terminals; the pin rows above still name SIG+ / SIG- / EXC+ / EXC- / SHLD.
- "CANBUS" knockout (review L5) along J4's RJ45 bank, 1 mm like the board's other knockouts, in the clear strip between
  the bank's outline and J2 / SW1, between two shield pins (found with a clear-spot search: pads, vias, silk).
- Drop the GND stitching vias (no track on them) that a label sits on, so no label prints over a via, and refill."""
import sys, pcbnew

P = sys.argv[1]; b = pcbnew.LoadBoard(P); mm, T = pcbnew.FromMM, pcbnew.ToMM
REFS = {  # ref: (x, y, angle)
    'R33': (97.84, 86.01, None), 'C7': (177.91, 85.99, None), 'D5': (76.80, 82.16, None), 'F3': (137.89, 82.34, None),
    'F4': (137.89, 99.94, None), 'F5': (137.89, 117.54, None), 'R46': (152.98, 73.96, None), 'J16': (55.05, 139.32, None),
    'D26': (154.06, 67.55, None), 'R34': (95.37, 84.01, None), 'C26': (177.98, 90.82, None), 'C8': (73.65, 114.35, None),
    'C9': (73.65, 119.31, None), 'D17': (143.50, 136.24, None), 'D9': (217.68, 51.65, None), 'F2': (103.52, 70.03, None),
    'L1': (158.68, 76.99, None), 'LED5': (142.90, 94.83, None), 'R26': (159.63, 115.55, None), 'R38': (197.21, 137.69, None),
    'U2': (108.19, 88.27, None), 'U3': (108.19, 100.18, None), 'U4': (108.19, 117.78, None), 'U5': (108.19, 141.07, None),
    'J1': (101.03, 100.83, None), 'R32': (100.28, 80.64, 90), 'R43': (189.88, 72.23, None), 'R41': (73.36, 125.62, None),
    'R45': (150.77, 70.98, None), 'U8': (97.30, 77.47, None), 'D25': (183.24, 63.77, None), 'Q1': (212.16, 69.76, None),
    'R10': (106.07, 93.06, None), 'R5': (107.48, 80.70, None), 'R4': (107.48, 82.00, None),   # off routed vias
}
SILK_ON = {  # ref: (x, y), 1 mm text, upright
    'LED3': (147.48, 64.58), 'LED8': (147.48, 67.48), 'LED1': (147.48, 70.38), 'LED2': (147.48, 73.28),
    'J5': (234.58, 60.35), 'SW2': (113.9, 64.04), 'H1': (83.96, 139.48),
    'TP1': (229.28, 68.21), 'TP6': (239.91, 68.21), 'TP9': (61.01, 142.79), 'TP7': (67.98, 142.79),   # level with the pad
    'TP2': (151.68, 147.25), 'TP3': (158.68, 147.25), 'TP4': (165.68, 147.25), 'TP5': (172.68, 147.25), 'TP8': (179.68, 147.25),
    'H6': (216.74, 77.24), 'H7': (236.36, 77.24), 'H8': (216.74, 123.94), 'H9': (236.36, 123.94),  # servo standoffs, inboard
}
TAGS = (143.3, 63.7, 146.2, 74.1)                            # the 24V / 9V / 5V / 3V3 tags (filled polygons)
gone = widened = 0; dots = []
fps = [f for f in b.GetFootprints()]                        # look up before removing anything (SWIG loses the type after Remove)
for f in fps:
    for g in f.GraphicalItems():
        if g.GetLayerName() != 'F.Silkscreen' or g.GetClass() != 'PCB_SHAPE': continue
        if 'ircle' in g.GetShapeStr() and T(g.GetRadius()) < 0.1 and T(g.GetWidth()) < 0.1 and not g.IsFilled():
            dots.append((f, g))
        elif not g.IsFilled() and 0 < T(g.GetWidth()) < 0.15:
            g.SetWidth(mm(0.15)); widened += 1
    r = f.GetReference()
    if r in SILK_ON:
        t = f.Reference(); t.SetLayer(pcbnew.F_SilkS); t.SetVisible(True); t.SetTextSize(pcbnew.VECTOR2I(mm(1), mm(1)))
        t.SetTextThickness(mm(0.15)); t.SetTextAngleDegrees(0); t.SetMirrored(False); REFS[r] = (*SILK_ON[r], None)
    if r in REFS:
        x, y, ang = REFS[r]; t = f.Reference()
        if ang is not None: t.SetTextAngleDegrees(ang)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
for f, g in dots: f.Remove(g); gone += 1
for g in b.GetDrawings():
    if g.GetLayerName() == 'F.Silkscreen' and g.GetClass() == 'PCB_SHAPE' and not g.IsFilled() and 0 < T(g.GetWidth()) < 0.15:
        g.SetWidth(mm(0.15)); widened += 1
    bb = g.GetBoundingBox()
    if g.GetLayerName() == 'F.Silkscreen' and g.GetClass() == 'PCB_SHAPE' and g.IsFilled() and TAGS[0] < T(bb.GetLeft()) \
            and T(bb.GetRight()) < TAGS[2] and TAGS[1] < T(bb.GetTop()) and T(bb.GetBottom()) < TAGS[3]:
        g.Move(pcbnew.VECTOR2I(mm(-0.5), 0))
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
P2 = lambda g: (T(g.GetStart().x), T(g.GetStart().y), T(g.GetEnd().x), T(g.GetEnd().y))
txt = {t.GetText(): t for t in b.GetDrawings() if t.GetClass() == 'PCB_TEXT' and t.GetLayerName() == 'F.Silkscreen'}
sig, exc = txt['LOAD CELL SIG'], txt['LOAD CELL EXC']
sy, xs, xe = T(sig.GetPosition().y), T(sig.GetPosition().x), T(exc.GetPosition().x)
segs = [g for g in b.GetDrawings() if g.GetClass() == 'PCB_SHAPE' and g.GetLayerName() == 'F.Silkscreen' and g.GetShapeStr() == 'Line']
hz = [g for g in segs if abs(P2(g)[1] - P2(g)[3]) < 0.01 and any(min(P2(g)[0], P2(g)[2]) < x < max(P2(g)[0], P2(g)[2]) for x in (xs, xe))]
ydiv, ybot = max(P2(g)[1] for g in hz if P2(g)[1] < sy), min(P2(g)[1] for g in hz if P2(g)[1] > sy)
inner = [g for g in segs if abs(P2(g)[0] - P2(g)[2]) < 0.01 and xs < P2(g)[0] < xe and min(P2(g)[1], P2(g)[3]) < sy < max(P2(g)[1], P2(g)[3])]
assert len(inner) == 2, 'expected the two facing sides of the J12 / J13 label boxes'
for g in inner:                                            # the boxes' facing sides stop at the pin row ...
    x, top = P2(g)[0], min(P2(g)[1], P2(g)[3]); g.SetStart(V(x, top)); g.SetEnd(V(x, ydiv))
xa, xb = sorted(P2(g)[0] for g in inner)
for y in (ydiv, ybot):                                     # ... and the name row runs on across the gap
    n = pcbnew.PCB_SHAPE(b); n.SetShape(pcbnew.SHAPE_T_SEGMENT); n.SetLayer(pcbnew.F_SilkS); n.SetWidth(inner[0].GetWidth())
    n.SetStart(V(xa, y)); n.SetEnd(V(xb, y)); b.Add(n)
bot = [P2(g) for g in hz if abs(P2(g)[1] - ybot) < 0.01]
sig.SetText('5V LOAD CELL'); sig.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
sig.SetPosition(V((min(min(q[0], q[2]) for q in bot) + max(max(q[0], q[2]) for q in bot)) / 2, sy)); b.Remove(exc)
k = pcbnew.PCB_TEXT(b); k.SetText('CANBUS'); k.SetLayer(pcbnew.F_SilkS); k.SetIsKnockout(True); k.SetTextAngleDegrees(90)
k.SetTextSize(V(1.0, 1.0)); k.SetTextThickness(mm(0.16)); k.SetPosition(V(72.35, 101.80))
k.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); k.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER); b.Add(k)
gl = [f.Reference().GetEffectiveTextShape().BBox() for f in b.GetFootprints()
      if f.Reference().IsVisible() and f.Reference().GetLayerName() == 'F.Silkscreen'] + [k.GetBoundingBox()]
for g in gl: g.Inflate(mm(0.1))
ends = [p for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'GND' for p in (t.GetStart(), t.GetEnd())]
stitch = [v for v in b.GetTracks() if v.GetClass() == 'PCB_VIA' and v.GetNetname() == 'GND'
          and any(g.Intersects(v.GetBoundingBox()) for g in gl) and not any(v.HitTest(p, 0) for p in ends)]
for v in stitch: b.Remove(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print(f'silk: {gone} unprintable dots removed, {widened} strokes widened to 0.15, {len(REFS) - len(SILK_ON)} labels moved, '
      f'{len(SILK_ON)} put on silk, {len(stitch)} stitching vias under labels dropped')
