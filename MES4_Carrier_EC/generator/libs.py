import re, os, shutil, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sx import parse, dump, find, first, Q
FL = '/Users/aaron/Desktop/MES4 Ecosystem/MES4-Flasher/'
OUT = '/Users/aaron/Desktop/MES4 Ecosystem/MES4-Carrier-EC/MES4_Carrier_EC/'
LIB = 'MES4-Carrier-EC'
# which project symbols / footprints are used
used_sym, used_fp = set(), set()
for f in glob.glob(OUT + '*.kicad_sch'):
    s = open(f).read()
    used_sym |= set(re.findall(r'\(lib_id "%s:([^"]+)"' % LIB, s))
    used_fp |= set(re.findall(r'"Footprint" "%s:([^"]+)"' % LIB, s))
print('symbols', sorted(used_sym)); print('footprints', sorted(used_fp))
# symbol library: rebuilt from the copies embedded in the sheets, so they match exactly
syms = {}
for f in sorted(glob.glob(OUT + '*.kicad_sch')):
    r = parse(open(f).read())
    for sy in find(first(r, 'lib_symbols') or [], 'symbol'):
        if sy[1].startswith(LIB + ':') and sy[1] not in syms:
            sy[1] = Q(sy[1].split(':', 1)[1])
            syms[sy[1]] = sy
lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('kicad_symbol_editor')], ['generator_version', Q('9.0')]]
lib += [syms[k] for k in sorted(syms)]
open(OUT + LIB + '.kicad_sym', 'w').write(dump(lib) + '\n')
# footprints + 3D models
os.makedirs(OUT + LIB + '.pretty', exist_ok=True)
os.makedirs(OUT + LIB + '.3dshapes', exist_ok=True)
import can_parts
can_parts.write_footprint(OUT + LIB + '.pretty')
import aux_parts
aux_parts.write_footprints(OUT + LIB + '.pretty', OUT + LIB + '.3dshapes')
for fp in sorted(used_fp):
    src = FL + 'MES4-Flasher.pretty/' + fp + '.kicad_mod'
    if not os.path.exists(src):
        continue  # project-made footprint (written above)
    s = open(src).read()
    for m in re.findall(r'\(model "([^"]+)"', s):
        base = os.path.basename(m)
        if 'MES4-Flasher.3dshapes' in m:
            for ext in ('.step', '.wrl'):
                cand = FL + 'MES4-Flasher.3dshapes/' + os.path.splitext(base)[0] + ext
                if os.path.exists(cand):
                    shutil.copy(cand, OUT + LIB + '.3dshapes/')
        print('  model', fp, m)
    s = s.replace('MES4-Flasher.3dshapes', LIB + '.3dshapes').replace('MES4-Flasher:', LIB + ':')
    open(OUT + LIB + '.pretty/' + fp + '.kicad_mod', 'w').write(s)
# Two clean-ups on the imported footprints, so the board (see generator/pcb/silk.py, parts_sync.py) matches the library:
# - EasyEDA imports carry an "LCSC Part" field. The Fabrication Toolkit reads it ahead of the symbol's "LCSC", so a
#   stale one overrides the schematic (review B1: U9 / SW2): keep LCSC numbers on the symbols only.
# - their 0.06 mm pin-1 dots (radius 0.03) are far under JLC's 0.15 mm silk minimum and never print.
def blocks(s, head):
    """(start, end) of every top-level-in-footprint block that starts with head."""
    i = s.find(head)
    while i >= 0:
        d = 0
        for j in range(i, len(s)):
            d += {'(': 1, ')': -1}.get(s[j], 0)
            if d == 0: break
        yield i, j + 1
        i = s.find(head, j + 1)


def unprintable_dot(b):
    c, e, w = (re.search(r'\((center|end|width) ([-\d.]+)(?: ([-\d.]+))?\)'.replace('center|end|width', k), b) for k in ('center', 'end', 'width'))
    r = ((float(e[2]) - float(c[2])) ** 2 + (float(e[3]) - float(c[3])) ** 2) ** 0.5
    return 'SilkS"' in b and '(fill yes)' not in b and r < 0.1 and float(w[2]) < 0.1


for fn in os.listdir(OUT + LIB + '.pretty'):
    path = OUT + LIB + '.pretty/' + fn; s = open(path).read()
    cut = [(i, j) for i, j in blocks(s, '(property "LCSC Part"')] + \
          [(i, j) for i, j in blocks(s, '(fp_circle') if unprintable_dot(s[i:j])]
    for i, j in sorted(cut, reverse=True):
        s = s[:s.rindex('\n', 0, i)] + s[j:]
    open(path, 'w').write(s)
open(OUT + 'sym-lib-table', 'w').write('(sym_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr "MES4-Carrier-EC project symbols (from the MES4-Flasher)"))\n)\n' % (LIB, LIB))
open(OUT + 'fp-lib-table', 'w').write('(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "MES4-Carrier-EC project footprints (from the MES4-Flasher, checked against datasheets)"))\n)\n' % (LIB, LIB))
