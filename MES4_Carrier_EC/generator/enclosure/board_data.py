"""Board facts for the enclosure generator (run with KiCad's Python):

    board_data.py <pcb> <out.json>

Coordinates match the board STEP export (review/MES4_Carrier_EC.step, --user-origin 49.9x149.4mm): x right, y up, origin
at the bottom-left corner of the 200 x 100 mm board rectangle. Writes the Edge.Cuts outline (lines / arcs), the four
corner mounting holes (H2-H5), the FE-URT-2 standoffs (H6-H9: A1 has no 3D model yet), the LEDs (centre of their
pads), the board thickness and the MONKEY ROBOTICS logo (the silkscreen group "LOGO Monkey Robotics", unfractured
into outlines and holes, in its own frame: origin at its bottom-left, y up)."""
import sys, json, pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM
X0, Y0 = 49.9, 149.4
S = lambda p: [round(T(p.x) - X0, 4), round(Y0 - T(p.y), 4)]
edges = []
for d in b.GetDrawings():
    if d.GetLayerName() != 'Edge.Cuts': continue
    if d.GetShapeStr() == 'Arc': edges.append(['arc', S(d.GetStart()), S(d.GetArcMid()), S(d.GetEnd())])
    elif d.GetShapeStr() == 'Line': edges.append(['line', S(d.GetStart()), S(d.GetEnd())])
    else: raise SystemExit('unhandled Edge.Cuts shape ' + d.GetShapeStr())
pos = lambda r: S(b.FindFootprintByReference(r).GetPosition())


def centre(f):
    bb = f.Pads()[0].GetBoundingBox()
    for p in f.Pads(): bb.Merge(p.GetBoundingBox())
    return S(bb.GetCenter())


leds = sorted([f.GetReference()] + centre(f) for f in b.GetFootprints() if f.GetFPIDAsString().split(':')[-1].startswith('LED'))
logo = []
for d in next(g for g in b.Groups() if g.GetName() == 'LOGO Monkey Robotics').GetItems():
    ps = d.GetPolyShape().CloneDropTriangulation(); ps.Unfracture()
    for k in range(ps.OutlineCount()):
        chain = lambda c: [S(c.CPoint(i)) for i in range(c.PointCount())]
        logo.append([chain(ps.Outline(k))] + [chain(ps.Hole(k, h)) for h in range(ps.HoleCount(k))])
lx, ly = min(p[0] for poly in logo for p in poly[0]), min(p[1] for poly in logo for p in poly[0])
logo = [[[[round(x - lx, 4), round(y - ly, 4)] for x, y in ring] for ring in poly] for poly in logo]
json.dump(dict(edges=edges, logo=logo, holes=[pos(r) for r in ('H2', 'H3', 'H4', 'H5')],
               hole_d=T(b.FindFootprintByReference('H2').Pads()[0].GetDrillSize().x),
               fe_urt2=[pos(r) for r in ('H6', 'H7', 'H8', 'H9')], leds=leds,
               thickness=T(b.GetDesignSettings().GetBoardThickness())), open(sys.argv[2], 'w'), indent=1)
print('board_data: %d outline edges, holes %s, logo %d outlines / %d holes, %.1f x %.1f mm'
      % (len(edges), [pos(r) for r in ('H2', 'H3', 'H4', 'H5')], len(logo), sum(len(p) - 1 for p in logo),
         max(p[0] for poly in logo for p in poly[0]), max(p[1] for poly in logo for p in poly[0])))
