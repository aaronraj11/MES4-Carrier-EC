"""Two-part enclosure for the MES4-Carrier-EC (FDM print, M3 heat-set inserts), built around the board's own STEP.

    freecadcmd -c "import sys; sys.argv = ['enclosure.py', '<project dir>']; exec(open('<project dir>/generator/enclosure/enclosure.py').read())"

Inputs: enclosure/board_data.json (generator/enclosure/board_data.py, KiCad's Python) and review/MES4_Carrier_EC.step
(kicad-cli STEP export with --user-origin 49.9x149.4mm, see HANDOFF). Outputs in enclosure/, in the board STEP's frame
(x right, y up, origin at the bottom-left corner of the board rectangle, z = 0 at the board's underside), so the board
STEP, base and lid open in place: MES4-Carrier-EC_base / _lid .step, _assembly.step, and print-ready .stl (base on its
floor, lid upside down).

Layout
- The cavity follows the board outline (200 x 100 mm, corner lobes r 5 round the M3 holes H2-H5) with CLR clearance;
  walls WALL thick, so the corners are round lobes too.
- Base: floor, walls up to the board's top face (the split), a tongue above the split that the lid's skirt fits over,
  and four corner pillars the board sits on, each with an M3 heat-set insert.
- Lid: top, walls, skirt, and four pillars that press the board's corners down, with counterbored clearance holes:
  one M3 x 25 socket-head screw per corner goes through lid, board and into the base insert.
- Heights from the parts: the board stands STANDOFF above the floor (clears the THT leads under it), the ceiling sits
  HEADROOM above the tallest part (the SRD relays) and above FE_URT2_TOP (A1 has no 3D model yet).
- Openings, cut through base and lid wherever they reach: for every connector at the board edge, its outline where it
  meets the wall plus a margin (RJ45 bank, USB-C opened to fit a plug overmould, XT30 with room for the plug, DB9 with
  its flange); one slot in front of each push-in terminal's wire entry (they take the wire from the edge side, 5-13.5 mm
  above the board); and a cable slot in the right wall beside the FE-URT-2 for its servo lead (placeholder: A1 has no
  model, so the slot isn't aligned to its connector). Openings on one wall keep at least MIN_POST of wall between them.
- LEDs: each LED gets a light-guide tube from the lid down to just above it (LED_GAP over the LED, PART_GAP over
  anything else under the tube), so each LED lights its own hole: dia 2.5 bores, dia 2.0 where LEDs sit closer than 4 mm
  (the 24V / 9V / 5V / 3V3 column at 2.9 mm, whose tubes merge into one block with 0.9 mm walls between the bores).
  A dia 2-2.5 mm light pipe or a piece of clear filament fits a bore for a flush glowing dot.
- Mounting: two M5 tabs on the base, at the centre of the left and right ends, 5 mm thick with ribs; bolt down from
  above. The left one sits under the RJ45 plugs, so the board stands high enough (STANDOFF) for an M5 socket head and
  washer to pass under them; the script checks every bolt head against the openings above it.
- Branding and labels: the MONKEY ROBOTICS logo (the board's silkscreen artwork) engraved LOGO_DEPTH deep into the lid's
  top right, over an inside pad so the lid stays LOGO_DEPTH + 2 mm thick there; small engraved labels beside the LED
  holes (24V / 9V / 5V / 3V3, RLY1-4).
- Fit, tuned for a Bambu Lab P1S (0.4 mm nozzle, PLA / PETG): see the P1S block of parameters. The lid's skirt stops
  SEAT_GAP above the base wall and the tongue TONGUE_TOP_GAP below the lid, so the four screws always clamp the board
  between the pillars whatever its thickness (1.6 mm +-10 %).
- Printing: base on its floor, lid on its top, no supports. The edges on the bed are chamfered (elephant's foot), the
  insert pockets have a lead-in, the counterbores end in a 45 deg cone instead of a flat ledge, and the only bridges
  are the tops of the terminal wire slots. The script lists every downward-facing surface off the bed.
Every part of the board STEP is checked against base and lid for overlap."""
import sys, os, json, math, FreeCAD, Part, Import, Mesh, MeshPart

V = FreeCAD.Vector
D = sys.argv[1]; OUT = os.path.join(D, 'enclosure'); NAME = 'MES4-Carrier-EC'
B = json.load(open(os.path.join(OUT, 'board_data.json')))

# ---- parameters (mm)
WALL, FLOOR, TOP = 2.5, 2.5, 2.5
# Bambu Lab P1S fit (0.4 mm nozzle, PLA / PETG): XY within ~0.1-0.15 mm, holes print ~0.1 mm small
CLR = 0.6                               # board edge to cavity wall: board outline +-0.2 mm plus the print
FIT_P1S = 0.3                           # lid skirt over the base tongue, per side
HOLE_COMP = 0.1                         # added to every clearance hole and light-guide bore
SEAT_GAP, TONGUE_TOP_GAP = 0.3, 0.5     # lid skirt above the base wall / tongue below the lid: the screws clamp the board
STANDOFF = 8.0                          # floor to board underside: SW2's pins reach 3.5 mm below the board, and an
                                        # M5 socket head + washer on the left tab passes under the RJ45 plugs
HEADROOM = 2.0                          # tallest part to the ceiling
FE_URT2_TOP = 15.0                      # FE-URT-2 stack above the board (2 mm standoffs + 1.6 board + parts), estimate
TONGUE, TONGUE_H, FIT = 1.2, 2.0, FIT_P1S   # base tongue width, lid groove height above the split, skirt clearance
PILLAR_LID_R, WEB_FROM = 4.5, 7.0       # lid pillars clear J5 (5.1 mm from H3); full-width corner web from 7 mm up
INSERT_D, INSERT_DEPTH, TIP_D, TIP_DEPTH = 4.0, 6.0, 2.8, 1.0      # M3 x 5.7 brass heat-set insert, screw-tip room
SCREW_D, HEAD_D, HEAD_DEPTH = 3.4 + HOLE_COMP, 6.2 + HOLE_COMP, 3.2   # M3 socket-head clearance and counterbore
M_CONN, M_XT30, USBC_MIN = 0.5, 1.0, (13.0, 7.5)                   # opening margins; USB-C plug overmould
TERM_Z, TERM_M = (5.0, 13.5), 0.25      # push-in terminal wire slot: height band above the board, side margin
SERVO_SLOT = (14.0, 12.0)               # FE-URT-2 servo-lead slot in the right wall: width, height above the board
SERVO_Y = 66.0                          # its centre: beside the FE-URT-2 (y 18-73), clear of the right M5 tab
MIN_POST = 1.2                          # narrowest wall left between two openings
LED_BORE, LED_BORE_DENSE, LED_WALL = 2.5 + HOLE_COMP, 2.0 + HOLE_COMP, 0.9   # light-guide bore (dia 2.0 where LEDs are
                                                                             # < 4 mm apart), tube wall
LED_GAP, PART_GAP, LED_SINK = 0.8, 0.5, 0.4          # tube end above its LED / above other parts; countersink outside
CHAMFER, LEAD_IN = 0.6, 0.4             # print-bed edges; heat-set insert pocket lead-in
M5_TABS = (('left', 50.0), ('right', 50.0))  # wall, position along it: the centre of each end
M5_HEAD, WASHER = 5.0, 1.0              # M5 socket head height, washer: must pass under the openings above the tab
M5_D, TAB_T, TAB_W, TAB_OUT, TAB_HOLE, TAB_R = 5.5 + HOLE_COMP, 5.0, 18.0, 14.0, 8.0, 4.0   # hole, thickness, width,
                                        # reach past the wall, hole centre from the wall, corner radius
RIB, RIB_L, RIB_H = 3.0, 6.0, 5.0       # ribs between tab and wall (they stay under the RJ45 plugs too)
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
LOGO_W, LOGO_CENTRE, LOGO_DEPTH, LOGO_PAD = 58.0, (161.0, 86.0), 2.5, 2.0   # width, centre, engraving, pad inside
LED_LABELS = {'LED3': '24V', 'LED8': '9V', 'LED1': '5V', 'LED2': '3V3',   # the board's tags beside the power LEDs;
              'LED4': 'RLY1', 'LED5': 'RLY2', 'LED6': 'RLY3', 'LED7': 'RLY4'}   # LED4-7 hang off RLY1_OUT-RLY4_OUT
LABEL_H, LABEL_DEPTH, LABEL_GAP = 2.4, 0.6, 1.0   # text height (fits the 2.9 mm LED pitch), engraving, gap to the hole

# ---- board outline, faces
edges = [Part.LineSegment(V(*e[1], 0), V(*e[2], 0)).toShape() if e[0] == 'line'
         else Part.Arc(V(*e[1], 0), V(*e[2], 0), V(*e[3], 0)).toShape() for e in B['edges']]
board = Part.Face(Part.Wire(Part.__sortEdges__(edges)))
off = lambda d: board.makeOffset2D(d, 0, False, False, False)
CAV, OUTER, TONGUE_OUT, SKIRT_IN = off(CLR), off(CLR + WALL), off(CLR + TONGUE), off(CLR + TONGUE + FIT)
bx = board.BoundBox; RECT = (min(e[1][0] for e in B['edges'] if e[0] == 'line'), 0, 0, 0)
X0, X1 = 0.0, 200.0; Y0, Y1 = 0.0, 100.0          # board rectangle (straight edges), corner lobes beyond


def bed_chamfer(slab, z):
    """Chamfer the outline of a slab's face at height z: the face that lies on the print bed."""
    try:
        return slab.makeChamfer(CHAMFER, [e for e in slab.Edges if all(abs(v.Z - z) < 1e-6 for v in e.Vertexes)])
    except Exception as ex:
        print('  (no bed chamfer: %s)' % ex); return slab


def prism(f, z0, z1):
    s = f.copy(); s.translate(V(0, 0, z0)); return s.extrude(V(0, 0, z1 - z0))


ring = lambda a, b, z0, z1: prism(a, z0, z1).cut(prism(b, z0, z1))
cyl = lambda r, x, y, z0, z1: Part.makeCylinder(r, z1 - z0, V(x, y, z0))
box = lambda x0, y0, z0, x1, y1, z1: Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

# ---- the board and its parts (board STEP), in the enclosure frame (z = 0 at the base's underside)
doc = FreeCAD.newDocument('board')
Import.insert(os.path.join(D, 'review', 'MES4_Carrier_EC.step'), doc.Name)
groups = {}
for o in doc.Objects:
    if o.TypeId != 'Part::Feature' or o.Shape.isNull() or not o.Shape.Solids: continue
    p = o
    while p.InList and not p.InList[0].Label.startswith('MES4_Carrier_EC'): p = p.InList[0]
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
    groups.setdefault(p.Name, [p.Label, []])[1].append(s)
parts = {k: (lab, Part.makeCompound(sh)) for k, (lab, sh) in groups.items()}
pcb = next(s for lab, s in parts.values() if lab.endswith('_PCB'))
ZB = FLOOR + STANDOFF; ZT = ZB + B['thickness']
DZ = ZT - pcb.BoundBox.ZMax                     # parts sit on the real 1.6 mm board's top face
for lab, s in parts.values(): s.translate(V(0, 0, DZ))
comps = {k: (lab, s) for k, (lab, s) in parts.items() if not lab.endswith('_PCB') and 'silkscreen' not in lab}
tallest = max(s.BoundBox.ZMax for lab, s in comps.values()) - ZT
lowest = ZB - min(s.BoundBox.ZMin for lab, s in comps.values() if s.BoundBox.XMin > X0 + 1 and s.BoundBox.YMin > Y0 + 1
                  and s.BoundBox.XMax < X1 - 1 and s.BoundBox.YMax < Y1 - 1)
ZC = ZT + max(tallest, FE_URT2_TOP) + HEADROOM  # ceiling (lid's inner face)
ZL = ZC + TOP
assert lowest < STANDOFF - 0.5, 'leads under the board reach %.1f mm: raise STANDOFF' % lowest

# ---- base
base = bed_chamfer(prism(OUTER, 0, FLOOR), 0).fuse(ring(OUTER, CAV, FLOOR, ZT - SEAT_GAP))
base = base.fuse(ring(TONGUE_OUT, CAV, ZT - SEAT_GAP - 0.01, ZT + TONGUE_H - TONGUE_TOP_GAP))
for hx, hy in B['holes']:
    base = base.fuse(cyl(CLR + 5.0 + 0.01, hx, hy, FLOOR - 0.01, ZB))
def m5_tab(wall, a):
    """A floor-level tab past the left / right wall with an M5 clearance hole and two ribs up the wall."""
    sg = -1 if wall == 'left' else 1
    xw = X0 - CLR - WALL if wall == 'left' else X1 + CLR + WALL          # outer wall face
    xf = xw + sg * TAB_OUT
    t = box(min(xw - sg, xf), a - TAB_W / 2, 0, max(xw - sg, xf), a + TAB_W / 2, TAB_T)
    t = t.makeFillet(TAB_R, [e for e in t.Edges if len(e.Vertexes) == 2 and abs(e.Vertexes[0].X - xf) < 1e-6
                             and abs(e.Vertexes[1].X - xf) < 1e-6 and abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])
    for dy in (-(TAB_W - RIB) / 2, (TAB_W - RIB) / 2):
        y0 = a + dy - RIB / 2
        tri = [V(xw - sg, y0, TAB_T - 0.01), V(xw + sg * RIB_L, y0, TAB_T - 0.01), V(xw - sg, y0, TAB_T + RIB_H)]
        t = t.fuse(Part.Face(Part.makePolygon(tri + [tri[0]])).extrude(V(0, RIB, 0)))
    return t, cyl(M5_D / 2, xw + sg * TAB_HOLE, a, -1, TAB_T + RIB_H + 1)


m5_holes = []
for wall, a in M5_TABS:
    t, h = m5_tab(wall, a); base = base.fuse(t); m5_holes.append(h)
for h in m5_holes: base = base.cut(h)
for hx, hy in B['holes']:
    base = base.cut(cyl(INSERT_D / 2, hx, hy, ZB - INSERT_DEPTH, ZB + 1)).cut(cyl(TIP_D / 2, hx, hy, ZB - INSERT_DEPTH - TIP_DEPTH, ZB))
    base = base.cut(Part.makeCone(INSERT_D / 2, INSERT_D / 2 + LEAD_IN, LEAD_IN + 0.01, V(hx, hy, ZB - LEAD_IN)))

# ---- lid
lid = bed_chamfer(prism(OUTER, ZC, ZL), ZL).fuse(ring(OUTER, CAV, ZT + TONGUE_H, ZC)).fuse(ring(OUTER, SKIRT_IN, ZT, ZT + TONGUE_H))
for hx, hy in B['holes']:
    lid = lid.fuse(cyl(PILLAR_LID_R, hx, hy, ZT, ZC + 0.01)).fuse(cyl(CLR + 5.0 + 0.01, hx, hy, ZT + WEB_FROM, ZC + 0.01))
CONE = (HEAD_D - SCREW_D) / 2                    # the counterbore ends in a 45 deg cone: no flat ledge to bridge
for hx, hy in B['holes']:
    lid = lid.cut(cyl(SCREW_D / 2, hx, hy, ZT - 1, ZL + 1)).cut(cyl(HEAD_D / 2, hx, hy, ZL - HEAD_DEPTH, ZL + 1))
    lid = lid.cut(Part.makeCone(SCREW_D / 2, HEAD_D / 2, CONE, V(hx, hy, ZL - HEAD_DEPTH - CONE)))

# ---- LED light guides: a tube from the lid down to just above each LED, its own bore through the top
guides = []
for ref, x, y in B['leds']:
    d = LED_BORE_DENSE if min(math.dist((x, y), (u, w)) for r, u, w in B['leds'] if r != ref) < 4.0 else LED_BORE
    R = d / 2 + LED_WALL; zb = ZT + PART_GAP
    for lab, s in comps.values():                # the tallest thing under the tube sets its end
        b = s.BoundBox
        if b.XMax < x - R or b.XMin > x + R or b.YMax < y - R or b.YMin > y + R or b.ZMin > ZC: continue
        own = lab.startswith('LED') and abs(b.Center.x - x) < 0.6 and abs(b.Center.y - y) < 0.6
        zb = max(zb, b.ZMax + (LED_GAP if own else PART_GAP))
    guides.append((ref, x, y, d, R, zb))
for ref, x, y, d, R, zb in guides: lid = lid.fuse(cyl(R, x, y, zb, ZC + 0.01))
for ref, x, y, d, R, zb in guides:
    lid = lid.cut(cyl(d / 2, x, y, zb - 1, ZL + 1)).cut(Part.makeCone(d / 2, d / 2 + LED_SINK, LED_SINK + 0.01, V(x, y, ZL - LED_SINK)))


def engrave(faces, depth):
    """Cut flat faces (at z 0) into the lid's top, `depth` deep."""
    global lid
    for f in faces:
        g = f.copy(); g.translate(V(0, 0, ZL - depth)); lid = lid.cut(g.extrude(V(0, 0, depth + 1)))


# MONKEY ROBOTICS logo, top right: the board's silkscreen outlines, scaled to LOGO_W, over a pad inside the lid
lw = max(p[0] for poly in B['logo'] for p in poly[0]); lh = max(p[1] for poly in B['logo'] for p in poly[0])
LK = LOGO_W / lw; ox, oy = LOGO_CENTRE[0] - LOGO_W / 2, LOGO_CENTRE[1] - lh * LK / 2
ring_w = lambda r: Part.makePolygon([V(ox + x * LK, oy + y * LK, 0) for x, y in r] + [V(ox + r[0][0] * LK, oy + r[0][1] * LK, 0)])
logo = [Part.makeFace([ring_w(r) for r in poly], 'Part::FaceMakerBullseye') for poly in B['logo']]
lid = lid.fuse(box(ox - 2, oy - 2, ZC - LOGO_PAD, ox + LOGO_W + 2, oy + lh * LK + 2, ZC + 0.01))
engrave(logo, LOGO_DEPTH)
# LED labels, to the right of each hole, centred on it
labels = []
for ref, x, y, d, R, zb in guides:
    if ref not in LED_LABELS: continue
    chars = [Part.makeFace(ch, 'Part::FaceMakerBullseye') for ch in Part.makeWireString(LED_LABELS[ref], FONT, LABEL_H, 0) if ch]
    c = Part.makeCompound(chars); bb = c.BoundBox
    c.translate(V(x + d / 2 + LED_SINK + LABEL_GAP - bb.XMin, y - (bb.YMin + bb.YMax) / 2, 0))
    labels += c.Faces
engrave(labels, LABEL_DEPTH)

# ---- openings
OUT_D = CLR + WALL                               # board rectangle to the outer wall face
walls = {'left': (lambda bb: bb.XMin - X0), 'right': (lambda bb: X1 - bb.XMax),
         'bottom': (lambda bb: bb.YMin - Y0), 'top': (lambda bb: Y1 - bb.YMax)}


def through(wall, a0, a1, z0, z1):
    """A box through `wall`, spanning a0..a1 along it and z0..z1, from 1 mm inside its inner face to past the outside."""
    z0 = max(z0, FLOOR + 0.8)
    if wall == 'left': return box(X0 - OUT_D - 1, a0, z0, X0 - CLR + 1, a1, z1)
    if wall == 'right': return box(X1 + CLR - 1, a0, z0, X1 + OUT_D + 1, a1, z1)
    if wall == 'bottom': return box(a0, Y0 - OUT_D - 1, z0, a1, Y0 - CLR + 1, z1)
    return box(a0, Y1 + CLR - 1, z0, a1, Y1 + OUT_D + 1, z1)


def beyond(wall, d):
    """Everything closer than d to the wall's inner face, or past it."""
    big = 1000
    if wall == 'left': return box(-big, -big, -big, X0 - CLR + d, big, big)
    if wall == 'right': return box(X1 + CLR - d, -big, -big, big, big, big)
    if wall == 'bottom': return box(-big, -big, -big, big, Y0 - CLR + d, big)
    return box(-big, Y1 + CLR - d, -big, big, big, big)


found = lambda g: not g.isNull() and (g.Volume > 1e-3 or g.Area > 1e-3)   # some models (J4) slice to faces, volume 0
wins, report = [], []
KINDS = (('RJ45', 'RJ45 bank'), ('TYPE-C', 'USB-C'), ('AMASS_XT30', 'XT30'), ('DSUB', 'DB9'), ('CONN-TH_KF250NH', 'terminal'))
for k, (lab, s) in sorted(comps.items(), key=lambda kv: kv[1][1].BoundBox.XMin):
    kind = next((n for pre, n in KINDS if lab.startswith(pre)), None)
    if not kind: continue
    bb = s.BoundBox; wall = min(walls, key=lambda w: walls[w](bb))
    if walls[wall](bb) > 1.0: continue           # faces inward (J15 / J17 feed the FE-URT-2 inside)
    along = (lambda b: (b.YMin, b.YMax)) if wall in ('left', 'right') else (lambda b: (b.XMin, b.XMax))
    if kind == 'terminal':
        a0, a1 = along(bb); a0, a1 = a0 - TERM_M, a1 + TERM_M; z0, z1 = ZT + TERM_Z[0], ZT + TERM_Z[1]
    else:                                        # its outline where it meets the wall; a part that stays on the
        near = s.common(beyond(wall, 1.0))       # board (no overhang) only counts above the board: its legs go
        fb = near.BoundBox if found(near) else bb  # through the board, not through the wall
        over = {'left': X0 - fb.XMin, 'right': fb.XMax - X1, 'bottom': Y0 - fb.YMin, 'top': fb.YMax - Y1}[wall]
        if over < 0.05: fb = FreeCAD.BoundBox(fb.XMin, fb.YMin, max(fb.ZMin, ZT - 0.2), fb.XMax, fb.YMax, fb.ZMax)
        m = M_XT30 if kind == 'XT30' else M_CONN
        a0, a1 = along(fb); a0, a1, z0, z1 = a0 - m, a1 + m, fb.ZMin - m, fb.ZMax + m
        if kind == 'USB-C':
            ca, cz = (a0 + a1) / 2, (z0 + z1) / 2
            a0, a1 = min(a0, ca - USBC_MIN[0] / 2), max(a1, ca + USBC_MIN[0] / 2)
            z0, z1 = min(z0, cz - USBC_MIN[1] / 2), max(z1, cz + USBC_MIN[1] / 2)
    wins.append([kind, wall, a0, a1, z0, z1])
wins.append(['servo', 'right', SERVO_Y - SERVO_SLOT[0] / 2, SERVO_Y + SERVO_SLOT[0] / 2, ZT, ZT + SERVO_SLOT[1]])
for w in ('left', 'right', 'bottom', 'top'):     # keep MIN_POST of wall between neighbouring openings
    ws = sorted((x for x in wins if x[1] == w), key=lambda x: x[2])
    for p, q in zip(ws, ws[1:]):
        if q[2] - p[3] < MIN_POST and min(p[5], q[5]) > max(p[4], q[4]):
            dd = (MIN_POST - (q[2] - p[3])) / 2; p[3] -= dd; q[2] += dd
heads = []                                       # each M5 head + washer against the openings above its tab
for wall, a in M5_TABS:
    over = [max(z0, FLOOR + 0.8) for kind, w, a0, a1, z0, z1 in wins if w == wall and a0 < a + 5 and a1 > a - 5]
    room = min(over) - (TAB_T + M5_HEAD + WASHER) if over else None
    assert room is None or room > 0.3, '%s M5 head hits the opening above it (%.1f mm): raise STANDOFF' % (wall, room)
    heads.append('%s %s' % (wall, 'nothing above' if room is None else '%.1f mm under the openings above' % room))
for kind, wall, a0, a1, z0, z1 in wins:
    c = through(wall, a0, a1, z0, z1); base, lid = base.cut(c), lid.cut(c)
    report.append('%-8s %-6s wall  along %6.1f..%6.1f  z %5.1f..%5.1f above the board%s'
                  % (kind, wall, a0, a1, max(z0, FLOOR + 0.8) - ZT, z1 - ZT, ' (FE-URT-2 lead, placeholder)' if kind == 'servo' else ''))
base, lid = base.removeSplitter(), lid.removeSplitter()

# ---- checks: every part against base and lid; the board on the pillars
hits = []
for k, (lab, s) in parts.items():
    for name, body in (('base', base), ('lid', lid)):
        if not s.BoundBox.intersect(body.BoundBox): continue
        c = s.common(body)
        if c.isNull(): continue
        if c.Volume > 0.01 or (not lab.endswith('_PCB') and c.Area > 0.5):   # the board itself touches the pillars
            hits.append('%s overlaps %s (%.2f mm3, %.2f mm2)' % (lab, name, c.Volume, c.Area))

# ---- printability: downward-facing surfaces off the bed (base on its floor, lid upside down)
def overhangs(shape):
    out = []
    for f in shape.Faces:
        try: n = f.normalAt(*[(a + b) / 2 for a, b in zip(f.ParameterRange[0::2], f.ParameterRange[1::2])])
        except Exception: continue
        if n.z < -0.72 and f.BoundBox.ZMin > 0.3 and f.Area > 0.05:   # bridge length: the face's longer side
            out.append((round(max(f.BoundBox.XLength, f.BoundBox.YLength), 1), round(f.BoundBox.ZMin, 1), round(f.Area, 1)))
    return sorted(out, reverse=True)


printed = {}
for name, s, flip in (('base', base, False), ('lid', lid, True)):
    t = s.copy()
    if flip: t.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    t.translate(V(0, 0, -t.BoundBox.ZMin)); printed[name] = t

# ---- outputs, in the board STEP's frame (z = 0 at the board's underside)
for s in (base, lid): s.translate(V(0, 0, -ZB))
base.exportStep(os.path.join(OUT, NAME + '_base.step')); lid.exportStep(os.path.join(OUT, NAME + '_lid.step'))
asm = FreeCAD.newDocument('asm')
for name, s in (('base', base), ('lid', lid)): asm.addObject('Part::Feature', name).Shape = s
for lab, s in parts.values():
    t = s.copy(); t.translate(V(0, 0, -ZB)); asm.addObject('Part::Feature', lab.replace(' ', '_')).Shape = t
Import.export(asm.Objects, os.path.join(OUT, NAME + '_assembly.step'))
for name, t in printed.items():
    MeshPart.meshFromShape(Shape=t, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False).write(os.path.join(OUT, '%s_%s.stl' % (NAME, name)))
ob = base.BoundBox.united(lid.BoundBox)
print('enclosure: outside %.1f x %.1f x %.1f mm; board underside %.1f above the floor, ceiling %.1f above the board top'
      % (ob.XLength, ob.YLength, ob.ZLength, STANDOFF, ZC - ZT))
print('  tallest part %.1f mm above the board, deepest lead %.1f mm below it; base valid %s, lid valid %s; base %.0f cm3, lid %.0f cm3'
      % (tallest, lowest, base.isValid(), lid.isValid(), base.Volume / 1000, lid.Volume / 1000))
seat = ZL - HEAD_DEPTH - (HEAD_D - 5.5) / 2      # an M3 socket head (dia 5.5) sits on the cone
print('  screws: 4 x M3 socket head x 25: %.1f mm from the head seat to the insert bottom, %.1f to the tip hole bottom'
      % (seat - (ZB - INSERT_DEPTH), seat - (ZB - INSERT_DEPTH - TIP_DEPTH)))
print('  M5 heads (socket + washer): %s' % '; '.join(heads))
print('  M5 mounting: %s; logo %.0f x %.1f mm at (%.0f, %.0f), %.1f mm deep; %d LED labels %.1f mm tall'
      % (', '.join('%s wall at %.0f mm' % t for t in M5_TABS), LOGO_W, lh * LK, LOGO_CENTRE[0], LOGO_CENTRE[1], LOGO_DEPTH,
         len([g for g in guides if g[0] in LED_LABELS]), LABEL_H))
for ref, x, y, d, R, zb in sorted(guides, key=lambda g: (-g[2], g[1])):
    print('  LED %-5s bore dia %.1f, tube dia %.1f from %.1f mm above the board to the lid' % (ref, d, 2 * R, zb - ZT))
for name, t in printed.items():
    o = overhangs(t)
    print('  print %-4s: %d downward surfaces off the bed (bridges)%s' % (name, len(o), (', longest %.1f mm' % o[0][0]) if o else ''))
for r in report: print('  opening ' + r)
print('  overlaps:', hits or 'none')
