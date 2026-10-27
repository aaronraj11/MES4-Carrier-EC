"""Aux power parts: URB2409S-10WR3 (IMU 9 V, as on the MES3.1 carrier) and URB2405LD-20WR3 (screen 5 V)."""
import os, re, shutil, subprocess
from sx import Q, dump, find, first, deep
import builder as B
from builder import U, LIBNAME

MES3 = '/Users/aaron/Downloads/Project files 21_10_2026/MES3.1-Carrier-LH/'
HARV = '/Users/aaron/Desktop/MES3 Ecosystem/MES2_Harvester Project/MES2_Harvester Project/'
FP_4P = 'CONN-TH_KF250NH-3.5-4P'
EXT = '/Users/aaron/Desktop/MES3 Ecosystem/MES2_Extension/'
FP_IM = 'RELAY-SMD_IMXXGR'
FP_10W = 'PWRM-TH_YLPTEC_URBXXXXS-10WR3'
FP_20W = 'PWRM-TH_YLPTEC_URBXXXXLD-20WR3'


def _pin(num, name, x, y, ang, kind='passive'):
    return ['pin', kind, 'line', ['at', x, y, ang], ['length', 2.54],
            ['name', Q(name), ['effects', ['font', ['size', 1.27, 1.27]]]],
            ['number', Q(num), ['effects', ['font', ['size', 1.27, 1.27]]]]]


def _props(name, value, fp, ds, desc, ref_y, val_y):
    e = lambda hide=False: ['effects', ['font', ['size', 1.27, 1.27]]] + ([['hide', 'yes']] if hide else [])
    return [['property', Q('Reference'), Q('U'), ['at', 0, ref_y, 0], e()],
            ['property', Q('Value'), Q(value), ['at', 0, val_y, 0], e()],
            ['property', Q('Footprint'), Q(LIBNAME + ':' + fp), ['at', 0, 0, 0], e(True)],
            ['property', Q('Datasheet'), Q(ds), ['at', 0, 0, 0], e(True)],
            ['property', Q('Description'), Q(desc), ['at', 0, 0, 0], e(True)]]


def urb_10w_symbol():
    """Same pins / graphics as the URB2405S-6WR3 symbol (1 GND, 2 VIN, 3 CTRL, 5 NC, 6 +Vo, 7 -Vo, 8 NC)."""
    base = deep(B.symdef(LIBNAME + ':URB2405S-6WR3'))
    old = 'URB2405S-6WR3'
    new = 'URB2409S-10WR3'
    base[1] = Q(LIBNAME + ':' + new)
    for sub in find(base, 'symbol'):
        sub[1] = Q(sub[1].replace(old, new))
    for p in find(base, 'property'):
        if p[1] == 'Value':
            p[2] = Q(new)
        elif p[1] == 'Footprint':
            p[2] = Q(LIBNAME + ':' + FP_10W)
        elif p[1] == 'Description':
            p[2] = Q('YLPTEC URB2409S-10WR3: 9-36 V in, 9 V 1.11 A out, 10 W, 1.5 kV isolated, SIP-8')
        elif p[1] == 'Datasheet':
            p[2] = Q('https://www.lcsc.com/product-detail/C7424703.html')
    return base


def tca9535_symbol():
    """TI TCA9535PWR: same TSSOP-24 pinout as KiCad's PCA9555PW (no internal I/O pull-ups)."""
    base = B.kicad_symbol('Interface_Expansion:PCA9555PW')
    new = 'TCA9535PWR'
    base[1] = Q(LIBNAME + ':' + new)
    for sub in find(base, 'symbol'):
        sub[1] = Q(sub[1].replace('PCA9555PW', new))
    for p in find(base, 'property'):
        if p[1] == 'Value':
            p[2] = Q(new)
        elif p[1] == 'Description':
            p[2] = Q('TI TCA9535PWR: 16-bit I2C / SMBus I/O expander, 1.65-5.5 V, 5.5 V-tolerant I/O, '
                     'interrupt output, no internal pull-ups, TSSOP-24')
        elif p[1] == 'Datasheet':
            p[2] = Q('https://www.ti.com/lit/ds/symlink/tca9535.pdf')
    return base


def ina236_symbol():
    """TI INA236 (DDF, TSOT-23-8), drawn on KiCad's INA226 body so the Flasher relay wiring still lands on the
    same pins: VBUS and A1 dropped (the INA236 reads the bus on IN-, address via A0 only), pins renumbered."""
    base = B.kicad_symbol('Sensor_Energy:INA226')
    new = 'INA236'
    base[1] = Q(LIBNAME + ':' + new)
    num = {'Vin+': ('IN+', '1'), 'Vin-': ('IN-', '2'), 'GND': ('GND', '3'), 'VS': ('VS', '4'),
           'SCL': ('SCL', '5'), 'SDA': ('SDA', '6'), 'A0': ('A0', '7'), '~{Alert}': ('~{ALERT}', '8')}
    for sub in find(base, 'symbol'):
        sub[1] = Q(sub[1].replace('INA226', new))
        keep = []
        for it in sub[2:]:
            if isinstance(it, list) and it[0] == 'pin':
                name = first(it, 'name')[1]
                if name not in num:
                    continue
                first(it, 'name')[1] = Q(num[name][0])
                first(it, 'number')[1] = Q(num[name][1])
            keep.append(it)
        sub[2:] = keep
    for p in find(base, 'property'):
        if p[1] == 'Value':
            p[2] = Q(new)
        elif p[1] == 'Footprint':
            p[2] = Q('Package_TO_SOT_SMD:TSOT-23-8')
        elif p[1] == 'Datasheet':
            p[2] = Q('https://www.ti.com/lit/ds/symlink/ina236.pdf')
        elif p[1] == 'Description':
            p[2] = Q('TI INA236: 48 V (50 V abs max), 16-bit current / voltage / power monitor, I2C, '
                     'bus voltage on IN-, 4 addresses via A0, TSOT-23-8 (DDF)')
        elif p[1] == 'ki_fp_filters':
            p[2] = Q('TSOT?23*')
    return base


def im03gr_symbol():
    """TE Axicom IM03GR, 5 V monostable 2 form C (TE terminal assignment: coil 1+ / 8-,
    pole 1: 3 COM, 2 NC, 4 NO; pole 2: 6 COM, 7 NC, 5 NO)."""
    n = 'IM03GR'
    s = ['symbol', Q(LIBNAME + ':' + n), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
         ['in_bom', 'yes'], ['on_board', 'yes']]
    s += _props(n, n, FP_IM, 'https://www.lcsc.com/product-detail/C2153100.html',
                'TE IM03GR signal relay: 5 V coil 178 Ohm (28 mA), 2 form C (DPDT), 2 A, 220 VDC / 250 VAC, '
                '60 W DC; SMD 10 x 6 mm', 12.7, -12.7)
    s[s.index(next(p for p in s if isinstance(p, list) and p[0] == 'property' and p[1] == 'Reference'))][2] = Q('K')
    s.append(['symbol', Q(n + '_0_1'),
              ['rectangle', ['start', -10.16, 10.16], ['end', 10.16, -10.16],
               ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]],
              ['rectangle', ['start', -8.89, 2.54], ['end', -5.08, -2.54],
               ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'none']]],
              ['polyline', ['pts', ['xy', -6.985, 5.08], ['xy', -6.985, 2.54]],
               ['stroke', ['width', 0], ['type', 'default']], ['fill', ['type', 'none']]],
              ['polyline', ['pts', ['xy', -6.985, -2.54], ['xy', -6.985, -5.08]],
               ['stroke', ['width', 0], ['type', 'default']], ['fill', ['type', 'none']]],
              ['polyline', ['pts', ['xy', -7.62, 5.08], ['xy', -10.16, 5.08]],
               ['stroke', ['width', 0], ['type', 'default']], ['fill', ['type', 'none']]],
              ['polyline', ['pts', ['xy', -7.62, -5.08], ['xy', -10.16, -5.08]],
               ['stroke', ['width', 0], ['type', 'default']], ['fill', ['type', 'none']]]])
    s.append(['symbol', Q(n + '_1_1'),
              _pin('1', 'COIL+', -12.7, 5.08, 0), _pin('8', 'COIL-', -12.7, -5.08, 0),
              _pin('3', 'COM1', 12.7, 7.62, 180), _pin('2', 'NC1', 12.7, 5.08, 180), _pin('4', 'NO1', 12.7, 2.54, 180),
              _pin('6', 'COM2', 12.7, -2.54, 180), _pin('7', 'NC2', 12.7, -5.08, 180), _pin('5', 'NO2', 12.7, -7.62, 180)])
    s.append(['embedded_fonts', 'no'])
    return s


def urb_20w_symbol():
    n = 'URB2405LD-20WR3'
    s = ['symbol', Q(LIBNAME + ':' + n), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
         ['in_bom', 'yes'], ['on_board', 'yes']]
    s += _props(n, n, FP_20W, 'https://www.lcsc.com/product-detail/C5369825.html',
                'YLPTEC URB2405LD-20WR3: 9-36 V in, 5 V 4 A out, 20 W, 1.5 kV isolated, 2" x 1" DIP. '
                'CTRL open = on, Trim open = 5.0 V', 8.89, -8.89)
    s.append(['symbol', Q(n + '_0_1'),
              ['rectangle', ['start', -7.62, 6.35], ['end', 7.62, -6.35],
               ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]])
    s.append(['symbol', Q(n + '_1_1'),
              _pin('2', '+Vin', -10.16, 2.54, 0),
              _pin('6', 'CTRL', -10.16, 0, 0),
              _pin('1', '-Vin', -10.16, -2.54, 0),
              _pin('3', '+Vo', 10.16, 2.54, 180),
              _pin('4', 'Trim', 10.16, 0, 180, 'passive'),
              _pin('5', 'GND', 10.16, -2.54, 180)])
    s.append(['embedded_fonts', 'no'])
    return s


def urb_20w_footprint():
    """From the JLC/EasyEDA library footprint PWRM-TH_URBXXXXLD-20WR3 (C5369825), origin = body centre."""
    c = (4000, 3000)
    mm = lambda x, y: (round((x - c[0]) * 0.254, 3), round((y - c[1]) * 0.254, 3))
    pads = {'1': (3960, 2990), '2': (3960, 3010), '3': (4040, 3040), '4': (4040, 3000), '5': (4040, 2960),
            '6': (3960, 2960)}

    def line(a, b, layer, w):
        return ['fp_line', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']],
                ['layer', Q(layer)], ['uuid', U('fp20')]]

    def rect(a, b, layer, w):
        return ['fp_rect', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']],
                ['fill', 'no'], ['layer', Q(layer)], ['uuid', U('fp20')]]

    fx = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
    fp = ['footprint', Q(FP_20W), ['version', 20241229], ['generator', Q('pcbnew')], ['generator_version', Q('9.0')],
          ['layer', Q('F.Cu')],
          ['descr', Q('YLPTEC URBxxxxLD-20WR3 isolated DC/DC, 2" x 1" (50.8 x 25.4 mm) DIP, 6 pins. Pads from the '
                      'JLC/EasyEDA library footprint of URB2405LD-20WR3 (LCSC C5369825)')],
          ['tags', Q('DC-DC isolated brick 20W URB LD')],
          ['property', Q('Reference'), Q('REF**'), ['at', 0, -14.2, 0], ['layer', Q('F.SilkS')], ['uuid', U('fp20')], fx()],
          ['property', Q('Value'), Q(FP_20W), ['at', 0, 14.2, 0], ['layer', Q('F.Fab')], ['uuid', U('fp20')], fx()],
          ['property', Q('Datasheet'), Q('https://www.lcsc.com/product-detail/C5369825.html'), ['at', 0, 0, 0],
           ['layer', Q('F.Fab')], ['hide', 'yes'], ['uuid', U('fp20')], fx()],
          ['property', Q('Description'), Q('URBxxxxLD-20WR3 DC/DC module'), ['at', 0, 0, 0], ['layer', Q('F.Fab')],
           ['hide', 'yes'], ['uuid', U('fp20')], fx()],
          ['attr', 'through_hole'],
          rect((-25.4, -12.7), (25.4, 12.7), 'F.Fab', 0.1),
          rect((-25.51, -12.81), (25.51, 12.81), 'F.SilkS', 0.12),
          rect((-25.65, -12.95), (25.65, 12.95), 'F.CrtYd', 0.05),
          ['fp_text', 'user', Q('${REFERENCE}'), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['uuid', U('fp20')], fx()]]
    p1 = mm(*pads['1'])
    fp.append(line((p1[0] - 2.8, p1[1] - 1.0), (p1[0] - 2.8, p1[1] + 1.0), 'F.SilkS', 0.12))  # pin 1 mark
    for num, raw in sorted(pads.items()):
        fp.append(['pad', Q(num), 'thru_hole', 'rect' if num == '1' else 'circle', ['at'] + list(mm(*raw)),
                   ['size', 2.3, 2.3], ['drill', 1.5], ['layers', Q('*.Cu'), Q('*.Mask')],
                   ['remove_unused_layers', 'no'], ['uuid', U('fp20')]])
    fp.append(['embedded_fonts', 'no'])
    return fp


def write_footprints(pretty_dir, shapes_dir):
    open(os.path.join(pretty_dir, FP_20W + '.kicad_mod'), 'w').write(dump(urb_20w_footprint()) + '\n')
    # 10 W SIP-8: the MES3.1 carrier's footprint (easyeda2kicad, KiCad 5 format) + its 3D model
    src = open(MES3 + 'EasyEDA.pretty/' + FP_10W + '.kicad_mod').read()
    src = src.replace('easyeda2kicad:' + FP_10W, FP_10W)
    src = src.replace('${KIPRJMOD}/EasyEDA.3dshapes/', '${KIPRJMOD}/' + LIBNAME + '.3dshapes/')
    # upgrade the KiCad 5 file to the current format (kicad-cli fp upgrade on a one-file library)
    import tempfile
    work = os.path.join(tempfile.gettempdir(), 'mes4ec_fp_upgrade.pretty')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    open(os.path.join(work, FP_10W + '.kicad_mod'), 'w').write(src)
    subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli', 'fp', 'upgrade', '--force', work],
                   capture_output=True)
    shutil.copy(os.path.join(work, FP_10W + '.kicad_mod'), pretty_dir)
    for ext in ('.wrl', '.step'):
        f = MES3 + 'EasyEDA.3dshapes/' + FP_10W + ext
        if os.path.exists(f):
            shutil.copy(f, shapes_dir)
    # KF250NH-3.5-4P: the MES2 Harvester's footprint (CN13) + its 3D model
    src = open(HARV + 'EasyEDA.pretty/' + FP_4P + '.kicad_mod').read()
    src = src.replace('easyeda2kicad:' + FP_4P, FP_4P)
    src = src.replace('${KIPRJMOD}/EasyEDA.3dshapes/', '${KIPRJMOD}/' + LIBNAME + '.3dshapes/')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    open(os.path.join(work, FP_4P + '.kicad_mod'), 'w').write(src)
    subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli', 'fp', 'upgrade', '--force', work],
                   capture_output=True)
    shutil.copy(os.path.join(work, FP_4P + '.kicad_mod'), pretty_dir)
    for ext in ('.wrl', '.step'):
        f = HARV + 'EasyEDA.3dshapes/' + FP_4P + ext
        if os.path.exists(f):
            shutil.copy(f, shapes_dir)
    # IM03GR relay: the MES2_Extension's footprint + 3D model
    src = open(EXT + 'EasyEDA.pretty/' + FP_IM + '.kicad_mod').read()
    src = src.replace('easyeda2kicad:' + FP_IM, FP_IM)
    src = src.replace('${KIPRJMOD}/EasyEDA.3dshapes/', '${KIPRJMOD}/' + LIBNAME + '.3dshapes/')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    open(os.path.join(work, FP_IM + '.kicad_mod'), 'w').write(src)
    subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli', 'fp', 'upgrade', '--force', work],
                   capture_output=True)
    shutil.copy(os.path.join(work, FP_IM + '.kicad_mod'), pretty_dir)
    for ext in ('.wrl', '.step'):
        f = EXT + 'EasyEDA.3dshapes/' + FP_IM + ext
        if os.path.exists(f):
            shutil.copy(f, shapes_dir)
