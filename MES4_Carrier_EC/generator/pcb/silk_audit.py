"""Silkscreen audit: reference labels that crowd each other, sit on pads / vias / other parts' outlines, sit far from
their part, or run off the board; silk strokes too thin to print (JLC: 0.15 mm).

    silk_audit.py <pcb>"""
import sys, pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM
box = lambda bb: (T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()))
gap = lambda a, c: max(c[0] - a[2], a[0] - c[2], c[1] - a[3], a[1] - c[3])          # < 0: overlap
refs = {f.GetReference(): (f, box(f.Reference().GetEffectiveTextShape().BBox())) for f in b.GetFootprints()   # glyph extents
        if f.Reference().IsVisible() and f.Reference().GetLayerName() == 'F.Silkscreen'}
pads = [(p.GetParentAsString(), box(p.GetBoundingBox())) for p in b.GetPads() if p.IsOnLayer(pcbnew.F_Cu) or p.GetDrillSize().x]
vias = [box(t.GetBoundingBox()) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
lines = [(f.GetReference(), box(g.GetBoundingBox())) for f in b.GetFootprints() for g in f.GraphicalItems()
         if g.GetLayerName() == 'F.Silkscreen' and g.GetClass() != 'PCB_FIELD']
edge = box(b.GetBoardEdgesBoundingBox())
issues = {}
names = sorted(refs)
for i, a in enumerate(names):
    ra = refs[a][1]
    for c in names[i + 1:]:
        d = gap(ra, refs[c][1])
        if d < 0.2: issues.setdefault(a, []).append(f'crowds {c} ({d:+.2f})'); issues.setdefault(c, []).append(f'crowds {a} ({d:+.2f})')
    on = sorted({o for o, pb in pads if gap(ra, pb) < 0.1})
    if on: issues.setdefault(a, []).append('on pads of ' + ','.join(on))
    nv = sum(1 for vb in vias if gap(ra, vb) < 0.0)
    if nv: issues.setdefault(a, []).append(f'over {nv} via(s)')
    ol = sorted({o for o, lb in lines if o != a and gap(ra, lb) < 0.0})
    if ol: issues.setdefault(a, []).append('on outline of ' + ','.join(ol))
    fb = box(refs[a][0].GetBoundingBox(False, False))
    if gap(ra, fb) > 2.5: issues.setdefault(a, []).append(f'far from part ({gap(ra, fb):.1f} mm)')
    if ra[0] < edge[0] + 0.3 or ra[1] < edge[1] + 0.3 or ra[2] > edge[2] - 0.3 or ra[3] > edge[3] - 0.3: issues.setdefault(a, []).append('at board edge')
thin = [(f.GetReference(), g.GetShapeStr(), round(T(g.GetWidth()), 2)) for f in b.GetFootprints() for g in f.GraphicalItems()
        if g.GetLayerName() == 'F.Silkscreen' and g.GetClass() == 'PCB_SHAPE' and 0 < T(g.GetWidth()) < 0.15
        and not (hasattr(g, 'IsSolidFill') and g.IsSolidFill())]
thin += [('board', g.GetShapeStr(), round(T(g.GetWidth()), 2)) for g in b.GetDrawings()
         if g.GetLayerName() == 'F.Silkscreen' and g.GetClass() == 'PCB_SHAPE' and 0 < T(g.GetWidth()) < 0.15 and not g.IsSolidFill()]
print(f'refs {len(refs)}, with issues {len(issues)}; thin silk strokes {len(thin)}')
for r in sorted(issues): print(f'  {r:6} ' + '; '.join(issues[r]))
for t in thin: print('  thin', *t)
