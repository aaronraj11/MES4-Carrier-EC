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


# Pad data: JLC/EasyEDA library footprint RJ45-TH_HC-RJ45-059-4-4 (10-mil units, pad 1 = origin);
# drill sizes from the HCTL drawing (32 x Ø1.0, 5 x Ø1.5, 2 x Ø3.2), shield drills kept at the
# library's Ø1.7 to absorb the 0.2 mm difference between the two sources on the rear shield row.
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
                      '(LCSC C3000204). Pad positions from the JLC/EasyEDA library footprint, drills from the HCTL '
                      'drawing. Port front face 17.0 mm in front of the pin-1 row.')],
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
    # 32 contacts: port pitch 13.97 mm (550 mil), 1.27 mm pitch, rows 2.54 mm apart (pin 1 row nearer the front)
    for port in range(4):
        for k in range(1, 9):
            num = 8 * port + k
            x = round(13.97 * port + 1.27 * (k - 1), 3)
            y = 0 if k % 2 else -2.54
            fp.append(pad(str(num), 'thru_hole', 'rect' if num == 1 else 'circle', (x, y), 1.6, 1.0))
    for num, raw in (('33', (4099.378, 2954.429)), ('33', (4154.496, 2954.429)), ('33', (4215.52, 3013.091)),
                     ('34', (4044.26, 2954.429)), ('34', (3983.237, 3013.091))):
        fp.append(pad(num, 'thru_hole', 'circle', _mm(*raw), 2.3, 1.7))
    for raw in ((3994.063, 2995.768), (4204.693, 2995.768)):
        fp.append(pad('', 'np_thru_hole', 'circle', _mm(*raw), 3.2, 3.2))
    fp.append(['embedded_fonts', 'no'])
    return fp


def write_footprint(pretty_dir):
    open(pretty_dir + '/' + RJ_FP + '.kicad_mod', 'w').write(dump(rj45x4_footprint()) + '\n')
