"""Helpers for the hand-routed PCB scripts (route_rails.py, route_winch.py, ...).

A path is (net, width, runs); runs = [('F'|'B', [(x, y), ...]), ...]. A via (0.6 / 0.3) joins
consecutive runs at the last point of a run; a run with a single point only places that via.
save() gives a route that ends on the middle of another track a vertex there (KiCad wants an
anchor), refills the zones and writes the board."""
import math, pcbnew

mm, T = pcbnew.FromMM, pcbnew.ToMM
LAY = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}


def d_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


class Board:
    def __init__(self, path):
        self.file = path; self.b = pcbnew.LoadBoard(path); self.added = []

    def path(self, net, w, runs):
        b = self.b; ni = b.FindNet(net); V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
        for k, (lc, pts) in enumerate(runs):
            for a, c in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(w)); t.SetLayer(LAY[lc]); t.SetNet(ni)
                b.Add(t); self.added.append(t)
            if k < len(runs) - 1:
                v = pcbnew.PCB_VIA(b); v.SetPosition(V(*pts[-1])); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(ni); b.Add(v)

    def _split_tees(self):
        for t0 in self.added:
            for q in (t0.GetStart(), t0.GetEnd()):
                px, py = T(q.x), T(q.y)
                for t in list(self.b.GetTracks()):
                    if t.GetClass() != 'PCB_TRACK' or t is t0 or t.GetLayer() != t0.GetLayer() or t.GetNetname() != t0.GetNetname(): continue
                    a, c = t.GetStart(), t.GetEnd(); ax, ay, cx, cy = T(a.x), T(a.y), T(c.x), T(c.y)
                    if min(math.hypot(px - ax, py - ay), math.hypot(px - cx, py - cy)) < 0.005 or d_seg(px, py, ax, ay, cx, cy) > 0.005: continue
                    n = pcbnew.PCB_TRACK(self.b); n.SetStart(q); n.SetEnd(c); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNet(t.GetNet())
                    t.SetEnd(q); self.b.Add(n); break

    def save(self):
        self._split_tees()
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        pcbnew.SaveBoard(self.file, self.b)
