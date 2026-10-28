"""Quick clearance probe for hand-routing (a pre-check before DRC; DRC stays the judge).

    probe.py <pcb> path <net> <w> F:x,y;x,y;...  [B:x,y;...]   test a path (layer runs, vias between runs)
    probe.py <pcb> rows <layer> <w> <x0> <x1> <y0> <y1> [step]   y values where a straight run x0 -> x1 is clear
    probe.py <pcb> cols <layer> <w> <y0> <y1> <x0> <x1> [step]   x values where a straight run y0 -> y1 is clear

Clearance 0.2 to copper of other nets on the layer, 0.25 to drilled holes; vias are 0.6 / 0.3."""
import sys, pcbnew

mm, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
LAY = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}
b = pcbnew.LoadBoard(sys.argv[1]); mode = sys.argv[2]


def items(layer, net):
    out = []
    for t in b.GetTracks():
        if t.GetNetname() == net: continue
        if t.GetClass() == 'PCB_VIA' or t.GetLayer() == layer: out.append(t)
    for p in b.GetPads():
        if p.GetNetname() == net and net: continue
        if p.IsOnLayer(layer) or p.GetDrillSize().x > 0: out.append(p)
    return out


def blockers(layer, net, pts, half):
    """items within clearance of the polyline pts (list of (x, y)) for a copper half-width half"""
    cand = items(layer, net); hits = {}
    for a, c in zip(pts, pts[1:]) if len(pts) > 1 else [(pts[0], pts[0])]:
        n = max(1, int(((c[0] - a[0]) ** 2 + (c[1] - a[1]) ** 2) ** 0.5 / 0.05))
        x0, x1 = min(a[0], c[0]) - 3, max(a[0], c[0]) + 3; y0, y1 = min(a[1], c[1]) - 3, max(a[1], c[1]) + 3
        box = lambda i: i.GetBoundingBox()                  # bounding box, not the anchor: long tracks start far away
        near = [i for i in cand if T(box(i).GetLeft()) < x1 and T(box(i).GetRight()) > x0
                and T(box(i).GetTop()) < y1 and T(box(i).GetBottom()) > y0]
        for k in range(n + 1):
            x, y = a[0] + (c[0] - a[0]) * k / n, a[1] + (c[1] - a[1]) * k / n
            for i in near:
                if id(i) in hits: continue
                hole = i.GetClass() == 'PAD' and not i.IsOnLayer(layer)
                acc = mm(half + (0.25 if hole else 0.2))
                if i.HitTest(V(x, y), acc): hits[id(i)] = (i, round(x, 2), round(y, 2))
    return list(hits.values())


def name(i):
    if i.GetClass() == 'PAD': return f"pad {i.GetParentAsString()}.{i.GetNumber()} [{i.GetNetname()}]"
    if i.GetClass() == 'PCB_VIA': return f"via [{i.GetNetname()}] {T(i.GetPosition().x):.2f},{T(i.GetPosition().y):.2f}"
    return f"track [{i.GetNetname()}] {T(i.GetStart().x):.2f},{T(i.GetStart().y):.2f}-{T(i.GetEnd().x):.2f},{T(i.GetEnd().y):.2f}"


if mode == 'path':
    net, w = sys.argv[3], float(sys.argv[4]); runs = []
    for arg in sys.argv[5:]:
        lc, s = arg.split(':', 1); runs.append((lc, [tuple(map(float, p.split(','))) for p in s.split(';')]))
    bad = 0
    for k, (lc, pts) in enumerate(runs):
        for i, x, y in blockers(LAY[lc], net, pts, w / 2):
            print(f"{lc}: {name(i)} near {x},{y}"); bad += 1
        if k < len(runs) - 1:                               # via at the run's last point, both layers
            for L in 'FB':
                for i, x, y in blockers(LAY[L], net, [pts[-1]], 0.3):
                    print(f"via {pts[-1]} {L}: {name(i)}"); bad += 1
    print('clear' if not bad else f'{bad} conflicts')
else:
    lc, w = sys.argv[3], float(sys.argv[4]); a0, a1, b0, b1 = map(float, sys.argv[5:9])
    step = float(sys.argv[9]) if len(sys.argv) > 9 else 0.1
    ok, v = [], b0
    while v <= b1 + 1e-9:
        pts = [(a0, v), (a1, v)] if mode == 'rows' else [(v, a0), (v, a1)]
        if not blockers(LAY[lc], '', pts, w / 2): ok.append(round(v, 2))
        v += step
    runs, cur = [], []
    for v in ok:
        if cur and v - cur[-1] > step * 1.5: runs.append(cur); cur = []
        cur.append(v)
    if cur: runs.append(cur)
    print(' '.join(f"{r[0]}-{r[-1]}" for r in runs) or 'none')
