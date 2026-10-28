"""Winch_48V isolation check: every winch pad / track / via against all other copper on the same layer
(F.Cu, B.Cu, In1 / In2 planes). Unused contact pins of K5 / K6 count as part of the relay. Prints anything
closer than 2 mm."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm, T = pcbnew.FromMM, pcbnew.ToMM
LAYERS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
win = lambda n: n.startswith('/Winch/') or n.startswith('unconnected-(K5') or n.startswith('unconnected-(K6')
items = []
for f in b.GetFootprints():
    for p in f.Pads(): items.append((p, f'{f.GetReference()}.{p.GetNumber()}'))
for t in b.GetTracks(): items.append((t, 'via' if t.GetClass() == 'PCB_VIA' else 'track'))
zones = [z for z in b.Zones() if not z.GetIsRuleArea()]
bad = 0
for a, an in items:
    if not win(a.GetNetname()): continue
    for L in LAYERS:
        if not a.IsOnLayer(L): continue
        sa = a.GetEffectiveShape(L)
        for o, on in items:
            if win(o.GetNetname()) or not o.IsOnLayer(L) or o.GetNetname() == '' and on.startswith(('H', 'J18')): continue
            if sa.Collide(o.GetEffectiveShape(L), mm(2.0)):
                bad += 1; print(f'{pcbnew.LayerName(L)}: {an} {a.GetNetname()} @({T(a.GetPosition().x):.2f},{T(a.GetPosition().y):.2f}) <2mm {on} {o.GetNetname()}')
        for z in zones:
            if z.IsOnLayer(L) and z.GetFilledPolysList(L).Collide(sa, mm(2.0)):
                bad += 1; print(f'{pcbnew.LayerName(L)}: {an} {a.GetNetname()} @({T(a.GetPosition().x):.2f},{T(a.GetPosition().y):.2f}) <2mm zone {z.GetNetname()}')
print('winch isolation issues:', bad)
