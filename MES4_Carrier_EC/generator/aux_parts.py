"""Aux power parts: URB2409S-10WR3 (IMU 9 V, as on the MES3.1 carrier) and URB2405YMD-20WR3 (screen 5 V)."""
import os, re, shutil, subprocess
from sx import Q, dump, find, first, deep, parse
import builder as B
from builder import U, LIBNAME

MES3 = '/Users/aaron/Downloads/Project files 21_10_2026/MES3.1-Carrier-LH/'
HARV = '/Users/aaron/Desktop/MES3 Ecosystem/MES2_Harvester Project/MES2_Harvester Project/'
FP_4P = 'CONN-TH_KF250NH-3.5-4P'
EXT = '/Users/aaron/Desktop/MES3 Ecosystem/MES2_Extension/'
FP_IM = 'RELAY-SMD_IMXXGR'
FP_10W = 'PWRM-TH_YLPTEC_URBXXXXS-10WR3'
FP_YMD = 'PWRM-TH_YLPTEC_URBXXXXYMD-20WR3'
FP_DDF = 'TSOT-23-8_TI_DDF'
FL = '/Users/aaron/Desktop/MES4 Ecosystem/MES4-Flasher/'
ECR = '/Users/aaron/Desktop/MES3 Ecosystem/MES2_E-Crawler Project/'
FP_SO25 = 'Standoff_SMD_M3_H2.5mm_SMTS0M325STR'
FP_SO2 = 'Standoff_SMD_M3_H2mm_SMTSOM320BTR'
FP_FE = 'FE-URT-2'
FP_SO65 = 'Standoff_SMD_M3_H6.5mm_SMTSOM365BTR'
FP_RTK = 'ArduSimple_simpleRTK4_Dual_mount'
RTK_STEP = '/Users/aaron/Downloads/AS-RTK4-X20D-NH-00-R00.step'
RTK_W, RTK_H = 68.58, 53.34     # simpleRTK4 Dual PCB (Arduino Uno size), measured in its STEP
# its 3.2 mm holes used here, from the PCB's bottom-left corner (y up): left-bottom, left-top, right. The two middle
# holes (47.63, 12.95 / 43.43) are left out: the FE-URT-2 sits under that part of the board.
RTK_HOLES = ((13.97, 2.54), (15.24, 50.80), (66.04, 35.56))
RTK_POST = 18.5                 # 6.5 mm SMD standoff + M3 x 12 mm male-female spacer: RTK underside above the carrier
# FE-URT-2 mounting holes, footprint coordinates (Feetech drawing: 48.5 x 28.7 mm, 3 mm holes, board 55.8 x 37.6 mm)
FE_HOLES = ((-14.095, -23.1), (14.605, -23.1), (-14.095, 25.4), (14.605, 25.4))


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
            p[2] = Q(LIBNAME + ':' + FP_DDF)
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


def urb_ymd_symbol():
    """Pin names as on the old LD symbol, so the sheet wiring is unchanged; numbers per the YMD pinout
    (YLPTEC EasyEDA symbol for C5369777 = Mornsun URB_YMD-20WR3 datasheet: 1 Ctrl, 2 GND, 3 Vin, 4 +Vo, 5 Trim, 6 0V)."""
    n = 'URB2405YMD-20WR3'
    s = ['symbol', Q(LIBNAME + ':' + n), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
         ['in_bom', 'yes'], ['on_board', 'yes']]
    s += _props(n, n, FP_YMD, 'https://www.lcsc.com/product-detail/C5369777.html',
                'YLPTEC URB2405YMD-20WR3: 9-36 V in (40 V max, 50 V 1 s surge), 5 V 4 A out, 20 W, 1.5 kV isolated, '
                '1" x 1" DIP. CTRL open = on, Trim open = 5.0 V', 8.89, -8.89)
    s.append(['symbol', Q(n + '_0_1'),
              ['rectangle', ['start', -7.62, 6.35], ['end', 7.62, -6.35],
               ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]])
    s.append(['symbol', Q(n + '_1_1'),
              _pin('3', '+Vin', -10.16, 2.54, 0),
              _pin('1', 'CTRL', -10.16, 0, 0),
              _pin('2', '-Vin', -10.16, -2.54, 0),
              _pin('4', '+Vo', 10.16, 2.54, 180),
              _pin('5', 'Trim', 10.16, 0, 180, 'passive'),
              _pin('6', 'GND', 10.16, -2.54, 180)])
    s.append(['embedded_fonts', 'no'])
    return s


def urb_ymd_footprint():
    """From the JLC/EasyEDA library footprint PWRM-TH_URBXXXXYMD-20WR3 (C5369777), origin = body centre. Matches the
    Mornsun drawing: pins 1-2-3 7.62 + 5.08 mm apart, 6-5-4 2 x 10.16 mm, rows 20.32 mm apart, 25.4 mm body;
    1.5 mm holes (datasheet) for the 1.0 mm pins, 2.4 mm pads (EasyEDA)."""
    c = (3990, 3040)
    mm = lambda x, y: (round((x - c[0]) * 0.254, 3), round((y - c[1]) * 0.254, 3))
    pads = {'1': (3950, 3000), '2': (3950, 3030), '3': (3950, 3050), '4': (4030, 3080), '5': (4030, 3040),
            '6': (4030, 3000)}

    def line(a, b, layer, w):
        return ['fp_line', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']],
                ['layer', Q(layer)], ['uuid', U('fpymd')]]

    def rect(a, b, layer, w):
        return ['fp_rect', ['start', a[0], a[1]], ['end', b[0], b[1]], ['stroke', ['width', w], ['type', 'solid']],
                ['fill', 'no'], ['layer', Q(layer)], ['uuid', U('fpymd')]]

    fx = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
    h = 12.7
    fp = ['footprint', Q(FP_YMD), ['version', 20241229], ['generator', Q('pcbnew')], ['generator_version', Q('9.0')],
          ['layer', Q('F.Cu')],
          ['descr', Q('YLPTEC URBxxxxYMD-20WR3 isolated DC/DC, 1" x 1" (25.4 x 25.4 x 11.8 mm) DIP, 6 pins. Pads from the '
                      'JLC/EasyEDA library footprint of URB2405YMD-20WR3 (LCSC C5369777), checked against the Mornsun '
                      'URB_YMD-20WR3 drawing')],
          ['tags', Q('DC-DC isolated brick 20W URB YMD 1x1')],
          ['property', Q('Reference'), Q('REF**'), ['at', 0, -h - 1.5, 0], ['layer', Q('F.SilkS')], ['uuid', U('fpymd')], fx()],
          ['property', Q('Value'), Q(FP_YMD), ['at', 0, h + 1.5, 0], ['layer', Q('F.Fab')], ['uuid', U('fpymd')], fx()],
          ['property', Q('Datasheet'), Q('https://www.lcsc.com/product-detail/C5369777.html'), ['at', 0, 0, 0],
           ['layer', Q('F.Fab')], ['hide', 'yes'], ['uuid', U('fpymd')], fx()],
          ['property', Q('Description'), Q('URBxxxxYMD-20WR3 DC/DC module'), ['at', 0, 0, 0], ['layer', Q('F.Fab')],
           ['hide', 'yes'], ['uuid', U('fpymd')], fx()],
          ['attr', 'through_hole'],
          rect((-h, -h), (h, h), 'F.Fab', 0.1),
          rect((-h - 0.11, -h - 0.11), (h + 0.11, h + 0.11), 'F.SilkS', 0.12),
          rect((-h - 0.25, -h - 0.25), (h + 0.25, h + 0.25), 'F.CrtYd', 0.05),
          ['fp_text', 'user', Q('${REFERENCE}'), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['uuid', U('fpymd')], fx()]]
    p1 = mm(*pads['1'])
    fp.append(line((p1[0] - 2.0, p1[1] - 1.0), (p1[0] - 2.0, p1[1] + 1.0), 'F.SilkS', 0.12))  # pin 1 mark
    for num, raw in sorted(pads.items()):
        fp.append(['pad', Q(num), 'thru_hole', 'rect' if num == '1' else 'circle', ['at'] + list(mm(*raw)),
                   ['size', 2.4, 2.4], ['drill', 1.5], ['layers', Q('*.Cu'), Q('*.Mask')],
                   ['remove_unused_layers', 'no'], ['uuid', U('fpymd')]])
    # 3D: the EasyEDA/LCSC model of C5369777 (downloaded once into the 3dshapes folder); its origin is the body centre
    # on the board surface and its pins sit on these pads, so no offset or rotation
    fp.append(['model', Q('${KIPRJMOD}/' + LIBNAME + '.3dshapes/' + FP_YMD + '.step'),
               ['offset', ['xyz', 0, 0, 0]], ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz', 0, 0, 0]]])
    fp.append(['embedded_fonts', 'no'])
    return fp


def write_footprints(pretty_dir, shapes_dir):
    open(os.path.join(pretty_dir, FP_YMD + '.kicad_mod'), 'w').write(dump(urb_ymd_footprint()) + '\n')
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
    # INA236 (TI DDF, SOT-23-THIN 8): KiCad's TSOT-23-8 with TI's land pattern (DDF0008A: 8 x 1.05 x 0.45 mm pads,
    # rows 2.6 mm apart, 0.65 mm pitch). KiCad's 0.5 mm pads leave 0.15 mm gaps, under the 0.2 mm net-class clearance.
    src = open('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Package_TO_SOT_SMD.pretty/'
               'TSOT-23-8.kicad_mod').read()
    assert src.count('(size 1.325 0.5)') == 8 and src.count('1.1375') == 8
    src = src.replace('(footprint "TSOT-23-8"', '(footprint "%s"' % FP_DDF, 1)
    src = src.replace('(size 1.325 0.5)', '(size 1.05 0.45)').replace('-1.1375 ', '-1.3 ').replace('(at 1.1375 ', '(at 1.3 ')
    src = re.sub(r'\(descr "[^"]*"\)', '(descr "TI DDF0008A (SOT-23-THIN 8, 2.9 x 1.6 mm, 0.65 mm pitch), land pattern from the '
                 'INA236 datasheet: 8 x 1.05 x 0.45 mm pads, rows 2.6 mm apart")', src, count=1)
    open(os.path.join(pretty_dir, FP_DDF + '.kicad_mod'), 'w').write(src)
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
    standoff_2mm(pretty_dir, shapes_dir)
    feurt2_outline(pretty_dir)
    standoff(pretty_dir, shapes_dir, FP_SO65, 6.5, 'SMTSOM365BTR', 'C5301796')
    rtk_mount(pretty_dir, shapes_dir)


def standoff_2mm(pretty_dir, shapes_dir):
    """YIYUAN SMTSOM320BTR (C5301780), M3 x 2 mm: the FE-URT-2 standoffs (as U21-U24 on the MES3 E-Crawler and U24-U28
    on the MES3.1 carrier)."""
    standoff(pretty_dir, shapes_dir, FP_SO2, 2.0, 'SMTSOM320BTR', 'C5301780')


def standoff(pretty_dir, shapes_dir, name, h, mpn, lcsc):
    """YIYUAN SMTSO M3 SMD standoff of height h. Same series as the module hold-down SMTS0M325STR (LCSC: M3 x 5.56 x
    L<h> + 1.53 mm), so the MES4-Flasher's checked land pattern is reused; only the height and the part change."""
    src = open(FL + 'MES4-Flasher.pretty/' + FP_SO25 + '.kicad_mod').read()
    for a, b in (('(footprint "%s"' % FP_SO25, '(footprint "%s"' % name),
                 ('2.5 mm above the board', '%g mm above the board' % h),
                 ('(YIYUAN SMTS0M325STR, LCSC C5301771)', '(YIYUAN %s, LCSC %s; same series as SMTS0M325STR)' % (mpn, lcsc)),
                 ('SMTSO M3 2.5mm', 'SMTSO M3 %gmm' % h), ('"M3 standoff 2.5mm"', '"M3 standoff %gmm"' % h),
                 ('MES4-Flasher.3dshapes/' + FP_SO25, LIBNAME + '.3dshapes/' + name)):
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    open(os.path.join(pretty_dir, name + '.kicad_mod'), 'w').write(src)
    # 3D: the Flasher's tube at the new height (VRML units are 2.54 mm)
    open(os.path.join(shapes_dir, name + '.wrl'), 'w').write(_tube(h, name))


def _tube(h, name, label='M3 SMD standoff'):
    """The MES4-Flasher's 5.56 mm standoff tube (VRML), h mm tall."""
    wrl = open(FL + 'MES4-Flasher.3dshapes/' + FP_SO25 + '.wrl').read()
    top = '%.4f' % (2.5 / 2.54)
    assert ' ' + top in wrl
    wrl = wrl.replace(' ' + top, ' %.4f' % (h / 2.54)).replace(FP_SO25, name).replace('2.5 mm tall', '%g mm tall' % h)
    return wrl.replace('M3 SMD standoff', label, 1)


def feurt2_outline(pretty_dir):
    """FE-URT-2 outline, board-only: the MES3 footprint without its holes (the board screws onto the four SMD standoffs,
    which are their own parts), plus a footprint keep-out under the board so nothing gets placed there. The corners
    around the standoffs stay open for their courtyards."""
    src = open(ECR + 'FE-URT-2.pretty/' + FP_FE + '.kicad_mod').read()
    d = parse(src)
    # drop the holes, their courtyards, the model, and the square outline + texts (redrawn below)
    d[:] = [c for c in d if not (isinstance(c, list) and (
        c[0] in ('pad', 'model', 'fp_rect', 'fp_text') or (c[0] == 'fp_circle' and first(c, 'layer')[1] == 'F.CrtYd')))]
    attr = first(d, 'attr')
    attr[1:] = ['board_only', 'exclude_from_pos_files', 'exclude_from_bom']
    def walk(n):
        for c in n:
            if isinstance(c, list):
                if c[:2] == ['thickness', '0.1']:
                    c[1] = 0.15  # the board's minimum text thickness
                walk(c)
    walk(d)
    k = d.index(first(d, 'layer')) + 1
    d.insert(k, ['descr', Q('Feetech FE-URT-2 servo driver outline (board-only). It mounts on 4 x %s M3 x 2 mm SMD '
                            'standoffs on its 48.5 x 28.7 mm holes, as on the MES3 E-Crawler / MES3.1 carriers. '
                            'Keep-out: no parts under the board.' % FP_SO2)])
    x0, y0, x1, y1 = -18.545, -26.75, 19.055, 29.05  # board outline (55.8 x 37.6 mm)
    cx, cy = round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)
    # outline with rounded corners: bold on the silkscreen, thin on F.Fab for the assembly drawing
    rad, c45 = 2.0, 2.0 * (1 - 0.5 ** 0.5)
    for layer, w in (('F.SilkS', 0.3), ('F.Fab', 0.1)):
        st = ['stroke', ['width', w], ['type', 'solid']]
        for a, b in (((x0 + rad, y0), (x1 - rad, y0)), ((x1, y0 + rad), (x1, y1 - rad)),
                     ((x1 - rad, y1), (x0 + rad, y1)), ((x0, y1 - rad), (x0, y0 + rad))):
            d.append(['fp_line', ['start', round(a[0], 3), round(a[1], 3)], ['end', round(b[0], 3), round(b[1], 3)],
                      st, ['layer', Q(layer)], ['uuid', U('fe')]])
        for (sx_, sy_), (mx, my), (ex_, ey_) in (
                ((x0, y0 + rad), (x0 + c45, y0 + c45), (x0 + rad, y0)), ((x1 - rad, y0), (x1 - c45, y0 + c45), (x1, y0 + rad)),
                ((x1, y1 - rad), (x1 - c45, y1 - c45), (x1 - rad, y1)), ((x0 + rad, y1), (x0 + c45, y1 - c45), (x0, y1 - rad))):
            d.append(['fp_arc', ['start', round(sx_, 3), round(sy_, 3)], ['mid', round(mx, 3), round(my, 3)],
                      ['end', round(ex_, 3), round(ey_, 3)], st, ['layer', Q(layer)], ['uuid', U('fe')]])
    def txt(s, y, size, thick, layer='F.SilkS', bold=True, knockout=False):
        font = ['font', ['size', size, size], ['thickness', thick]] + ([['bold', 'yes']] if bold else [])
        return ['fp_text', 'user', Q(s), ['at', cx, round(cy + y, 3), 0],
                ['layer', Q(layer)] + (['knockout'] if knockout else []), ['uuid', U('fe')], ['effects', font]]
    # one two-line knockout label (text cut out of a single solid silkscreen block)
    d.append(txt('FE-URT-2\nSERVO DRIVER', 0, 3.0, 0.5, knockout=True))
    d.append(txt('${REFERENCE}', 0, 1.0, 0.15, 'F.Fab', bold=False))
    for p in find(d, 'property'):
        if p[1] == 'Reference':
            first(p, 'at')[1:3] = [cx, round(cy + 7.6, 3)]
    ex, ey = 3.6, 3.6  # standoff corners left open
    l, r = FE_HOLES[0][0] + ex, FE_HOLES[1][0] - ex
    t, b = FE_HOLES[0][1] + ey, FE_HOLES[2][1] - ey
    pts = [(l, y0), (r, y0), (r, t), (x1, t), (x1, b), (r, b), (r, y1), (l, y1), (l, b), (x0, b), (x0, t), (l, t)]
    d.append(['zone', ['net', 0], ['net_name', Q('')], ['layers', Q('F.Cu')], ['uuid', U('fe')],
              ['name', Q('FE-URT-2 clear')], ['hatch', 'edge', 0.5], ['connect_pads', ['clearance', 0]],
              ['min_thickness', 0.25], ['filled_areas_thickness', 'no'],
              ['keepout', ['tracks', 'allowed'], ['vias', 'allowed'], ['pads', 'allowed'], ['copperpour', 'allowed'],
               ['footprints', 'not_allowed']],
              ['placement', ['enabled', 'no'], ['sheetname', Q('')]],
              ['fill', ['thermal_gap', 0.5], ['thermal_bridge_width', 0.5]],
              ['polygon', ['pts'] + [['xy', round(x, 3), round(y, 3)] for x, y in pts]]])
    # 3D: the FE-URT-2 STEP (not on this Mac yet: drop it into the 3dshapes folder) on top of the 2 mm standoffs
    d.append(['model', Q('${KIPRJMOD}/' + LIBNAME + '.3dshapes/LC-PCB-PCB0-URT-2201.STEP'),
              ['offset', ['xyz', 14.5, -25.5, 2.0]], ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz', 0, 0, -90]]])
    open(os.path.join(pretty_dir, FP_FE + '.kicad_mod'), 'w').write(dump(d) + '\n')


def rtk_holes_fp():
    """RTK mounting holes in the mount footprint's coordinates (origin at the RTK PCB centre, KiCad y down)."""
    return [(round(x - RTK_W / 2, 3), round(RTK_H / 2 - y, 3)) for x, y in RTK_HOLES]


def rtk_mount(pretty_dir, shapes_dir):
    """ArduSimple simpleRTK4 Dual, stacked over the FE-URT-2 on three posts (6.5 mm SMD standoff + 12 mm spacer).
    Board-only: Fab outline and post marks, the RTK's STEP 18.5 mm up, and the spacers. No courtyard or silkscreen:
    the RTK is above everything on the carrier (tallest part, the relays, is 15.5 mm)."""
    x0, y0, x1, y1 = -RTK_W / 2, -RTK_H / 2, RTK_W / 2, RTK_H / 2
    st = lambda w: ['stroke', ['width', w], ['type', 'solid']]
    fp = ['footprint', Q(FP_RTK), ['version', 20241229], ['generator', Q('pcbnew')], ['generator_version', Q('9.0')],
          ['layer', Q('F.Cu')],
          ['descr', Q('ArduSimple simpleRTK4 Dual (AS-RTK4-X20D), stacked above the FE-URT-2 on 3 x %s M3 x 6.5 mm SMD '
                      'standoffs + M3 x 12 mm male-female spacers (underside %g mm above the carrier). Holes used: left-bottom, '
                      'left-top, right. Powered from its own GPS USB-C (west edge, with the SMAs).' % (FP_SO65, RTK_POST))],
          ['tags', Q('GPS RTK ArduSimple simpleRTK4 mount')]]
    e = lambda size=1.0: ['effects', ['font', ['size', size, size], ['thickness', 0.15]]]
    fp += [['property', Q('Reference'), Q('REF**'), ['at', 0, round(y1 - 3.0, 3), 0], ['layer', Q('F.Fab')], ['uuid', U('rtk')], e()],
           ['property', Q('Value'), Q('simpleRTK4 Dual'), ['at', 0, round(y1 - 5.0, 3), 0], ['layer', Q('F.Fab')], ['uuid', U('rtk')], e()],
           ['property', Q('Datasheet'), Q('https://www.ardusimple.com/product/simplertk-4-dual/'), ['at', 0, 0, 0],
            ['layer', Q('F.Fab')], ['hide', 'yes'], ['uuid', U('rtk')], e()],
           ['property', Q('Description'), Q('GPS mount (board-only)'), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'],
            ['uuid', U('rtk')], e()],
           ['attr', 'board_only', 'exclude_from_pos_files', 'exclude_from_bom']]
    fp.append(['fp_rect', ['start', round(x0, 3), round(y0, 3)], ['end', round(x1, 3), round(y1, 3)], st(0.1), ['fill', 'no'],
               ['layer', Q('F.Fab')], ['uuid', U('rtk')]])
    fp.append(['fp_text', 'user', Q('GPS: simpleRTK4 Dual, %g mm up' % RTK_POST), ['at', 0, round(y1 - 7.0, 3), 0],
               ['layer', Q('F.Fab')], ['uuid', U('rtk')], e()])
    for hx, hy in rtk_holes_fp():
        fp.append(['fp_circle', ['center', hx, hy], ['end', round(hx + 1.6, 3), hy], st(0.1), ['fill', 'no'],
                   ['layer', Q('F.Fab')], ['uuid', U('rtk')]])
    # 3D: the RTK's own STEP (PCB bottom-left corner at (0.164, 12.337), underside at z 58.09 in that file),
    # moved so its PCB centre is the footprint origin and its underside sits on the posts
    if os.path.exists(RTK_STEP):
        shutil.copy(RTK_STEP, os.path.join(shapes_dir, FP_RTK + '.step'))
    fp.append(['model', Q('${KIPRJMOD}/' + LIBNAME + '.3dshapes/' + FP_RTK + '.step'),
               ['offset', ['xyz', round(-(0.164 + RTK_W / 2), 3), round(-(12.337 + RTK_H / 2), 3), round(RTK_POST - 58.09, 3)]],
               ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz', 0, 0, 0]]])
    spacer = 'Spacer_M3_12mm_hex'
    open(os.path.join(shapes_dir, spacer + '.wrl'), 'w').write(_tube(RTK_POST - 6.5, spacer, 'M3 male-female spacer'))
    for hx, hy in rtk_holes_fp():
        fp.append(['model', Q('${KIPRJMOD}/' + LIBNAME + '.3dshapes/' + spacer + '.wrl'),
                   ['offset', ['xyz', hx, -hy, 6.5]], ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz', 0, 0, 0]]])
    fp.append(['embedded_fonts', 'no'])
    open(os.path.join(pretty_dir, FP_RTK + '.kicad_mod'), 'w').write(dump(fp) + '\n')
