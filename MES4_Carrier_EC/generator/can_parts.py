"""Custom CAN connector parts: 4-port RJ45 symbol + footprint (HCTL HC-RJ45-059-4-4, LCSC C3000204)."""
from sx import Q, dump
from builder import U, LIBNAME

RJ_NAME = 'RJ45x4_CAN'
RJ_FP = 'RJ45_HCTL_HC-RJ45-059-4-4_1x4_Horizontal'
RJ_LCSC = 'C3000204'


def _eff(hide=False, justify=None):
    e = ['effects', ['font', ['size', 1.27, 1.27]]]
    if justify:
        e.append(['justify', justify])
    if hide:
        e.append(['hide', 'yes'])
    return e


def rj45x4_symbol():
    """4 units, one per port (CiA 303-1 / T568B pins 1-3 named), shield pins on unit 1."""
    n = RJ_NAME
    sym = ['symbol', Q(LIBNAME + ':' + n), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
           ['in_bom', 'yes'], ['on_board', 'yes'],
           ['property', Q('Reference'), Q('J'), ['at', -7.62, 13.97, 0], _eff(justify='left')],
           ['property', Q('Value'), Q('HC-RJ45-059-4-4'), ['at', -7.62, -16.51, 0], _eff(justify='left')],
           ['property', Q('Footprint'), Q(LIBNAME + ':' + RJ_FP), ['at', 0, 0, 0], _eff(hide=True)],
           ['property', Q('Datasheet'), Q('https://www.lcsc.com/product-detail/C3000204.html'), ['at', 0, 0, 0],
            _eff(hide=True)],
           ['property', Q('Description'), Q('RJ45 8P8C jack, 1x4 ganged, shielded, no magnetics, no LEDs, '
                                             'used for CAN (CiA 303-1: 1 CAN_H, 2 CAN_L, 3 GND)'),
            ['at', 0, 0, 0], _eff(hide=True)],
           ['symbol', Q(n + '_0_1'),
            ['rectangle', ['start', -7.62, 12.7], ['end', 7.62, -10.16],
             ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]]]
    names = {1: 'CANH', 2: 'CANL', 3: 'GND'}
    for u in range(1, 5):
        sub = ['symbol', Q('%s_%d_1' % (n, u))]
        sub.append(['text', Q('PORT %d' % u), ['at', 3.556, 0, 0],
                    ['effects', ['font', ['size', 1.27, 1.27]]]])
        for k in range(1, 9):
            num = 8 * (u - 1) + k
            sub.append(['pin', 'passive', 'line', ['at', -10.16, 10.16 - 2.54 * (k - 1), 0], ['length', 2.54],
                        ['name', Q(names.get(k, str(k))), ['effects', ['font', ['size', 1.27, 1.27]]]],
                        ['number', Q(str(num)), ['effects', ['font', ['size', 1.27, 1.27]]]]])
        if u == 1:
            for num, x in (('33', -2.54), ('34', 2.54)):
                sub.append(['pin', 'passive', 'line', ['at', x, -12.7, 90], ['length', 2.54],
                            ['name', Q('SH'), ['effects', ['font', ['size', 1.27, 1.27]]]],
                            ['number', Q(num), ['effects', ['font', ['size', 1.27, 1.27]]]]])
        sym.append(sub)
    sym.append(['embedded_fonts', 'no'])
    return sym


# Pads from the HCTL HC-RJ45-059-4-4 drawing ("PCB参考图", LCSC C3000204 PDF), pad 1 = origin:
# 32 x Ø1.0 contacts, 1.27 mm pitch, rows 2.54 mm apart, ports 14.0 mm apart; 2 x Ø3.2 pegs 53.5 mm apart,
# 8.89 mm in front of the rear row; 5 x Ø1.5 shield pins: rear row 10.25 mm behind the pegs, 14.0 mm apart,
# front pair 4.4 mm in front of the pegs, 59.0 mm apart. All centred on the contact field.
# (The JLC/EasyEDA library part has rows 2.50 mm apart, 13.97 mm ports and Ø3.5 pegs: not used.)
# Silk / Fab outline still from the library part (10-mil units).
_O = (3999.378, 2970.571)


def _mm(x, y):
    return round((x - _O[0]) * 0.254, 3), round((y - _O[1]) * 0.254, 3)


def rj45x4_footprint():
    def pad(num, kind, shape, at, size, drill, layers=('*.Cu', '*.Mask')):
        return ['pad', Q(num), kind, shape, ['at', at[0], at[1]], ['size', size, size], ['drill', drill],
                ['layers'] + [Q(l) for l in layers], ['remove_unused_layers', 'no'], ['uuid', U('fp')]]

    def line(a, b, layer, w):
        return ['fp_line', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']],
                ['layer', Q(layer)], ['uuid', U('fp')]]

    def rect(a, b, layer, w):
        return ['fp_rect', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']],
                ['fill', 'no'], ['layer', Q(layer)], ['uuid', U('fp')]]

    fp = ['footprint', Q(RJ_FP), ['version', 20241229], ['generator', Q('pcbnew')], ['generator_version', Q('9.0')],
          ['layer', Q('F.Cu')],
          ['descr', Q('HCTL HC-RJ45-059-4-4: RJ45 1x4 ganged, shielded, no magnetics, no LEDs, right angle, THT '
                      '(LCSC C3000204). Pads and drills from the HCTL drawing. Port front face 10.6 mm in front '
                      'of the pegs (17.0 mm in front of the pin-1 row).')],
          ['tags', Q('RJ45 8P8C 1x4 quad ganged shielded CAN')],
          ['property', Q('Reference'), Q('REF**'), ['at', 25.4, -6.6, 0], ['layer', Q('F.SilkS')], ['uuid', U('fp')],
           ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]],
          ['property', Q('Value'), Q(RJ_FP), ['at', 25.4, 18.5, 0], ['layer', Q('F.Fab')], ['uuid', U('fp')],
           ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]],
          ['property', Q('Datasheet'), Q('https://www.lcsc.com/product-detail/C3000204.html'), ['at', 0, 0, 0],
           ['layer', Q('F.Fab')], ['hide', 'yes'], ['uuid', U('fp')],
           ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]],
          ['property', Q('Description'), Q('RJ45 1x4, shielded, no magnetics'), ['at', 0, 0, 0],
           ['layer', Q('F.Fab')], ['hide', 'yes'], ['uuid', U('fp')],
           ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]],
          ['attr', 'through_hole']]
    # body outline (library silk extents) on Fab, courtyard around body + shield pads
    x0, y0 = _mm(3982.8428, 2954.0356)
    x1, y1 = _mm(4215.9132, 3037.5)
    fp.append(rect((x0, y0), (x1, y1), 'F.Fab', 0.1))
    fp.append(['fp_text', 'user', Q('PCB edge / port fronts'), ['at', 25.4, 16.0, 0], ['layer', Q('F.Fab')],
               ['uuid', U('fp')], ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]]]])
    fp.append(['fp_text', 'user', Q('${REFERENCE}'), ['at', 25.4, 8.5, 0], ['layer', Q('F.Fab')], ['uuid', U('fp')],
               ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]])
    fp.append(rect((-5.5, -5.5), (56.3, 17.25), 'F.CrtYd', 0.05))
    # silkscreen: the library's outline with gaps around the shield pads
    silk = [[(3982.8428, 3007.6672), (3982.8428, 2954.0356), (4038.8367, 2954.0356)],
            [(4215.9132, 3018.5138), (4215.9132, 3037.5), (3982.8428, 3037.5), (3982.8428, 3018.5138)],
            [(4159.9193, 2954.0356), (4215.9132, 2954.0356), (4215.9132, 3007.6672)],
            [(4104.8013, 2954.0356), (4149.0727, 2954.0356)],
            [(4049.7718, 2954.0356), (4093.9547, 2954.0356)]]
    for poly in silk:
        pts = [_mm(*p) for p in poly]
        for a, b in zip(pts, pts[1:]):
            fp.append(line(a, b, 'F.SilkS', 0.12))
    fp.append(line((-1.0, 1.5), (1.0, 1.5), 'F.SilkS', 0.12))  # pin 1 mark
    # 32 contacts (pin 1 row nearer the front)
    for port in range(4):
        for k in range(1, 9):
            num = 8 * port + k
            x = round(14.0 * port + 1.27 * (k - 1), 3)
            y = 0 if k % 2 else -2.54
            fp.append(pad(str(num), 'thru_hole', 'rect' if num == 1 else 'circle', (x, y), 1.6, 1.0))
    c = (3 * 14.0 + 8.89) / 2         # centre of the contact field
    yp = round(-2.54 + 8.89, 3)        # pegs
    yr, yf = round(yp - 10.25, 3), round(yp + 4.4, 3)  # rear / front shield rows
    for num, x, y in (('34', c - 14.0, yr), ('33', c, yr), ('33', c + 14.0, yr),
                      ('34', c - 29.5, yf), ('33', c + 29.5, yf)):
        fp.append(pad(num, 'thru_hole', 'circle', (round(x, 3), y), 2.3, 1.5))
    for x in (c - 26.75, c + 26.75):
        fp.append(pad('', 'np_thru_hole', 'circle', (round(x, 3), yp), 3.2, 3.2))
    # 3D: the EasyEDA/LCSC model of C3000204 (downloaded once into the 3dshapes folder), measured in FreeCAD:
    # pegs at x -72.8 / -19.3, y 3.96, seating plane z -13.5, port fronts toward -y. Shifted so its pegs sit on
    # ours and its base on the board; its contact rows are the library's (2.50 mm), ours are 2.54 mm.
    fp.append(['model', Q('${KIPRJMOD}/MES4-Carrier-EC.3dshapes/' + RJ_FP + '.step'),
               ['offset', ['xyz', round(c + 46.05, 3), round(-3.96 - yp, 3), 13.5]], ['scale', ['xyz', 1, 1, 1]],
               ['rotate', ['xyz', 0, 0, 0]]])
    fp.append(['embedded_fonts', 'no'])
    return fp


def write_footprint(pretty_dir):
    open(pretty_dir + '/' + RJ_FP + '.kicad_mod', 'w').write(dump(rj45x4_footprint()) + '\n')
