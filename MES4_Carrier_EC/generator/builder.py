"""Schematic builder: template surgery + fresh placement + writer for KiCad 9 sheets."""
import uuid, re, math, os
from sx import Q, parse, dump, find, first, prop, deep
from symlib import SymDef, xform, kicad_symbol, flasher_symbols

PROJECT = 'MES4_Carrier_EC'
LIBNAME = 'MES4-Carrier-EC'
NS = uuid.UUID('6d3c1e2a-9b8f-4c51-8e0a-4ec3a1b2c0de')
_uuid_counter = [0]


def U(key=None):
    _uuid_counter[0] += 1
    return Q(str(uuid.uuid5(NS, '%s/%d' % (key or '', _uuid_counter[0]))))


def rn(lib_id):
    return lib_id.replace('MES4-Flasher:', LIBNAME + ':')


def R2(v):
    return round(float(v) + 0.0, 2)


def fmt(v):
    return '%.2f' % (round(v, 2) + 0.0)


SYMS = {}


def register_symbol(node):
    symdef('Device:R')
    SYMS[node[1]] = node
    _defs.pop(node[1], None)


def symdef(lib_id):
    if not SYMS:
        for k, v in flasher_symbols().items():
            v = deep(v)
            v[1] = Q(rn(k))
            SYMS[rn(k)] = v
    if lib_id not in SYMS:
        SYMS[lib_id] = kicad_symbol(lib_id)
    return SYMS[lib_id]


_defs = {}


def D(lib_id):
    if lib_id not in _defs:
        _defs[lib_id] = SymDef(symdef(lib_id))
    return _defs[lib_id]


def eff(size=1.27, justify=None, hide=False, bold=False):
    font = ['font', ['size', size, size]]
    if bold:
        font.append(['bold', 'yes'])
    e = ['effects', font]
    if justify:
        e.append(['justify'] + justify.split())
    if hide:
        e.append(['hide', 'yes'])
    return e


class Part:
    def __init__(self, node, tag=None):
        self.node = node
        self.tag = tag
        self.group = None

    @property
    def lib_id(self):
        return first(self.node, 'lib_id')[1]

    @lib_id.setter
    def lib_id(self, v):
        first(self.node, 'lib_id')[1] = Q(v)

    @property
    def at(self):
        a = first(self.node, 'at')
        return R2(a[1]), R2(a[2]), R2(a[3]) if len(a) > 3 else 0

    @property
    def mirror(self):
        m = first(self.node, 'mirror')
        return m[1] if m else None

    @property
    def unit(self):
        u = first(self.node, 'unit')
        return int(u[1]) if u else 1

    def p(self, num):
        d = D(self.lib_id)
        pins = d.unit_pins(self.unit)
        if num not in pins:
            cand = [n for n in d.pin_by_name(num) if n in pins]
            assert len(cand) >= 1, (self.lib_id, num)
            num = cand[0]
        px, py = pins[num][0][:2]
        X, Y, Rr = self.at
        dx, dy = xform(px, py, Rr, self.mirror)
        return (R2(X + dx), R2(Y + dy))

    def pins(self):
        out = []
        d = D(self.lib_id)
        X, Y, Rr = self.at
        for num, l in d.unit_pins(self.unit).items():
            for (px, py, a, nm, tp, un) in l:
                dx, dy = xform(px, py, Rr, self.mirror)
                out.append((num, (R2(X + dx), R2(Y + dy))))
        return out

    def get(self, name):
        p_ = prop(self.node, name)
        return p_[2] if p_ else None

    def set(self, name, value, hide=True):
        p_ = prop(self.node, name)
        if p_:
            p_[2] = Q(value)
        else:
            X, Y, _ = self.at
            idx = max(i for i, c in enumerate(self.node) if isinstance(c, list) and c[0] == 'property') + 1
            self.node.insert(idx, ['property', Q(name), Q(value), ['at', X, Y, 0], eff(hide=hide)])

    @property
    def ref(self):
        return self.get('Reference')

    def move(self, dx, dy):
        for a in _all_at(self.node):
            a[1] = R2(float(a[1]) + dx)
            a[2] = R2(float(a[2]) + dy)


def _all_at(node):
    out = []
    for c in node:
        if isinstance(c, list):
            if c and c[0] == 'at':
                out.append(c)
            else:
                out.extend(_all_at(c))
    return out


class Sheet:
    def __init__(self, name, file, comment, page, paper='A3'):
        self.name, self.file, self.comment, self.page, self.paper = name, file, comment, page, paper
        self.items = []  # non-symbol nodes
        self.parts = []
        self.uuid = U('sheet:' + name)

    # ---------------- template loading ----------------
    @classmethod
    def from_template(cls, path, name, file, comment, page):
        sh = cls(name, file, comment, page)
        root = parse(open(path).read())

        def fresh(n):
            # every copied item gets a new UUID (two sheets may come from one template)
            for c in n:
                if isinstance(c, list):
                    if c and c[0] == 'uuid' and len(c) == 2:
                        c[1] = U('tpl:' + name)
                    else:
                        fresh(c)
        fresh(root)
        for c in root:
            if not isinstance(c, list):
                continue
            if c[0] == 'symbol':
                c = deep(c)
                first(c, 'lib_id')[1] = Q(rn(first(c, 'lib_id')[1]))
                for fp in find(c, 'property'):
                    if fp[1] == 'Footprint':
                        fp[2] = Q(fp[2].replace('MES4-Flasher:', LIBNAME + ':'))
                inst = first(c, 'instances')
                if inst is not None:
                    c.remove(inst)
                old = prop(c, 'Reference')[2]
                sh.parts.append(Part(c, tag='old:' + old))
            elif c[0] in ('wire', 'junction', 'label', 'global_label', 'hierarchical_label', 'text',
                          'rectangle', 'no_connect', 'polyline', 'text_box', 'bus', 'bus_entry'):
                sh.items.append(deep(c))
        return sh

    def part_by_tag(self, tag):
        for p_ in self.parts:
            if p_.tag == tag:
                return p_
        raise KeyError(tag)

    # ---------------- geometry helpers ----------------
    def wires(self):
        out = []
        for it in self.items:
            if it[0] == 'wire':
                pts = find(first(it, 'pts'), 'xy')
                out.append((it, (R2(pts[0][1]), R2(pts[0][2])), (R2(pts[1][1]), R2(pts[1][2]))))
        return out

    def anchors(self):
        """points that connect: pins, label anchors, no_connects"""
        pts = {}
        for p_ in self.parts:
            for num, xy in p_.pins():
                pts.setdefault(xy, []).append(('pin', p_, num))
        for it in self.items:
            if it[0] in ('label', 'global_label', 'hierarchical_label', 'no_connect'):
                a = first(it, 'at')
                pts.setdefault((R2(a[1]), R2(a[2])), []).append((it[0], it))
        return pts

    @staticmethod
    def _on_seg(p_, a, b):
        (x, y), (x1, y1), (x2, y2) = p_, a, b
        if abs(x1 - x2) < 1e-6 and abs(x - x1) < 1e-6:
            return min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6
        if abs(y1 - y2) < 1e-6 and abs(y - y1) < 1e-6:
            return min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6
        return False

    def prune(self):
        """remove dangling wire ends: trim back to the last connection point, else delete (iterative)"""
        while True:
            anc = self.anchors()
            ws = self.wires()
            ends = {}
            for w, a, b in ws:
                ends[a] = ends.get(a, 0) + 1
                ends[b] = ends.get(b, 0) + 1

            def connected(e, w):
                return e in anc or ends[e] > 1 or any(
                    w2 is not w and self._on_seg(e, a2, b2) for w2, a2, b2 in ws)

            changed = False
            for w, a, b in ws:
                ca, cb = connected(a, w), connected(b, w)
                if ca and cb:
                    continue
                if not ca and not cb:
                    self.items = [it for it in self.items if it is not w]
                    changed = True
                    break
                good, bad = (a, b) if ca else (b, a)
                # interior connection points on this wire
                cands = [pt for pt in list(anc.keys()) + list(ends.keys())
                         if pt not in (a, b) and self._on_seg(pt, a, b)]
                cands += [e for w2, a2, b2 in ws if w2 is not w for e in (a2, b2)
                          if e not in (a, b) and self._on_seg(e, a, b)]
                if cands:
                    nb = min(cands, key=lambda pt: abs(pt[0] - bad[0]) + abs(pt[1] - bad[1]))
                    xy = find(first(w, 'pts'), 'xy')
                    for node_ in xy:
                        if (R2(node_[1]), R2(node_[2])) == bad:
                            node_[1], node_[2] = nb[0], nb[1]
                else:
                    self.items = [it for it in self.items if it is not w]
                changed = True
                break
            if not changed:
                return

    def remove_orphans(self):
        """drop power symbols / labels / no-connects that touch nothing"""
        while True:
            ws = self.wires()
            pts = {}
            for w, a, b in ws:
                pts[a] = pts.get(a, 0) + 1
                pts[b] = pts.get(b, 0) + 1
            pinpts = {}
            for p_ in self.parts:
                for num, xy in p_.pins():
                    pinpts.setdefault(xy, []).append(p_)

            def touched(xy, me=None):
                if xy in pts or any(self._on_seg(xy, a, b) for w, a, b in ws):
                    return True
                return any(o is not me for o in pinpts.get(xy, []))

            dead_p = [p_ for p_ in self.parts if D(p_.lib_id).power and
                      not any(touched(xy, p_) for n, xy in p_.pins())]
            dead_i = []
            for it in self.items:
                if it[0] in ('label', 'global_label', 'no_connect'):
                    a = first(it, 'at')
                    if not touched((R2(a[1]), R2(a[2]))):
                        dead_i.append(it)
            if not dead_p and not dead_i:
                return
            self.parts = [p_ for p_ in self.parts if not any(p_ is d for d in dead_p)]
            self.items = [it for it in self.items if not any(it is d for d in dead_i)]

    def clean(self):
        for _ in range(5):
            self.prune()
            self.remove_orphans()
        self.fix_junctions()

    def remove_parts(self, tags):
        tags = set(tags)
        self.parts = [p_ for p_ in self.parts if p_.tag not in tags]

    def remove_items(self, pred):
        self.items = [it for it in self.items if not pred(it)]

    def in_region(self, node, x1, y1, x2, y2):
        a = first(node, 'at')
        if a is None and node[0] == 'wire':
            pts = find(first(node, 'pts'), 'xy')
            return all(x1 <= float(p_[1]) <= x2 and y1 <= float(p_[2]) <= y2 for p_ in pts)
        if a is None and node[0] == 'rectangle':
            s, e = first(node, 'start'), first(node, 'end')
            return x1 <= float(s[1]) <= x2 and y1 <= float(s[2]) <= y2
        if a is None:
            return False
        return x1 <= float(a[1]) <= x2 and y1 <= float(a[2]) <= y2

    def move_region(self, x1, y1, x2, y2, dx, dy):
        for p_ in self.parts:
            X, Y, _ = p_.at
            if x1 <= X <= x2 and y1 <= Y <= y2:
                p_.move(dx, dy)
        for it in self.items:
            if self.in_region(it, x1, y1, x2, y2):
                for a in _all_at(it):
                    a[1] = R2(float(a[1]) + dx)
                    a[2] = R2(float(a[2]) + dy)
                for k in ('start', 'end'):
                    n = first(it, k)
                    if n:
                        n[1] = R2(float(n[1]) + dx)
                        n[2] = R2(float(n[2]) + dy)
                pts = first(it, 'pts')
                if pts:
                    for xy in find(pts, 'xy'):
                        xy[1] = R2(float(xy[1]) + dx)
                        xy[2] = R2(float(xy[2]) + dy)

    def delete_region(self, x1, y1, x2, y2):
        self.parts = [p_ for p_ in self.parts if not (x1 <= p_.at[0] <= x2 and y1 <= p_.at[1] <= y2)]
        self.items = [it for it in self.items if not self.in_region(it, x1, y1, x2, y2)]

    def fix_junctions(self):
        self.items = [it for it in self.items if it[0] != 'junction']
        ws = self.wires()
        ends = {}
        for w, a, b in ws:
            for e in (a, b):
                ends[e] = ends.get(e, 0) + 1
        pins = {}
        for p_ in self.parts:
            for num, xy in p_.pins():
                pins[xy] = pins.get(xy, 0) + 1
        jn = set()
        for pt, n in ends.items():
            through = sum(1 for w, a, b in ws if pt != a and pt != b and self._on_seg(pt, a, b))
            if n + pins.get(pt, 0) + 2 * through >= 3:
                jn.add(pt)
        for pt in sorted(jn):
            self.items.append(['junction', ['at', pt[0], pt[1]], ['diameter', 0], ['color', 0, 0, 0, 0],
                               ['uuid', U('j')]])

    # ---------------- fresh placement ----------------
    def part(self, lib_id, prefix, value, at, rot=0, mirror=None, fp='', lcsc='', desc='', tag=None,
             fields='auto', ds='~', extra=None, in_bom=True, hide_value=False, ref_off=None, val_off=None,
             unit=1, group=None):
        X, Y = R2(at[0]), R2(at[1])
        d = D(lib_id)
        node = ['symbol', ['lib_id', Q(lib_id)], ['at', X, Y, rot]]
        if mirror:
            node.append(['mirror', mirror])
        node += [['unit', unit], ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'],
                 ['on_board', 'yes'], ['dnp', 'no'], ['uuid', U('p')]]
        tang = (-rot) % 180
        ro, vo, just = self._field_pos(lib_id, rot, fields, d)
        if ref_off:
            ro = ref_off
        if val_off:
            vo = val_off
        refp = ['property', Q('Reference'), Q(prefix + '?'), ['at', R2(X + ro[0]), R2(Y + ro[1]), tang],
                eff(justify=just, hide=d.power)]
        valp = ['property', Q('Value'), Q(value), ['at', R2(X + vo[0]), R2(Y + vo[1]), tang],
                eff(justify=just, hide=hide_value)]
        node += [refp, valp]
        for k, v in (('Footprint', fp), ('Datasheet', ds), ('Description', desc)):
            node.append(['property', Q(k), Q(v), ['at', X, Y, 0], eff(hide=True)])
        if lcsc:
            node.append(['property', Q('LCSC'), Q(lcsc), ['at', X, Y, 0], eff(hide=True)])
        for k, v in (extra or {}).items():
            node.append(['property', Q(k), Q(v), ['at', X, Y, 0], eff(hide=True)])
        for num in d.unit_pins(unit):
            node.append(['pin', Q(num), ['uuid', U('pin')]])
        p_ = Part(node, tag)
        p_.group = group
        self.parts.append(p_)
        return p_

    def _field_pos(self, lib_id, rot, fields, d):
        if d.power:
            # power symbols: value beyond the symbol graphic
            up = lib_id.split(':')[1] not in ('GND', 'GND_24V')
            name = lib_id.split(':')[1]
            dist = 3.81 if rot % 180 == 0 else 3.3 + 0.55 * len(name)
            if name == 'PWR_FLAG':
                dist = 3.18 if rot % 180 == 0 else 3.3 + 0.55 * 8
            vx, vy = xform(0, dist if up else -dist, rot)
            return (0, 0), (vx, vy), None
        two_pin = len(d.pins) == 2 and lib_id.split(':')[0] == 'Device'
        vertical = (rot % 180 == 0)
        if fields == 'auto':
            if two_pin:
                if lib_id in ('Device:D', 'Device:D_Schottky', 'Device:D_Zener', 'Device:LED', 'Device:D_TVS',
                              'Device:NetTie_2'):
                    vertical = not vertical
                fields = 'right' if vertical else 'above'
            else:
                fields = 'right'
        if fields == 'right':
            return (2.54, -1.27), (2.54, 1.27), 'left'
        if fields == 'left':
            return (-2.54, -1.27), (-2.54, 1.27), 'right'
        if fields == 'above':
            return (0, -3.81), (0, 3.81), None
        if fields == 'above2':
            return (0, -5.08), (0, -2.54), None
        if fields == 'below2':
            return (0, 2.54), (0, 5.08), None
        if isinstance(fields, tuple):
            return fields[0], fields[1], fields[2] if len(fields) > 2 else 'left'
        raise ValueError(fields)

    def pwr(self, name, at, rot=None, flag=False):
        lib = {'GND': 'power:GND', '+24V': 'power:+24V', '+5V': 'power:+5V', 'PWR_FLAG': 'power:PWR_FLAG',
               'GND_24V': LIBNAME + ':GND_24V', '+3V3_MOD': LIBNAME + ':+3V3_MOD',
               '+5V_24': LIBNAME + ':+5V_24'}.get(name, name)
        if rot is None:
            rot = 0
        return self.part(lib, '#FLG' if name == 'PWR_FLAG' else '#PWR', name, at, rot, in_bom=False)

    def wire(self, *pts):
        for a, b in zip(pts, pts[1:]):
            a, b = (R2(a[0]), R2(a[1])), (R2(b[0]), R2(b[1]))
            if a == b:
                continue
            assert a[0] == b[0] or a[1] == b[1], ('non-orthogonal wire', a, b)
            self.items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                               ['stroke', ['width', 0], ['type', 'default']], ['uuid', U('w')]])

    def hv(self, a, b):
        """horizontal first, then vertical"""
        self.wire(a, (b[0], a[1]), b)

    def vh(self, a, b):
        self.wire(a, (a[0], b[1]), b)

    def label(self, name, at, rot=0, kind='label', shape='bidirectional'):
        X, Y = R2(at[0]), R2(at[1])
        if kind == 'label':
            just = {0: 'left bottom', 90: 'left bottom', 180: 'right bottom', 270: 'right bottom'}[rot]
            n = ['label', Q(name), ['at', X, Y, rot], ['fields_autoplaced', 'yes'],
                 eff(justify=just), ['uuid', U('l')]]
        else:
            just = {0: 'left', 90: 'left', 180: 'right', 270: 'right'}[rot]
            n = ['global_label', Q(name), ['shape', shape], ['at', X, Y, rot], ['fields_autoplaced', 'yes'],
                 eff(justify=just), ['uuid', U('g')],
                 ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', X, Y, 0], eff(hide=True)]]
        self.items.append(n)
        return n

    def glabel(self, name, at, rot=0, shape='bidirectional'):
        return self.label(name, at, rot, 'global', shape)

    def nc(self, at):
        self.items.append(['no_connect', ['at', R2(at[0]), R2(at[1])], ['uuid', U('nc')]])

    def text(self, s, at, size=1.27, bold=False, color=None):
        e = eff(size=size, justify='left top', bold=bold)
        if color:
            e[1].append(['color'] + list(color) + [1])
        self.items.append(['text', Q(s), ['exclude_from_sim', 'no'], ['at', R2(at[0]), R2(at[1]), 0], e,
                           ['uuid', U('t')]])

    def box(self, x1, y1, x2, y2, title=None):
        self.items.append(['rectangle', ['start', R2(x1), R2(y1)], ['end', R2(x2), R2(y2)],
                           ['stroke', ['width', 0], ['type', 'dash']], ['fill', ['type', 'none']],
                           ['uuid', U('r')]])
        if title:
            self.text(title, (x1 + 2.54, y1 + 2.54), size=2, bold=True)

    # ---------------- output ----------------
    def node(self, root_uuid, title, date, rev, company, author, resolve=None):
        used = []
        for p_ in self.parts:
            if p_.lib_id not in used:
                used.append(p_.lib_id)
        libs = ['lib_symbols'] + [deep(symdef(l)) for l in used]
        n = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')], ['generator_version', Q('9.0')],
             ['uuid', U('file:' + self.name)], ['paper', Q(self.paper)],
             ['title_block', ['title', Q(title)], ['date', Q(date)], ['rev', Q(rev)], ['company', Q(company)],
              ['comment', 1, Q(author)], ['comment', 2, Q(self.comment)]],
             libs]
        for it in self.items:
            it = deep(it)
            if resolve and it[0] == 'text':
                it[1] = Q(resolve(self, it[1]))
            n.append(it)
        path = '/%s/%s' % (root_uuid, self.uuid)
        for p_ in self.parts:
            s = deep(p_.node)
            s.append(['instances', ['project', Q(PROJECT), ['path', Q(path), ['reference', Q(p_.ref)],
                                                            ['unit', p_.unit]]]])
            n.append(s)
        n.append(['embedded_fonts', 'no'])
        return n


def assign_refs(sheets):
    """Annotate: per sheet in page order, top-to-bottom then left-to-right."""
    counters = {}
    for sh in sheets:
        def key(p_):
            X, Y, _ = p_.at
            return (round(X / 25.4), Y, X) if False else (Y // 1 if False else 0, X, Y)
        # annotate column-wise in 60 mm bands, then by y, x
        rows = getattr(sh, 'ann_rows', None)
        if rows:
            order = sorted(sh.parts, key=lambda p_: (sum(p_.at[1] > r for r in rows), p_.at[0], p_.at[1]))
        else:
            order = sorted(sh.parts, key=lambda p_: (int(p_.at[0] // 100), p_.at[1], p_.at[0]))
        groups = {}
        for p_ in order:
            r = p_.ref
            prefix = re.match(r'^#?[A-Za-z_]+', r).group(0)
            if prefix in ('#PWR', '#FLG'):
                continue
            g = getattr(p_, 'group', None)
            if g and g in groups:
                p_.set('Reference', groups[g])
                continue
            counters[prefix] = counters.get(prefix, 0) + 1
            p_.set('Reference', prefix + str(counters[prefix]))
            if g:
                groups[g] = p_.ref
    for sh in sheets:
        for p_ in sh.parts:
            r = p_.ref
            prefix = re.match(r'^#?[A-Za-z_]+', r).group(0)
            if prefix in ('#PWR', '#FLG'):
                counters[prefix] = counters.get(prefix, 0) + 1
                p_.set('Reference', '%s%03d' % (prefix, counters[prefix]))
