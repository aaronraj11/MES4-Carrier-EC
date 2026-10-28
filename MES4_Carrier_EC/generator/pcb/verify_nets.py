"""Independent connection check: schematic netlist vs board, then copper connectivity per net (tracks / vias / pads
only, no zones, so nets that rely on the In1 / In2 planes show up as split and are listed with their plane).

    kicad-cli sch export netlist --format kicadxml -o net.xml MES4_Carrier_EC.kicad_sch
    verify_nets.py <pcb> <net.xml>"""
import sys, collections, xml.etree.ElementTree as ET, pcbnew

b = pcbnew.LoadBoard(sys.argv[1]); T = pcbnew.ToMM
sch = {}                                                    # (ref, pin) -> net
for net in ET.parse(sys.argv[2]).getroot().find('nets'):
    for node in net.findall('node'): sch[(node.get('ref'), node.get('pin'))] = net.get('name')
brd = {(p.GetParentAsString(), p.GetNumber()): p.GetNetname() for p in b.GetPads() if p.GetNumber()}
bad = [(k, sch.get(k), brd.get(k)) for k in sorted(set(sch) | set(brd))
       if not (sch.get(k, '').startswith('unconnected-') and brd.get(k, '').startswith('unconnected-')) and sch.get(k) != brd.get(k)]
print(f'schematic pins {len(sch)}, board pads {len(brd)}, net mismatches {len(bad)}')
for k, s, p in bad[:30]: print('  ', k, 'sch', s, 'pcb', p)

# copper connectivity, anchor based (like KiCad): an item joins another if one of its anchors lies on the other
items = collections.defaultdict(list)
for t in b.GetTracks(): items[t.GetNetname()].append(t)
for p in b.GetPads(): items[p.GetNetname()].append(p)
zones = collections.defaultdict(set)
for z in b.Zones():
    if not z.GetIsRuleArea(): zones[z.GetNetname()].update(b.GetLayerName(L) for L in z.GetLayerSet().Seq())


def anchors(i):
    if i.GetClass() == 'PCB_TRACK': return [(i.GetStart(), i.GetLayer()), (i.GetEnd(), i.GetLayer())]
    if i.GetClass() == 'PCB_VIA': return [(i.GetPosition(), L) for L in (pcbnew.F_Cu, pcbnew.B_Cu)]
    return [(i.GetPosition(), L) for L in (pcbnew.F_Cu, pcbnew.B_Cu) if i.IsOnLayer(L)]


def on(i, L):
    if i.GetClass() == 'PCB_TRACK': return i.GetLayer() == L
    if i.GetClass() == 'PCB_VIA': return True
    return i.IsOnLayer(L)


split = []
for net, its in items.items():
    if not net or net.startswith('unconnected-'): continue
    par = list(range(len(its)))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for ia, a in enumerate(its):
        for pos, L in anchors(a):
            for ib, c in enumerate(its):
                if ia != ib and on(c, L) and c.HitTest(pos, 1000): par[f(ia)] = f(ib)
    pads = [k for k, i in enumerate(its) if i.GetClass() == 'PAD']
    groups = collections.defaultdict(list)
    for k in pads: groups[f(k)].append(f"{its[k].GetParentAsString()}.{its[k].GetNumber()}")
    if len(groups) > 1: split.append((net, len(groups), [g[:3] for g in groups.values()]))
print(f'nets split on copper (no zones): {len(split)}')
for net, n, g in sorted(split, key=lambda s: -s[1]):
    plane = ', '.join(sorted(zones.get(net, []))) or 'NO ZONE'
    print(f'  {net}: {n} islands, joined by: {plane}' + ('' if zones.get(net) else f'  <-- {g[:4]}'))
