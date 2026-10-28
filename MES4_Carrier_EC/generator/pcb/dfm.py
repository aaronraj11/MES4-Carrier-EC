"""JLCPCB DFM check: the board against JLC's published rigid-PCB capabilities (4-layer, 1 oz outer / 0.5 oz inner).

    dfm.py <pcb>

1. KiCad DRC on a copy of the board with JLC's limits as custom rules (JLC below; netclass gaps drop to JLC's
   minimums, solder-mask web set to JLC's 0.1 mm dam). Vias need their pad 0.1 mm over the hole (ring 0.05); the
   0.15 mm ring is JLC's PTH (component hole) figure. JLC gives no inner-layer figure for bare (NPTH) holes, so they
   are held to the PTH one (0.3 mm). Anything it reports is a JLC limit the board misses; the
   board's own DRC (tighter rules) is run as usual.
2. What DRC doesn't see: vias in SMD pads (via-in-pad filling isn't standard on 4-layer), slots, the narrowest mask
   webs between pads of different nets, the smallest features actually used (margin to JLC), the stackup, parts on
   B.Cu, the finest-pitch parts, and sharp inside corners on the outline (the router leaves a radius there)."""
import sys, os, re, json, shutil, subprocess, collections, itertools, pcbnew

P = os.path.abspath(sys.argv[1]); T = pcbnew.ToMM
CLI = shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
JLC = '''(version 1)
(rule "JLC copper gap" (constraint clearance (min 0.09mm)))
(rule "JLC pad to track" (condition "A.Type == 'Pad' && B.Type == 'Track'") (constraint clearance (min 0.1mm)))
(rule "JLC pad to pad" (condition "A.Type == 'Pad' && B.Type == 'Pad'") (constraint clearance (min 0.15mm)))
(rule "JLC track" (constraint track_width (min 0.09mm)))
(rule "JLC via" (condition "A.Type == 'Via'") (constraint hole_size (min 0.15mm)) (constraint via_diameter (min 0.25mm)))
(rule "JLC pad ring" (condition "A.Type == 'Pad'") (constraint annular_width (min 0.15mm)))
(rule "JLC via ring" (condition "A.Type == 'Via'") (constraint annular_width (min 0.05mm)))
(rule "JLC PTH hole" (condition "A.Type == 'Pad' && A.isPlated()") (constraint hole_size (min 0.15mm) (max 6.3mm)))
(rule "JLC NPTH hole" (condition "A.Type == 'Pad' && !A.isPlated()") (constraint hole_size (min 0.5mm)))
(rule "JLC hole to hole" (constraint hole_to_hole (min 0.2mm)))
(rule "JLC pad hole to pad hole" (condition "A.Type == 'Pad' && B.Type == 'Pad'") (constraint hole_to_hole (min 0.45mm)))
(rule "JLC via hole to copper" (condition "A.Type == 'Via'") (constraint hole_clearance (min 0.2mm)))
(rule "JLC PTH hole to copper" (condition "A.Type == 'Pad' && A.isPlated()") (constraint hole_clearance (min 0.28mm)))
(rule "JLC NPTH hole to copper" (condition "A.Type == 'Pad' && !A.isPlated()") (constraint hole_clearance (min 0.2mm)))
(rule "JLC inner via hole to copper" (layer inner) (condition "A.Type == 'Via'") (constraint hole_clearance (min 0.2mm)))
(rule "JLC inner pad hole to copper" (layer inner) (condition "A.Type == 'Pad'") (constraint hole_clearance (min 0.3mm)))
(rule "JLC copper to edge" (constraint edge_clearance (min 0.2mm)))
(rule "JLC silk to pad" (condition "B.Type == 'Pad'") (constraint silk_clearance (min 0.15mm)))
'''

# 1. DRC with JLC's rules
base = os.path.join(os.path.dirname(P), '_dfm_jlc')       # beside the project, so its footprint library resolves
txt = open(P).read().replace('(pad_to_mask_clearance 0)', '(pad_to_mask_clearance 0)\n\t\t(solder_mask_min_width 0.1)', 1)
open(base + '.kicad_pcb', 'w').write(txt)
shutil.copy(P[:-len('.kicad_pcb')] + '.kicad_pro', base + '.kicad_pro')
open(base + '.kicad_dru', 'w').write(JLC)
subprocess.run([CLI, 'pcb', 'drc', '--severity-all', '--format', 'json', '-o', base + '.json', base + '.kicad_pcb'],
               capture_output=True)
rep = json.load(open(base + '.json'))
kinds = collections.defaultdict(list)
for v in rep.get('violations', []):
    kinds[v['type']].append('; '.join(f"{i['description']} @({i['pos']['x']:.2f}, {i['pos']['y']:.2f})" for i in v.get('items', [])))
print(f"DRC with JLC rules: {sum(len(v) for v in kinds.values())} findings, {len(rep.get('unconnected_items', []))} unconnected")
for k, items in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
    print(f'  {k}: {len(items)}')
    for i in items[:int(os.environ.get('DFM_SHOW', 4))]: print(f'      {i[:170]}')

# 2. what DRC doesn't see
b = pcbnew.LoadBoard(P)
tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
pads = list(b.GetPads())
smd = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
pth = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
npth = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
print('\nSmallest features used (JLC minimum):')
print(f'  track {min(T(t.GetWidth()) for t in tracks):.3f} mm (0.09)')
print(f'  via drill / pad {min(T(v.GetDrillValue()) for v in vias):.2f} / {min(T(v.GetWidth()) for v in vias):.2f} mm (0.15 / 0.25),'
      f' pad over hole {min(T(v.GetWidth()) - T(v.GetDrillValue()) for v in vias):.2f} mm (0.10, 0.15 preferred)')
ring = lambda p: min(T(p.GetSize().x) - T(p.GetDrillSize().x), T(p.GetSize().y) - T(p.GetDrillSize().y)) / 2
pr = sorted(pth, key=ring)
print(f'  PTH drill {min(T(min(p.GetDrillSize().x, p.GetDrillSize().y)) for p in pth):.2f} mm (0.15), ring {ring(pr[0]):.3f} mm'
      f' at {pr[0].GetParentAsString()}.{pr[0].GetNumber()} (0.15, 0.20 preferred)')
if npth: print(f'  NPTH drill {min(T(min(p.GetDrillSize().x, p.GetDrillSize().y)) for p in npth):.2f} mm (0.50)')
slots = [p for p in pth + npth if p.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_OBLONG]
for p in slots:
    w, l = sorted((T(p.GetDrillSize().x), T(p.GetDrillSize().y)))
    ok = (w >= 0.35 and l >= 2 * w) if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else w >= 1.0
    if not ok: print(f'  SLOT {p.GetParentAsString()}.{p.GetNumber()} {w:.2f} x {l:.2f} mm: below JLC (plated 0.35 wide, 2x long; NPTH 1.0)')
print(f'  slots {len(slots)}, all within JLC' if all((sorted((T(p.GetDrillSize().x), T(p.GetDrillSize().y)))[0] >= (0.35 if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else 1.0)) for p in slots) else '')

inpad = []
for v in vias:
    r = v.GetWidth() // 2
    for p in smd:
        if p.GetNetname() and p.HitTest(v.GetPosition(), r):
            inpad.append((p.GetParentAsString(), p.GetNumber(), v.GetNetname(), round(T(v.GetPosition().x), 2), round(T(v.GetPosition().y), 2),
                          'centre in pad' if p.HitTest(v.GetPosition(), 0) else 'ring overlaps pad'))
print(f'\nVias in / touching SMD pads: {len(inpad)}')
for x in inpad: print('  ', *x)

webs = []
for L in (pcbnew.F_Cu, pcbnew.B_Cu):
    ps = [p for p in smd + pth if p.IsOnLayer(L)]
    for a, c in itertools.combinations(ps, 2):
        if a.GetNetname() == c.GetNetname() and a.GetNetname(): continue
        ba, bc = a.GetBoundingBox(), c.GetBoundingBox()
        g = T(max(bc.GetLeft() - ba.GetRight(), ba.GetLeft() - bc.GetRight(), bc.GetTop() - ba.GetBottom(), ba.GetTop() - bc.GetBottom()))
        if g < 0.2: webs.append((round(g, 3), f'{a.GetParentAsString()}.{a.GetNumber()}', f'{c.GetParentAsString()}.{c.GetNumber()}'))
webs.sort()
fine = collections.Counter(a.split('.')[0] for g, a, c in webs if g < 0.2)
print(f'\nNarrowest mask webs between pads of different nets (1:1 mask, so web = copper gap; JLC dam 0.10 green, 0.13 black / white):')
for g, a, c in webs[:6]: print(f'  {g:.3f} mm  {a} / {c}')
print(f'  under 0.13 mm: {sum(1 for w in webs if w[0] < 0.13)} pairs; under 0.2 mm by part: {dict(fine)}')

pitch = {}
for f in b.GetFootprints():
    ctr = [p.GetPosition() for p in f.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    if len(ctr) > 3:
        pitch[f.GetReference()] = min(T((a - c).EuclideanNorm()) for a, c in itertools.combinations(ctr, 2))
print('\nFinest-pitch parts:', ', '.join(f'{r} {d:.2f} mm' for r, d in sorted(pitch.items(), key=lambda kv: kv[1])[:8]))
bot = [f.GetReference() for f in b.GetFootprints() if f.GetLayer() == pcbnew.B_Cu]
print('Parts on B.Cu:', ', '.join(bot) if bot else 'none (single-sided assembly)')
st = txt[txt.index('(stackup'):txt.index('(copper_finish')]          # BOARD_STACKUP isn't wrapped for Python
th = sum(float(x) for x in re.findall(r'\(thickness ([0-9.]+)\)', st))
bb = b.GetBoardEdgesBoundingBox()
fin = re.search(r'copper_finish "([^"]+)"', txt).group(1)
print(f'Board {T(bb.GetWidth()):.1f} x {T(bb.GetHeight()):.1f} mm, stackup {th:.2f} mm, finish {fin}')
ol = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ol)
sharp = 0
for k in range(ol.OutlineCount()):
    for chain in [ol.Outline(k)] + [ol.Hole(k, h) for h in range(ol.HoleCount(k))]:
        n = chain.PointCount()
        for i in range(n):
            a, c, d = chain.CPoint(i - 1), chain.CPoint(i), chain.CPoint((i + 1) % n)
            u, w = c - a, d - c
            cross = u.x * w.y - u.y * w.x
            if u.EuclideanNorm() > pcbnew.FromMM(0.5) and w.EuclideanNorm() > pcbnew.FromMM(0.5) and abs(cross) > 0.5 * u.EuclideanNorm() * w.EuclideanNorm() and cross < 0:
                sharp += 1; print(f'  sharp inside corner at ({T(c.x):.2f}, {T(c.y):.2f}): the router leaves a radius there')
print(f'Outline sharp inside corners: {sharp}')
for ext in ('.kicad_pcb', '.kicad_pro', '.kicad_dru', '.kicad_prl', '.json'):
    if os.path.exists(base + ext): os.remove(base + ext)
