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
# KiCad's own fuse footprints point at 3D models KiCad doesn't ship, so the fuses were missing from the board STEP.
# Project copies (same pads) use LCSC's models, kept as downloaded from EasyEDA (with their colours) in the
# 3dshapes folder: C22435908 2920 PTC (EasyEDA 3D "F2920-1", c20979b6eed84fe694c25fdbe1326c05) and C44480 Nano2
# ("FUSE-SMD_L6.1-W2.6-H2.6", ceafb183c74347baabbacc2158b065b9, centred on the board surface: lifted 1.3 mm).
KICAD_FP = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'
for name, off in (('Fuse_2920_7451Metric', (0, 0, 0)), ('Fuse_Littelfuse-NANO2-451_453', (0, 0, 1.3))):
    s = open(KICAD_FP + 'Fuse.pretty/' + name + '.kicad_mod').read()
    s = re.sub(r'\(model "[^"]*"', '(model "${KIPRJMOD}/%s.3dshapes/%s.step"' % (LIB, name), s, count=1)
    s = re.sub(r'(\(offset\s*\(xyz) [^)]*\)', r'\1 %g %g %g)' % off, s, count=1)
    open(OUT + LIB + '.pretty/' + name + '.kicad_mod', 'w').write(s)
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


# EasyEDA's STEP models don't share their VRML twins' origin, so a STEP export (which swaps the VRML for the STEP)
# put J1's M.2 socket 5.8 mm under the board, sank K5 / K6 1 mm into it and slid J16 0.4 mm. These footprints use the
# STEP directly, placed so its pins land on the pads (offsets measured from the pegs / legs / feet against the pads).
STEP_3D = {'TE_2199230-3_M.2_B-Key_4.2mm': ('PCIE-SMD_2199230-3_1', (0, 0.45, 5.76), (0, 0, 0)),
           'USB-C_Receptacle_PowerOnly_6P_C456012': ('TYPE-C-SMD_6P-L8.9-W6.8-H3.2-P1.00', (0, -2.025, 0), (0, 0, 180)),
           'RELAY-SMD_IMXXGR': ('RELAY-SMD_IMXXGR', (0, 0, 1.0), (0, 0, 0)),
           # VRML-only in the Flasher's library (KiCad's STEP export drops VRML): LCSC's STEP, fetched from EasyEDA
           # (C3031185 / C7431054), placed onto the VRML (U1 / U9's pin row incl. the missing pin 4 matches; SW2 1:1)
           'PWRM-TH_YLPTEC_URXXXXXS-6WR3': ('PWRM-TH_YLPTEC_URXXXXXS-6WR3', (0, -2.18, 12.10), (0, 0, 0)),
           'SW-TH_SHOU-HAN_SS12D10G4': ('SW-TH_SHOU-HAN_SS12D10G4', (0, 0, 2.10), (0, 0, 0))}
# The KF250NH 2P / 3P STEPs (LCSC C976556 / C976557, same origin as their VRML) and the standoffs' STEPs
# (generator/pcb/wrl2step.py from their VRML) sit beside the VRML in the 3dshapes folder: the export substitutes them.
for fn in os.listdir(OUT + LIB + '.pretty'):
    path = OUT + LIB + '.pretty/' + fn; s = open(path).read()
    if fn[:-10] in STEP_3D:
        m, off, rot = STEP_3D[fn[:-10]]; i, j = next(blocks(s, '(model '))
        xyz = lambda v: ' '.join('%g' % a for a in v)
        s = s[:i] + ('(model "${KIPRJMOD}/%s.3dshapes/%s.step"\n\t\t(offset\n\t\t\t(xyz %s)\n\t\t)\n\t\t(scale\n\t\t\t(xyz 1 1 1)\n'
                     '\t\t)\n\t\t(rotate\n\t\t\t(xyz %s)\n\t\t)\n\t)') % (LIB, m, xyz(off), xyz(rot)) + s[j:]
    cut = [(i, j) for i, j in blocks(s, '(property "LCSC Part"')] + \
          [(i, j) for i, j in blocks(s, '(fp_circle') if unprintable_dot(s[i:j])]
    for i, j in sorted(cut, reverse=True):
        s = s[:s.rindex('\n', 0, i)] + s[j:]
    open(path, 'w').write(s)
open(OUT + 'sym-lib-table', 'w').write('(sym_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr "MES4-Carrier-EC project symbols (from the MES4-Flasher)"))\n)\n' % (LIB, LIB))
open(OUT + 'fp-lib-table', 'w').write('(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")(descr "MES4-Carrier-EC project footprints (from the MES4-Flasher, checked against datasheets)"))\n)\n' % (LIB, LIB))
