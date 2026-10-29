"""Line-drawing previews of the enclosure (FreeCAD, headless): closed box, open base with the board, and the two
connector walls, the lid's LED holes and light guides. Writes enclosure/preview.html (render it with a browser / headless Chrome for a PNG).

    freecadcmd -c "import sys; sys.argv = ['preview.py', '<project dir>']; exec(open('<project dir>/generator/enclosure/preview.py').read())"
"""
import sys, os, re, FreeCAD, Part, Import, TechDraw

V = FreeCAD.Vector
D = sys.argv[1]; OUT = os.path.join(D, 'enclosure'); NAME = 'MES4-Carrier-EC'
load = lambda f: Part.read(os.path.join(OUT, f))
base, lid = load(NAME + '_base.step'), load(NAME + '_lid.step')
doc = FreeCAD.newDocument('board')
Import.insert(os.path.join(D, 'review', 'MES4_Carrier_EC.step'), doc.Name)
groups = {}
for o in doc.Objects:
    if o.TypeId != 'Part::Feature' or o.Shape.isNull() or not o.Shape.Solids: continue
    p = o
    while p.InList and not p.InList[0].Label.startswith('MES4_Carrier_EC'): p = p.InList[0]
    s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
    groups.setdefault(p.Label, []).append(s)
# the enclosure STEPs share the board STEP's frame, but sit the parts on the real 1.6 mm board like enclosure.py does
pcb = Part.makeCompound(next(v for k, v in groups.items() if k.endswith('_PCB')))
dz = 1.6 - pcb.BoundBox.ZMax
parts = []
for k, v in groups.items():
    c = Part.makeCompound(v)
    if not k.endswith('_PCB'): c.translate(V(0, 0, dz))
    parts.append((k, c))
edge = [c for k, c in parts if k.startswith(('RJ45', 'TYPE-C', 'AMASS_XT30', 'DSUB', 'CONN-TH_KF250NH'))]
board = [c for k, c in parts if 'silkscreen' not in k]


def svg(shape, direction, width, rot=0):
    """rot: turn the drawing (degrees, SVG sense) so a wall reads as seen from outside, height up."""
    g = TechDraw.projectToSVG(shape, direction).replace('stroke-width="1.0"', 'stroke-width="%.2f"' % width)
    xs, ys = [], []
    for cmd, args in re.findall(r'([MLCQA])([^MLCQAZz]*)', ' '.join(re.findall(r'd="([^"]*)"', g))):
        n = [float(t) for t in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?', args)]
        pts = {'M': n, 'L': n, 'C': n, 'Q': n, 'A': n[5:7] if len(n) >= 7 else []}[cmd]
        xs += pts[0::2]; ys += pts[1::2]
    import math
    c, sn = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    pts = [(X * c - Y * sn, X * sn + Y * c) for X in (min(xs), max(xs)) for Y in (-max(ys), -min(ys))]   # displayed (y down)
    x0, x1, y0, y1 = min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)
    m = 0.03 * max(x1 - x0, y1 - y0)
    return '<svg viewBox="%.2f %.2f %.2f %.2f" preserveAspectRatio="xMidYMid meet"><g transform="rotate(%d)">%s</g></svg>' % (
        x0 - m, y0 - m, x1 - x0 + 2 * m, y1 - y0 + 2 * m, rot, g)


closed = Part.makeCompound([base, lid] + edge)
views = [('Closed: left and top walls (RJ45, USB-C, DB9, terminals, XT30)', svg(closed, V(-1, 1, 1), 0.18)),
         ('Base with the board, lid off', svg(Part.makeCompound([base] + board), V(-1, 1, 1.3), 0.12)),
         ('Top wall from outside: XT30, ten terminal wire slots, DB9', svg(closed, V(0, 1, 0), 0.15, -90)),
         ('Left wall from outside: RJ45 bank and USB-C', svg(closed, V(-1, 0, 0), 0.15, 90)),
         ('Lid from above: LED holes (24V / 9V / 5V / 3V3 column, relays 1-4) and the corner screws', svg(lid, V(0, 0, 1), 0.15)),
         ('Lid from underneath: the LED light-guide tubes and the corner pillars', svg(lid, V(-1, 1, -1.2), 0.15))]
html = ['<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#fff;font:15px system-ui;color:#222}'
        '.g{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:12px}.c{border:1px solid #ddd;padding:6px}'
        '.c svg{width:100%;height:600px;display:block}.t{font-weight:600;margin:2px 4px 6px}</style><div class="g">']
for t, s in views: html.append('<div class="c"><div class="t">%s</div>%s</div>' % (t, s))
open(os.path.join(OUT, 'preview.html'), 'w').write(''.join(html) + '</div>')
print('preview: %d views written' % len(views))
