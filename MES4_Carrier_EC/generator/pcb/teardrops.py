"""Teardrops (KiCad 9's generator isn't reachable from Python, so this builds the same straight teardrops). Run last.

    teardrops.py <pcb>

Every track end that sits in a via or pad, on any net but GND (GND ends join the pours), gets a teardrop zone on the
track's layer when the track is narrower than 90 % of the via / pad across it: base on the via circle or at the pad edge
the track leaves by, centred on the track (the narrower side of the via / pad sets both halves, so a track entering
off-centre still gets a symmetric teardrop), length half the via / pad size (at most 1 mm, and never past the
segment), tapering to the track width. They are real KiCad teardrop zones (named and tagged as KiCad saves its own, filled with the board's clearances), and
pads / vias get their teardrop flag set, so KiCad's own teardrop tool regenerates the same thing from the GUI."""
import sys, math, pcbnew

P = sys.argv[1]; b = pcbnew.LoadBoard(P); mm, T = pcbnew.FromMM, pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
NAME = '$teardrop_padvia$'                                  # how KiCad names its own pad / via teardrop zones
segs = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetname() != 'GND']
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() != 'GND']
pads = [p for p in b.GetPads() if p.GetNetname() and p.GetNetname() != 'GND']
for it in vias + pads: it.SetTeardropsEnabled(True)


def drop(net, layer, pts):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet(net)); z.SetZoneName(NAME)
    z.SetMinThickness(mm(0.1)); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetAssignedPriority(30)
    z.Outline().NewOutline()
    for x, y in pts: z.Outline().Append(mm(x), mm(y))
    b.Add(z)


n_v = n_p = 0
for t in segs:
    L = t.GetLayer(); w = T(t.GetWidth())
    for e, o in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
        ex, ey, ox, oy = T(e.x), T(e.y), T(o.x), T(o.y); seg = math.hypot(ox - ex, oy - ey)
        if seg < 0.2: continue
        ux, uy = (ox - ex) / seg, (oy - ey) / seg; nx, ny = -uy, ux
        hit = next((v for v in vias if v.GetNetname() == t.GetNetname() and v.HitTest(e, 1000)), None)
        if hit:                                             # via: base on the circle, across the via's centre
            r = T(hit.GetWidth()) / 2; cx, cy = T(hit.GetPosition().x), T(hit.GetPosition().y)
            if w >= 0.9 * 2 * r: continue
            lat = (cx - ex) * nx + (cy - ey) * ny            # base on the track's own axis, not the via centre
            if abs(lat) > 0.6 * r: continue
            bx, by = cx - nx * lat, cy - ny * lat; h = math.sqrt(r * r - lat * lat) * 0.98
            d = (ex - bx) * ux + (ey - by) * uy
            ln = min(1.0, r, seg + d - h - 0.05)            # 0.5 x diameter, never past the segment
            if ln < 0.1 or h < w / 2 + 0.02: continue
            tx, ty = bx + ux * (h + ln), by + uy * (h + ln)
            drop(t.GetNetname(), L, [(bx + nx * h, by + ny * h), (tx + nx * w / 2, ty + ny * w / 2),
                                     (tx - nx * w / 2, ty - ny * w / 2), (bx - nx * h, by - ny * h)])
            n_v += 1; continue
        pad = next((p for p in pads if p.GetNetname() == t.GetNetname() and p.IsOnLayer(L) and p.HitTest(e, 0)), None)
        if not pad: continue
        k = 0.0                                             # walk out along the track to the pad edge
        while k < seg and pad.HitTest(V(ex + ux * k, ey + uy * k), 0): k += 0.02
        if k >= seg - 0.1: continue
        sx, sy = ex + ux * (k - 0.06), ey + uy * (k - 0.06)  # just inside the edge: measure the pad across the track
        a = [0.0, 0.0]
        for i, s in enumerate((1, -1)):
            while a[i] < 3 and pad.HitTest(V(sx + nx * s * (a[i] + 0.02), sy + ny * s * (a[i] + 0.02)), 0): a[i] += 0.02
        h = min(a)                                          # symmetric about the track: the narrower side sets both
        if w >= 0.9 * 2 * h or h < w / 2 + 0.02: continue
        size = min(T(pad.GetSize().x), T(pad.GetSize().y))
        ln = min(1.0, 0.5 * size, seg - k - 0.05)
        if ln < 0.1: continue
        tx, ty = ex + ux * (k + ln), ey + uy * (k + ln)
        drop(t.GetNetname(), L, [(sx + nx * h, sy + ny * h), (tx + nx * w / 2, ty + ny * w / 2),
                                 (tx - nx * w / 2, ty - ny * w / 2), (sx - nx * h, sy - ny * h)])
        n_p += 1

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
# the TEARDROP_TYPE enum isn't wrapped for Python, so tag the zones in the file the way KiCad saves its own teardrops
txt = open(P).read(); tag = f'(name "{NAME}")'
txt = txt.replace(tag, tag + '\n\t\t(attr\n\t\t\t(teardrop\n\t\t\t\t(type padvia)\n\t\t\t)\n\t\t)')
open(P, 'w').write(txt)
print('teardrops: vias', n_v, ' pads', n_p)
