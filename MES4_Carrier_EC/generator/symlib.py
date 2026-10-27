"""Symbol definitions (embedded-style, flattened) and pin geometry."""
import os, math
from sx import parse, dump, find, first, prop, deep, Q

KILIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
FLASHER = '/Users/aaron/Desktop/MES4 Ecosystem/MES4-Flasher'

_cache = {}


def _load_kicad_lib(lib):
    if lib not in _cache:
        root = parse(open(os.path.join(KILIB, lib + '.kicad_sym')).read())
        _cache[lib] = {s[1]: s for s in find(root, 'symbol')}
    return _cache[lib]


def _rename_units(sym, old, new):
    for sub in find(sym, 'symbol'):
        n = sub[1]
        if n.startswith(old + '_'):
            sub[1] = Q(new + n[len(old):])


def kicad_symbol(lib_id):
    """Return a flattened, embedded-style copy of a KiCad library symbol."""
    lib, name = lib_id.split(':')
    syms = _load_kicad_lib(lib)
    s = deep(syms[name])
    ext = first(s, 'extends')
    if ext:
        parent = kicad_symbol(lib + ':' + ext[1])
        base = deep(parent)
        pname = base[1].split(':')[1]
        # replace properties with the child's
        base[:] = [c for c in base if not (isinstance(c, list) and c and c[0] == 'property')]
        props = find(s, 'property')
        # insert child props after the flags
        idx = max(i for i, c in enumerate(base) if isinstance(c, list) and c[0] in
                  ('on_board', 'in_bom', 'exclude_from_sim', 'pin_names', 'pin_numbers')) + 1
        base[idx:idx] = props
        _rename_units(base, pname, name)
        s = base
    s[1] = Q(lib_id)
    return s


def flasher_symbols():
    out = {}
    for f in ['Main', 'Power', 'Relays', 'Sensors', 'LoadCell']:
        root = parse(open(os.path.join(FLASHER, f + '.kicad_sch')).read())
        for s in find(first(root, 'lib_symbols'), 'symbol'):
            out.setdefault(s[1], s)
    return out


class SymDef:
    def __init__(self, node):
        self.node = node
        self.lib_id = node[1]
        self.pins = {}  # number -> (x, y, angle, name, type)
        self.power = first(node, 'power') is not None
        for sub in find(node, 'symbol'):
            parts = sub[1].rsplit('_', 2)
            unit, body = int(parts[1]), int(parts[2])
            if body not in (0, 1):
                continue
            for p in find(sub, 'pin'):
                at = first(p, 'at')
                num = first(p, 'number')[1]
                nm = first(p, 'name')[1]
                self.pins.setdefault(num, []).append((float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, nm, p[1], unit))

    def unit_pins(self, unit):
        return {n: [x for x in l if x[5] in (0, unit)] for n, l in self.pins.items()
                if any(x[5] in (0, unit) for x in l)}

    def pin_by_name(self, name):
        return [n for n, l in self.pins.items() if any(x[3] == name for x in l)]


def xform(px, py, rot, mirror=None):
    """Library pin coords -> schematic offset (y down)."""
    x, y = px, -py
    a = math.radians(rot)
    c, s = round(math.cos(a)), round(math.sin(a))
    xr = x * c + y * s
    yr = -x * s + y * c
    if mirror == 'x':
        yr = -yr
    elif mirror == 'y':
        xr = -xr
    return xr, yr
