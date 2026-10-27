"""Netlist checks run by run.sh after ERC.
Usage: python3 checks.py <netlist> <project dir>
Every symbol pin has a footprint pad, no single-pin nets, no duplicate UUIDs,
every BOM part has an LCSC number (net ties and test pads excepted)."""
import glob
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import *

KICAD_FP = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
net_file, prj = sys.argv[1], sys.argv[2]
d = parse(open(net_file).read())[0]
bad = 0


def fail(msg):
    global bad
    bad += 1
    print('   FAIL', msg)


# component -> footprint, LCSC, lib part, BOM flag
comps = {}
for c in find(first(d, 'components'), 'comp'):
    props = {first(p, 'name')[1]: (first(p, 'value') or [None, ''])[1] for p in find(c, 'property')}
    fp = first(c, 'footprint')
    comps[first(c, 'ref')[1]] = dict(fp=fp[1] if fp else '', lcsc=props.get('LCSC', ''),
                                     part=first(first(c, 'libsource'), 'part')[1],
                                     bom='exclude_from_bom' not in props and 'dnp' not in props)

# symbol pins (every pin appears in a net, unconnected ones as unconnected-(...))
pins = {}
for n in find(first(d, 'nets'), 'net'):
    nodes = find(n, 'node')
    name = first(n, 'name')[1]
    if len(nodes) == 1 and not name.startswith('unconnected-'):
        fail('single-pin net %s (%s.%s)' % (name, first(nodes[0], 'ref')[1], first(nodes[0], 'pin')[1]))
    for nd in nodes:
        pins.setdefault(first(nd, 'ref')[1], set()).add(first(nd, 'pin')[1])

# footprint pads
pad_cache = {}


def pads(fp):
    if fp not in pad_cache:
        lib, name = fp.split(':', 1)
        base = os.path.join(prj, lib + '.pretty') if os.path.isdir(os.path.join(prj, lib + '.pretty')) \
            else os.path.join(KICAD_FP, lib + '.pretty')
        path = os.path.join(base, name + '.kicad_mod')
        pad_cache[fp] = set(re.findall(r'\(pad "([^"]+)"', open(path).read())) if os.path.exists(path) else None
    return pad_cache[fp]


for ref, c in sorted(comps.items()):
    if not c['fp']:
        fail('%s has no footprint' % ref)
        continue
    pp = pads(c['fp'])
    if pp is None:
        fail('%s footprint %s not found' % (ref, c['fp']))
        continue
    missing = pins.get(ref, set()) - pp
    if missing:
        fail('%s (%s): pins %s have no pad' % (ref, c['fp'], sorted(missing)))

# LCSC numbers on every purchased part
for ref, c in sorted(comps.items()):
    if c['bom'] and not c['lcsc'] and not re.match(r'(NetTie|TestPoint)', c['part']):
        fail('%s (%s) has no LCSC number' % (ref, c['part']))

# duplicate UUIDs across the schematic files
seen = {}
for f in glob.glob(os.path.join(prj, '*.kicad_sch')):
    for u in re.findall(r'\(uuid "([0-9a-f-]+)"\)', open(f).read()):
        if u in seen:
            fail('duplicate UUID %s (%s, %s)' % (u, os.path.basename(seen[u]), os.path.basename(f)))
        seen[u] = f

print('Checks: %d parts, %d UUIDs, %s' % (len(comps), len(seen), 'all passed' if not bad else '%d FAILED' % bad))
sys.exit(1 if bad else 0)
