"""Track tidiness audit (all nets, GND included).

    audit.py <pcb> [--bundles]

bends: 90 deg joints and acute bends (2-track nodes; 3+ tracks at 45 deg are tees) outside pads / vias.
tees: a track ending on another track's middle at 90 deg.
jogs: segments shorter than 0.3 mm that are not inside a pad / via.
--bundles: groups of parallel runs (same layer and direction, 2 mm+ side by side, < 1.2 mm apart) whose
neighbour spacings differ by more than 0.06 mm, i.e. candidates for even spacing."""
import sys, math, collections, pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM; V = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
segs = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
P = lambda p: (round(T(p.x), 3), round(T(p.y), 3))
stops = [p for p in b.GetPads()] + [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']


def in_stop(xy, layer, net):
    for s in stops:
        if s.GetNetname() != net: continue
        if s.GetClass() == 'PAD' and not s.IsOnLayer(layer): continue
        if s.HitTest(V(*xy), 0): return True
    return False


ends = collections.defaultdict(list)
for t in segs:
    a, c = P(t.GetStart()), P(t.GetEnd())
    if a == c: continue
    for p, q in ((a, c), (c, a)): ends[(p, t.GetLayer(), t.GetNetname())].append(math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])))
bends = []
for (p, L, n), angs in ends.items():
    if len(angs) < 2 or in_stop(p, L, n): continue
    for i in range(len(angs)):
        for j in range(i + 1, len(angs)):
            d = abs((angs[i] - angs[j] + 180) % 360 - 180)
            if abs(d - 90) < 1: bends.append(('90', n, p, b.GetLayerName(L)))
            elif d < 89 and len(angs) == 2: bends.append((f'acute {d:.0f}', n, p, b.GetLayerName(L)))   # 3+ = a 45 deg tee
tees = []
for t in segs:
    for e in (P(t.GetStart()), P(t.GetEnd())):
        for u in segs:
            if u is t or u.GetNetname() != t.GetNetname() or u.GetLayer() != t.GetLayer(): continue
            if e in (P(u.GetStart()), P(u.GetEnd())): continue
            if u.HitTest(V(*e), 1000) and not in_stop(e, t.GetLayer(), t.GetNetname()): tees.append((t.GetNetname(), e))
jogs = [(t.GetNetname(), P(t.GetStart()), P(t.GetEnd())) for t in segs if 0 < T(t.GetLength()) < 0.3
        and not (in_stop(P(t.GetStart()), t.GetLayer(), t.GetNetname()) and in_stop(P(t.GetEnd()), t.GetLayer(), t.GetNetname()))]
print(f'bends {len(bends)}  tees {len(tees)}  short jogs {len(jogs)}')
for x in bends: print('  bend', *x)
for x in tees: print('  tee', *x)
for x in jogs: print('  jog', *x)

if '--bundles' in sys.argv:
    long = [t for t in segs if T(t.GetLength()) > 2.0]
    def geom(t):
        a, c = P(t.GetStart()), P(t.GetEnd()); ang = math.atan2(c[1] - a[1], c[0] - a[0]) % math.pi
        return a, c, ang
    G = [geom(t) for t in long]; nb = collections.defaultdict(list)
    for i in range(len(long)):
        a1, c1, g1 = G[i]; ux, uy = math.cos(g1), math.sin(g1)
        for j in range(i + 1, len(long)):
            a2, c2, g2 = G[j]
            if long[i].GetLayer() != long[j].GetLayer() or abs(g1 - g2) > 0.01: continue
            d = abs((a2[0] - a1[0]) * -uy + (a2[1] - a1[1]) * ux)
            if d > 1.2 or d < 0.05: continue
            s1 = sorted((a1[0] * ux + a1[1] * uy, c1[0] * ux + c1[1] * uy)); s2 = sorted((a2[0] * ux + a2[1] * uy, c2[0] * ux + c2[1] * uy))
            if min(s1[1], s2[1]) - max(s1[0], s2[0]) < 2.0: continue
            nb[i].append((j, d)); nb[j].append((i, d))
    for i in nb:                                            # nearest neighbour on each side only
        a1, c1, g1 = G[i]; ux, uy = math.cos(g1), math.sin(g1); sides = {}
        for j, d in nb[i]:
            sgn = (G[j][0][0] - a1[0]) * -uy + (G[j][0][1] - a1[1]) * ux > 0
            if sgn not in sides or d < sides[sgn][1]: sides[sgn] = (j, d)
        nb[i] = list(sides.values())
    seen = set()
    for i in nb:
        if i in seen: continue
        comp, st = [], [i]
        while st:
            k = st.pop()
            if k in seen: continue
            seen.add(k); comp.append(k); st += [j for j, _ in nb[k]]
        ds = sorted({round(d, 2) for k in comp for _, d in nb[k]})
        nets = sorted({long[k].GetNetname().split('/')[-1] for k in comp})
        if len(comp) >= 3 and max(ds) - min(ds) > 0.06 and min(ds) < 0.9:
            xs = [p for k in comp for p in G[k][:2]]
            print(f'bundle {b.GetLayerName(long[comp[0]].GetLayer())} {len(comp)} runs  x {min(x for x, _ in xs):.1f}-{max(x for x, _ in xs):.1f}'
                  f' y {min(y for _, y in xs):.1f}-{max(y for _, y in xs):.1f}  spacings {ds}  nets {nets[:8]}')
