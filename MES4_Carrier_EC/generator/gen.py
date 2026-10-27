#!/usr/bin/env python3
"""Generate the MES4-Carrier-EC KiCad 9 schematic from the MES4-Flasher sheets + new blocks."""
import sys, os, re, json, shutil
TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from sx import parse, dump, find, first, prop, deep, Q
import builder as B
from builder import Sheet, U, R2
from parts import NEWP
import can_parts as CP
import aux_parts as AP

FL = '/Users/aaron/Desktop/MES4 Ecosystem/MES4-Flasher/'
OUT = '/Users/aaron/Desktop/MES4 Ecosystem/MES4-Carrier-EC/MES4_Carrier_EC/'
TITLE, DATE, REV, COMPANY, AUTHOR = 'MES4-Carrier-EC', '2026-10-27', 'A', 'Monkey Robotics', 'Aaron Raj Bhatti'


# ---------------------------------------------------------------- Flasher part fields
def harvest():
    out = {}
    for f in ['Main', 'Power', 'Relays', 'Sensors', 'LoadCell']:
        root = parse(open(FL + f + '.kicad_sch').read())
        for s in find(root, 'symbol'):
            def g(n):
                p = prop(s, n)
                return p[2] if p else ''
            out[g('Reference')] = dict(lib=B.rn(first(s, 'lib_id')[1]), value=g('Value'),
                                       fp=g('Footprint').replace('MES4-Flasher:', B.LIBNAME + ':'),
                                       lcsc=g('LCSC'), desc=g('Description'), ds=g('Datasheet') or '~')
    return out


FLP = harvest()


def fpart(sh, oldref, at, rot=0, mirror=None, tag=None, value=None, desc=None, **kw):
    f = FLP[oldref]
    prefix = re.match(r'[A-Z]+', oldref).group(0)
    return sh.part(f['lib'], prefix, value or f['value'], at, rot, mirror, fp=f['fp'], lcsc=f['lcsc'],
                   desc=desc or f['desc'], tag=tag, ds=f['ds'], **kw)


def npart(sh, key, prefix, at, rot=0, mirror=None, tag=None, value=None, desc=None, **kw):
    f = NEWP[key]
    return sh.part(f['lib'], prefix, value or f['value'], at, rot, mirror, fp=f['fp'], lcsc=f['lcsc'],
                   desc=desc or f['desc'], tag=tag or key, ds=f.get('ds', '~'), **kw)


def setf(p, value=None, lcsc=None, desc=None, fp=None, lib=None, ds=None):
    if lib:
        p.lib_id = lib
        # regenerate pin entries for the new symbol
        p.node[:] = [c for c in p.node if not (isinstance(c, list) and c[0] == 'pin')]
        for num in B.D(lib).pins:
            p.node.append(['pin', Q(num), ['uuid', U('pin')]])
    if value is not None:
        p.set('Value', value)
    if lcsc is not None:
        p.set('LCSC', lcsc)
    if desc is not None:
        p.set('Description', desc)
    if fp is not None:
        p.set('Footprint', fp)
    if ds is not None:
        p.set('Datasheet', ds)


def drop_texts(sh, pred=lambda t: True):
    sh.items = [it for it in sh.items if not (it[0] == 'text' and pred(it))]


def relabel(sh, old, new, kinds=('label', 'global_label'), region=None):
    for it in sh.items:
        if it[0] in kinds and it[1] == old:
            if region and not sh.in_region(it, *region):
                continue
            it[1] = Q(new)


def power_at(sh, xy):
    for p in sh.parts:
        if B.D(p.lib_id).power and any(pt == xy for n, pt in p.pins()):
            return p
    return None


def set_strap(sh, pin_xy, sym_xy, net):
    p = power_at(sh, sym_xy)
    assert p is not None, sym_xy
    sh.parts.remove(p)
    sh.pwr(net, sym_xy, 90 if net == 'GND' else 270)


# ---------------------------------------------------------------- relay sheets (template: Flasher Relays)
CH = {
    1: dict(drv='PA8', fb='RLY1_FB', addr='0x40', a1='GND', a0='GND', load='safety light'),
    2: dict(drv='PC6', fb='RLY2_FB', addr='0x41', a1='GND', a0='+3V3_MOD', load='LED DRL'),
    3: dict(drv='PB3', fb='RLY3_FB', addr='0x44', a1='+3V3_MOD', a0='GND', load='battery stopper'),
    4: dict(drv='PA7', fb='RLY4_FB', addr='0x45', a1='+3V3_MOD', a0='+3V3_MOD', load='spare'),
}
TPL = [dict(Q='Q1', RB='R8', RPD='R10', F='F7', U='U5', K='K1', J='J9', LED='LED3', RLED='R27', DL='D27',
            drv='PA8', fb='PA0', out='RLY1_OUT', y0=20.32, y1=121.92),
       dict(Q='Q2', RB='R9', RPD='R11', F='F8', U='U6', K='K2', J='J10', LED='LED4', RLED='R28', DL='D28',
            drv='PC6', fb='PA1', out='RLY2_OUT', y0=124.46, y1=226.06)]


def relay_sheet(name, file, page, chans, comment):
    sh = Sheet.from_template(FL + 'Relays.kicad_sch', name, file, comment, page)
    drop_texts(sh)
    fch = NEWP['F_CH']
    for t, n in zip(TPL, chans):
        c = CH[n]
        g = lambda r: sh.part_by_tag('old:' + r)
        q = g(t['Q'])
        setf(q, value='AO3400A', lcsc='C20917', fp='Package_TO_SOT_SMD:SOT-23', lib='Transistor_FET:AO3400A',
             ds='http://www.aosmd.com/pdfs/datasheet/AO3400A.pdf',
             desc='relay %d coil driver, N-MOSFET 30 V 5.7 A (CIF §7a)' % n)
        setf(g(t['RB']), value='100Ω', lcsc='C25076', desc='AO3400A gate series resistor (CIF §7a)')
        setf(g(t['RPD']), value='100k', lcsc='C25741',
             desc='gate pull-down: relay %d OFF during reset / boot (CIF §4a, §7a)' % n)
        setf(g(t['F']), value=fch['value'], lcsc=fch['lcsc'], fp=fch['fp'], lib=fch['lib'],
             desc='relay %d output PTC: a shorted output trips only this channel' % n)
        setf(g(t['U']), desc='INA226, I²C %s: relay %d (%s) load current + 24 V rail (CIF §6a)'
             % (c['addr'], n, c['load']))
        setf(g(t['J']), value='RLY%d OUT' % n,
             desc='relay %d (%s) output: 1 = switched +24 V, 2 = GND_24V (KF250NH 3.5 mm push-in)' % (n, c['load']))
        g(t['K']).set('Description', 'relay %d (%s), SRD-5VDC-SL-A, 5 V coil, SPST-NO 10 A' % (n, c['load']))
        region = (100, t['y0'], 420, t['y1'])
        relabel(sh, t['drv'], c['drv'], region=region)
        relabel(sh, t['fb'], c['fb'], region=region)
        relabel(sh, t['out'], 'RLY%d_OUT' % n, region=region)
        X, Y, _ = g(t['U']).at
        set_strap(sh, None, (R2(X + 12.70), R2(Y - 7.62)), c['a1'])
        set_strap(sh, None, (R2(X + 17.78), R2(Y - 5.08)), c['a0'])
        # retag for the note templates
        for k in ('Q', 'RB', 'RPD', 'F', 'U', 'K', 'J', 'LED', 'RLED', 'DL'):
            g(t[k]).tag = 'ch%d:%s' % (n, k)
        sh.text('Relay %d (%s): drive %s, coil feedback %s, INA226 {ch%d:U} at %s'
                % (n, c['load'], c['drv'], c['fb'], n, c['addr']), (111.76, t['y0'] + 2.54), size=2, bold=True)
        sh.text('Coil feedback (%s, TCA9535 P0%d): HIGH (3.0 V) = coil off and intact, LOW = energised.\n'
                'INA226 %s (A1 = %s, A0 = %s): load current (30 mΩ, LSB 100 µA) + 24 V rail; ALERT → PA15.\n'
                '{ch%d:LED}: output ON; its 6.7 mA also lets the INA226 see the contact close with no load.\n'
                '{ch%d:F}: %s hold PTC, so a shorted output trips only this channel. {ch%d:DL}: load flyback.\n'
                '{ch%d:Q} AO3400A: {ch%d:RB} 100 Ω gate, {ch%d:RPD} 100k pull-down = OFF in reset (CIF §7a).'
                % (c['fb'], n - 1, c['addr'], c['a1'].replace('+3V3_MOD', 'VS'), c['a0'].replace('+3V3_MOD', 'VS'),
                   n, n, fch['value'], n, n, n, n), (269.24, t['y0'] + 71.12))
    return sh


RELAY_DIAG = ('Relay diagnosis (CIF §7b)', (
    'Coil supply = +5V_24 (U? DC/DC, Power sheet).\n'
    'Read ≥ 30 ms after switching.\n\n'
    'OFF, FB HIGH, I ≈ 0 → OK, relay off\n'
    'OFF, FB LOW → open coil, no +5V_24\n'
    '   or shorted driver\n'
    'OFF, FB HIGH, I > 5 mA → contacts welded\n'
    'ON, FB LOW, I in window → OK (LED 6.7 mA + load)\n'
    'ON, FB HIGH → driver or GPIO not switching\n'
    'ON, FB LOW, I ≈ 0 → contact not closing,\n'
    '   output PTC or input fuse open, or no 24 V\n'
    'ON, I over limit → short / stall (ALERT → PA15)\n'
    'any, VBUS < 20 V → 24 V supply fault\n\n'
    'FB = coil feedback: 10k / 15k divider + 10 nF\n'
    'into the TCA9535 expander (I²C1 0x20, P00-P03,\n'
    'Relays 3-4 sheet): 3.0 V when the coil is off\n'
    'and intact, ~0 V when energised, ≈ 3.5 V at the\n'
    'turn-off peak (inputs are 5.5 V-tolerant).\n'
    'Read input port 0 (register 0x00) over I²C.\n'
    'I = INA226 load current, VBUS = 24 V rail.\n\n'
    'INA226 (30 mΩ, CIF §6a): CONFIG 0x4327,\n'
    'CAL 1707 (LSB 100 µA, FS 2.73 A),\n'
    'MASK/ENABLE 0x8001 (SOL, latched),\n'
    'ALERT limit 30000 = 2.5 A default; set each\n'
    "channel's value from the CANopen dictionary.\n"
    '"Current present" threshold 5 mA.\n'
    'On ALERT LOW: read MASK/ENABLE of each INA226\n'
    '(AFF bit 4) to find the channel; the read also\n'
    'clears the latch. Switch it OFF, report on CAN.'))

RELAY_LOADS = ('Loads (CIF §7, all 24 V DC)', (
    'CH1 safety light: Hanyoung T084-PAD24Y-D\n'
    '   (LED + motor). Current TBD: measure,\n'
    '   then set its window (est. 0.1-0.3 A).\n'
    'CH2 LED DRL: ≤ 2 A continuous.\n'
    'CH3 battery stopper: Heschen HS-1564B 24 V\n'
    '   push-pull solenoid, 1.5 A, intermittent\n'
    '   (80 °C after 3 min continuous): firmware\n'
    '   enforces a maximum on-time + cool-down.\n'
    'CH4 spare: ≤ 2 A continuous.\n\n'
    'Every channel: 24 V / 2 A continuous,\n'
    '{F_CH_VALUE} hold PTC per output (CIF §7a: fuse\n'
    'per channel). Shunt on the supply side of the\n'
    'contact, so the INA226 never sees the load\n'
    'flyback (−0.7 V < −0.3 V input limit) and a\n'
    'welded contact still shows current while OFF.\n\n'
    'Inductive loads (solenoid): SS34 flyback at\n'
    'each output on the board; also fit an SS14-class\n'
    'diode at the solenoid itself.\n\n'
    'Coil budget: 4 × 71 mA ≈ 285 mA from +5V_24\n'
    '(U? URB2405S, 1.2 A).\n'
    'All relays OFF in reset / boot / firmware\n'
    'update: 100k gate pull-downs; PA8 reads LOW in\n'
    'reset (UCPD pull-down), PA7 is pulled DOWN by\n'
    'the bootloader (CIF §2c).'))


# ---------------------------------------------------------------- sensors (template: Flasher Sensors blocks 3 + 4)
def sensor_sheet():
    sh = Sheet.from_template(FL + 'Sensors.kicad_sch', 'Sensors', 'Sensors.kicad_sch',
                             'Sheet 7: two Autonics PNP sensor inputs (PC817 opto, as on the MES4-Flasher)', 7)
    drop_texts(sh)
    sh.delete_region(0, 15, 420, 130.5)
    sh.delete_region(0, 243, 420, 285)
    for shunt in ('R31', 'R32'):
        p = sh.part_by_tag('old:' + shunt)
        a, b = p.p('1'), p.p('2')
        sh.wire(a, b)
    sh.remove_parts(['old:U9', 'old:U10', 'old:C10', 'old:C11', 'old:R31', 'old:R32'])
    sh.clean()
    sh.move_region(0, 130, 420, 242.5, 0, -111.76)
    # rename
    for old, new in (('SENS3_PWR', 'SENS1_PWR'), ('SENS3', 'SENS1'), ('SENS4_PWR', 'SENS2_PWR'), ('SENS4', 'SENS2')):
        relabel(sh, old, new, kinds=('label',))
    m = {'J13': 1, 'J14': 2}
    for oldj, n in m.items():
        setf(sh.part_by_tag('old:' + oldj), value='SENS%d' % n,
             desc='Autonics PNP sensor %d: 1 = +24 V (brown, 100 mA PTC), 2 = output (black), 3 = 0 V (blue)' % n)
    blocks = [(1, 'PB6', dict(J='J13', F='F5', R='R14', D='D31', U='U3', RP='R18', C='C30')),
              (2, 'PC15', dict(J='J14', F='F6', R='R15', D='D32', U='U4', RP='R19', C='C31'))]
    for n, gpio, refs in blocks:
        for k, r in refs.items():
            sh.part_by_tag('old:' + r).tag = 's%d:%s' % (n, k)
        p = sh.part_by_tag('s%d:U' % n)
        p.set('Description', 'PC817 opto: sensor %d output (24 V) → %s HIGH' % (n, gpio))
        y0 = 20.32 if n == 1 else 76.20
        sh.text('Sensor %d → %s: Autonics PNP proximity sensor, PC817 opto input' % (n, gpio), (17.78, y0 + 2.54),
                size=2, bold=True)
        sh.text('{s%d:J}: 1 = +24 V (brown) through {s%d:F} 100 mA PTC, 2 = sensor output (black), 3 = 0 V (blue).\n'
                'Output ON (24 V): ≈ 2.3 mA through {s%d:R} 10k + {s%d:U} LED → %s HIGH (3.3 V, emitter follower).\n'
                'Output OFF, cable unplugged or broken: %s LOW ({s%d:RP} 10k pull-down).\n'
                '{s%d:D} 1N4148W: reverse clamp across the opto LED. {s%d:C} 100 nF / 50 V: supply decoupling + ESD.\n'
                'A shorted sensor cable trips {s%d:F} only: the other sensor and the board keep running.'
                % (n, n, n, n, gpio, gpio, n, n, n, n), (177.80, y0 + 12.70))
    sh.box(15.24, 132.08, 297.18, 175.26, 'Sensor inputs: notes')
    sh.text(
        'For 3-wire PNP (sourcing) 24 V sensors, e.g. Autonics PRD08 / PR series (brown +V, black OUT, blue 0 V).\n'
        'NPN (sinking) sensors need a different input circuit.\n\n'
        'Same circuit as the MES4-Flasher sensor channels 3 / 4 (PB6 / PC15), without the INA226 supply monitors.\n'
        'GPIO budget: all 14 module pins are used (Main sheet). More sensors can use the TCA9535 expander\n'
        '(Relays 3-4 sheet), which has 12 spare inputs (P04-P17), polled over I²C.\n\n'
        'PB6: the ST bootloader enables a 25-55 kΩ pull-up on PB6 (blank chip only); with the 10k pull-down it\n'
        'reads LOW, which is harmless for an input. PC15: input only (RTC-domain pin, CIF rule 10): fine here.\n'
        'Interrupts: PB6 → EXTI6. PC15 shares EXTI15 with PA15 (INA226 ALERT): give EXTI15 to PC15 (sensor 2)\n'
        'and poll ALERT, which the INA226 latches (MASK/ENABLE LEN = 1), so no fault is missed.\n'
        'No back-powering: the PC817 collectors run from +3V3_MOD (module finger 4), so nothing drives the\n'
        'module pins while it is unpowered.', (17.78, 139.70))
    return sh


# ---------------------------------------------------------------- load cell (template: Flasher LoadCell, unchanged circuit)
def loadcell_sheet():
    sh = Sheet.from_template(FL + 'LoadCell.kicad_sch', 'LoadCell', 'LoadCell.kicad_sch',
                             'Sheet 8: load cell ADC (ADS1232, CIF §8, as on the MES4-Flasher)', 8)
    drop_texts(sh)
    for p in sh.parts:
        if not B.D(p.lib_id).power:
            p.tag = 'lc:' + p.tag[4:]
    T = sh.text
    T('Load cell inputs {lc:J15} / {lc:J18} + RC filters (CIF §8a)', (17.78, 22.86), size=2, bold=True)
    T('{lc:J15} SIG (KF250NH 3-pin):\n1 SIG+ green, 2 SIG- white, 3 shield.\n'
      '{lc:J18} EXC (KF250NH 3-pin):\n1 EXC+ red, 2 EXC- black, 3 shield.\n'
      'Shields: yellow, GND here only.\nTension cells may swap SIG+ / SIG-:\nfix the sign in firmware.', (17.78, 68.58))
    T('{lc:D35} / {lc:D36} BAV199 (≤ 5 nA, typ. pA): clamp the ADC\ninputs to GND / AVDD after the 100 Ω, so an ESD hit\n'
      "on the cable can't drive them past the rails (ADS1232\nis 750 V HBM). Leakage × ≈ 0.2 kΩ source ≪ 1 µV.",
      (104.14, 116.84))
    T('Signal and reference filters: 100 Ω per leg, 100 nF C0G across, 10 nF to GND (CIF §8a).\n'
      'The reference gets the same network so both time constants match (TI SBAS350 §8.2).\n'
      'REFP / REFN are sensed at {lc:J18} pins 1 / 2: route them as their own pair from the\n'
      'connector pads, not from the 5 V / GND planes. {lc:C21} = PGA bypass (pins 9-10).', (17.78, 145.54))
    T('{lc:U13} ADS1232 24-bit bridge ADC (TI SBAS350 weigh-scale configuration)', (165.10, 22.86), size=2, bold=True)
    T('A0 = GND (channel 1). GAIN1 / GAIN0 = 1 / 1 → gain 128, ±19.5 mV at a 5 V reference. SPEED = GND → 10 SPS, rejects 50 and 60 Hz.\n'
      'TEMP = GND. CLKIN = GND → internal oscillator, XTAL2 open. Unused channel 2 inputs to GND (TI weigh-scale example).\n'
      'AVDD = +5V via {lc:FB1} = bridge excitation → ratiometric. AVDD range 2.7-5.3 V (SBAS350 §5.3).\n'
      'PDWN (PA6) and SCLK (PA5) have 100k pull-downs: the ADC stays powered down until the firmware runs the power-up sequence.\n'
      'DRDY/DOUT → PA4. PA4 / PA5 are 3.6 V-max pins: fine, all ADC logic runs at 3.3 V. Input common mode 2.5 V (needs 1.5-3.5 V at gain 128).',
      (165.10, 137.16))
    T('Load cell firmware (CIF §8b, TI SBAS350 §7.4.5)', (17.78, 172.72), size=2, bold=True)
    T('Power-up: keep PA6 (PDWN) LOW until +5V and 3V3 are stable, wait ≥ 10 µs, then PDWN HIGH ≥ 26 µs, LOW ≥ 26 µs, HIGH.\n'
      "Read: wait for DRDY/DOUT LOW, clock 24 bits on SCLK (MSB first, two's complement). Clocking 26 bits instead also runs the\n"
      'offset self-calibration: do it after power-up and when the temperature changes. Discard the first conversions after power-up or reset.\n\n'
      'Scale: 2 × SOP SOPLF-102 (1.5 t, 1.5 mV/V) summed in the junction box → 7.5 mV full scale at 5 V ≈ 38 % of ±19.5 mV, ≈ 2.5 µV per kg.\n'
      'Bridge current ≈ 13 mA (two 780 Ω cells) from +5V. Warn at 1.5 t, alarm at 2.0 t total. Re-calibrate the scale factor (the old HX711\n'
      'factor was taken at 3.3 V). Filtering as before: 0.5 kg noise threshold, ±0.25 kg stability window, 0.1 kg rounding.\n\n'
      '5 V load cell only: {lc:J18} pin 1 is the +5V rail through {lc:FB1}. Never land a 24 V wire on {lc:J15} / {lc:J18}\n'
      '(same push-in terminal type as the relay and sensor outputs): mark them "5V LOAD CELL" on the silk.\n'
      'Excitation comes from +5V (Power sheet: URB2405S → PTC → ferrite pi filter), the same rail as the module.',
      (17.78, 177.80))
    return sh


# ---------------------------------------------------------------- main (template: Flasher Main, trimmed)
def main_sheet():
    sh = Sheet.from_template(FL + 'Main.kicad_sch', 'Main', 'Main.kicad_sch',
                             'Sheet 2: module socket, ST-Link, reset, I²C pull-ups, power LEDs', 2)
    drop_texts(sh)
    sh.delete_region(14, 19, 161, 103)          # USB-C input (no USB on this board)
    sh.delete_region(161.5, 183.5, 285.5, 283)  # GPIO / I2C test headers + ESD (all GPIOs are used)
    sh.remove_parts(['old:J6', 'old:R44', 'old:R45'])  # 1x7 SWD / UART header: STDC14 only
    sh.delete_region(314, 19, 405, 103)          # CAN header + RJ45: moved to the CAN sheet
    sh.clean()
    for it in list(sh.items):
        if it[0] == 'label' and it[1] in ('PA7', 'PB3', 'CANH', 'CANL'):
            a = first(it, 'at')
            sh.items.remove(it)
            sh.glabel(it[1], (R2(a[1]), R2(a[2])), int(float(a[3])))
    # PA2 / PA3: servo moved to the I2C-UART bridge; back to relay 3 / 4 coil feedback next (see HANDOFF.md)
    sh.items = [it for it in sh.items if not (it[0] == 'global_label' and it[1] in ('PA2', 'PA3'))]
    sh.clean()
    sh.nc(sh.part_by_tag('old:J1').p('43'))
    sh.nc(sh.part_by_tag('old:J1').p('45'))
    sh.part_by_tag('old:J1').set('Description', 'MES4-MCU module socket, TE 2199230-3 M.2 B-key 4.2 mm (MES4-CIF rev A-d6)')
    sh.part_by_tag('old:LED1').set('Description', 'red: module +5V present')
    sh.part_by_tag('old:R5').set('Description', 'I²C1 SDA pull-up to the module 3V3 (CIF rule 7)')
    sh.part_by_tag('old:R6').set('Description', 'I²C1 SCL pull-up to the module 3V3 (CIF rule 7)')
    T = sh.text
    T('Power indicators', (165.10, 22.86), size=2, bold=True)
    T('{LED1} red  = module +5V present (3 mA).\n{LED2} green = module 3V3 present\n(fed from finger 4, ~0.7 mA).',
      (165.10, 80.01))
    T('I²C1 + ALERT pull-ups', (223.52, 22.86), size=2, bold=True)
    T("CIF rule 7: always fitted,\nto the module's 3V3 (finger 4).\n2.2k: 4 × INA226 at 400 kHz.\n"
      '{R20}: INA226 ALERT wire-OR (PA15).', (223.52, 80.01))
    T('Reset', (271.78, 22.86), size=2, bold=True)
    T('Pulls NRST low only.\nNo capacitor: C6 100 nF\nis on the module (CIF §4a).', (271.78, 80.01))
    sh.box(314.96, 20.32, 403.86, 101.60, 'CAN bus (page 3)')
    T('Module CANH / CANL (fingers 1 / 3) go to the CAN sheet\n'
      'as global labels:\n\n'
      '{CAN/J_DB9} DB9 male to the IPC: 1 GND, 3 CAN_H, 5 CAN_L.\n'
      '{CAN/J_RJ} 1x4 RJ45, no magnetics: 1 CAN_H, 2 CAN_L,\n'
      '3 GND on every port (T568B: white-orange, orange,\n'
      'white-green).\n\n'
      'All five ports are one bus, wired in parallel.\n'
      'ESD at each connector: {CAN/D_DB9}, {CAN/D_RJ} (H24VNT2B).\n'
      'Transceiver + 120 Ω terminator (JP1) are on the module.', (317.50, 30.48))
    sh.box(15.24, 20.32, 160.02, 101.60, 'Module GPIO map: all 14 used')
    T('PA8   finger 31  out  relay 1 drive, safety light ({Relays1-2/ch1:Q})\n'
      'PC6   finger 29  out  relay 2 drive, LED DRL ({Relays1-2/ch2:Q})\n'
      'PB3   finger 61  out  relay 3 drive, battery stopper ({Relays3-4/ch3:Q})\n'
      'PA7   finger 35  out  relay 4 drive, spare ({Relays3-4/ch4:Q})\n'
      'PA2 / PA3  fingers 45 / 43  not connected (servo now on the I²C bridge {Winch/U_BRG});\n'
      '      TODO: back to relay 3 / 4 coil feedback per the MES4 standard (HANDOFF.md)\n'
      'PA0   finger 49  out  winch CLK relay ({Winch/K_CLK})\n'
      'PA1   finger 47  out  winch ACLK relay ({Winch/K_ACLK})\n'
      'PA15  finger 63  in   INA226 ALERT, all four wire-OR ({R20} 10k pull-up)\n'
      'PA4   finger 41  in   ADS1232 DRDY/DOUT ({LoadCell/lc:U13})\n'
      'PA5   finger 39  out  ADS1232 SCLK (100k pull-down)\n'
      'PA6   finger 37  out  ADS1232 PDWN (100k pull-down)\n'
      'PB6   finger 59  in   Autonics sensor 1 ({Sensors/s1:U} PC817)\n'
      'PC15  finger 51  in   Autonics sensor 2 ({Sensors/s2:U} PC817)\n'
      'I²C1 SDA / SCL  fingers 53 / 55: INA226 0x40 / 0x41 / 0x44 / 0x45, TCA9535 0x20\n'
      'Not used: USB 23 / 25 (open, CIF rule 8). VCP TX / RX: STDC14 only.\n'
      'Differs from MES4-CIF §2c: relay coil feedback on the TCA9535 ({Relays3-4/U_EXP}, polled,\n'
      'CIF §7c), freeing USART2 for the servo and PA0 / PA1 for the winch.', (17.78, 30.48))
    T('Links to the other pages', (17.78, 109.22), size=2, bold=True)
    T('Page 1: block diagram and page list.\n'
      'Page 3 CAN: DB9 male to the IPC + 1x4 RJ45, ESD.\n'
      'Page 4 Power: XT30 24 V input, fuse, reverse-polarity FET, TVS, noise filter, 24 V → 5 V.\n'
      'Pages 5-6 Relays: PA8 / PC6 / PB3 / PA7 drive, coil feedback via TCA9535 (polled), 4 × INA226.\n'
      'Page 7 Sensors: PB6 / PC15 (two Autonics PNP sensors).\n'
      'Page 8 LoadCell: PA4 DRDY, PA5 SCLK, PA6 PDWN.\n'
      'Page 9 AuxPower: IMU 9 V (MES3.1), screen USB-C 5 V / 3 A, door servo (FE-URT-2, USART2).\n'
      'Page 10 Winch: CLK / ACLK relays (PA0 / PA1) + SC16IS740 servo UART bridge (I²C 0x48).\n'
      'Signals shared between pages are global labels.', (17.78, 115.57))
    T('MES4-MCU module socket (TE 2199230-3, M.2 B-key 4.2 mm)', (17.78, 160.02), size=2, bold=True)
    T('Odd fingers (card top) on the left, power on the right.\n+5V = fingers 20 + 22. GND = all other fingers + the\n'
      'hold-down pads (stacked pin). USB 23/25 open (CIF rule 8).\nModule hold-down: {H5} M3 × 2.5 mm SMD standoff + M3\n'
      'screw, 40.25 mm from the socket posts (42 mm card).', (17.78, 254.00))
    T('ST-Link V3MINIE (STDC14) + ESD', (165.10, 109.22), size=2, bold=True)
    T('STDC14 per ST UM2448 Table 6: 3 T_VCC, 4 SWDIO, 6 SWCLK, 12 NRST,\n'
      '13 T_VCP_RX (probe → PA10), 14 T_VCP_TX (probe ← PA9), 5/7/11 GND.\n'
      'Never tie SWD, NRST or VCP to GND (MES3 bug). No BOOT0 button (CIF §4).', (165.10, 168.91))
    T('{D2}-{D6}: H5VSD3B ESD (5 V, 1.5 pF), pin 2 to GND.', (251.46, 172.72))
    T('Mechanical', (317.50, 109.22), size=2, bold=True)
    T('Design notes', (317.50, 137.16), size=2, bold=True)
    T('1. Purpose: E-Crawler carrier for one MES4-MCU module\n'
      '   (follows MES4-CIF rev A-d6). Circuits from the\n'
      '   MES4-Flasher: relays, opto inputs, load cell, 24 V in.\n'
      '2. No hot-plug (rule 5): unplug the 24 V XT30 before\n'
      '   inserting or removing a module (no power switch).\n'
      '3. +5V (fingers 20 / 22) = {Power/U_DCDC} URB2405S → {Power/F_MOD} PTC\n'
      '   → {Power/FB_5V} ferrite: 4.75-5.5 V, ≥ 300 mA (rule 2, 4).\n'
      '4. +3V3_MOD = module LDO output on finger 4, never\n'
      '   driven (rule 3, ≤ 50 mA): LED 0.7 + pull-ups ≤ 3.3\n'
      '   + 2 × PC817 0.7 + 4 × INA226 1.7 + ADS1232 0.1\n'
      '   + ST-Link VTref ≈ 10 mA.\n'
      '5. NRST: {SW1} and STDC14 pin 12 only pull low\n'
      '   (wired-OR). No extra capacitance (C6 on the module).\n'
      '6. ESD (rule 8): H5VSD3B on every STDC14 signal,\n'
      '   H24VNT2B on CANH / CANL, no series R on CAN.\n'
      '7. No back-powering (rule 6): carrier logic runs from\n'
      '   +3V3_MOD (pull-ups, PC817s, INA226, ADS1232 DVDD).\n'
      '8. All relay drives OFF in reset: 100k gate pull-downs.\n'
      '9. Parts: LCSC numbers in each symbol\'s LCSC field.', (317.50, 142.24))
    sh.box(162.56, 184.15, 284.48, 281.94, 'Board connectors')
    T('{Power/J_IN} 24V IN, XT30 male right-angle: 1 = +24 V (flat end),\n   2 = GND_24V (chamfered end).\n'
      '{Relays1-2/ch1:J} / {Relays1-2/ch2:J} / {Relays3-4/ch3:J} / {Relays3-4/ch4:J} RLY1-4 OUT (KF250NH 2-pin):\n'
      '   1 = switched +24 V, 2 = GND_24V.\n'
      '{Sensors/s1:J} / {Sensors/s2:J} SENS1 / SENS2 (KF250NH 3-pin): 1 = +24 V\n'
      '   (100 mA PTC, brown), 2 = output (black), 3 = 0 V (blue).\n'
      '{LoadCell/lc:J15} LC SIG: 1 SIG+ green, 2 SIG- white, 3 shield.\n'
      '{LoadCell/lc:J18} LC EXC: 1 EXC+ red, 2 EXC- black, 3 shield.\n'
      '   5 V load cell only: never 24 V.\n'
      '{CAN/J_DB9} CAN DB9 male (IPC): 1 GND, 3 CAN_H, 5 CAN_L.\n'
      '{CAN/J_RJ} CAN RJ45 x4: 1 CAN_H, 2 CAN_L, 3 GND (T568B).\n'
      '{AuxPower/J_IMU} IMU 9V (KF250NH 2-pin): 1 = +9 V after the switch, 2 = GND.\n'
      '{AuxPower/J_USB} SCREEN USB-C: 5 V / 3 A power only (no data).\n'
      '{AuxPower/J_SRVP} SERVO 24V: 1 GND_24V, 2 +24 V (3 A PTC).\n'
      '{AuxPower/J_SRVU} SERVO UART: 1 GND, 2 +5 V, 3 RX, 4 TX.\n'
      '{Winch/J_WINCH} WINCH: 1 CLK, 2 COM, 3 ACLK (relay contacts).\n'
      '{J3} STDC14: ST-Link V3MINIE (SWD, NRST, VCP).\n'
      'Test points: Power sheet.', (165.10, 191.77))
    return sh


# ---------------------------------------------------------------- CAN (new): DB9 to the IPC + 1x4 RJ45
def can_sheet():
    B.register_symbol(CP.rj45x4_symbol())
    sh = Sheet('CAN', 'CAN.kicad_sch',
               'Sheet 3: CAN bus connectors: DB9 male to the IPC + 1x4 RJ45 (no magnetics), ESD', 3)
    # ---- DB9 male to the IPC
    sh.box(15.24, 20.32, 140.97, 120.65, 'IPC link: DB9 male')
    db = sh.part('Connector:DE9_Pins_MountingHoles', 'J', 'D-SUB-DR-9PCG-BB', (45.72, 66.04), mirror='y',
                 fp='Connector_Dsub:DSUB-9_Pins_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm',
                 lcsc='C19077344', tag='J_DB9', fields=((0, -19.05), (0, -16.51), None),
                 ds='https://www.lcsc.com/product-detail/C19077344.html',
                 desc='CAN to the IPC: DB9 male (pins), right angle, THT, XUNPU D-SUB-DR-9PCG-BB. '
                      'Pinout per the IPC: 1 GND, 3 CAN_H, 5 CAN_L; shell to GND')
    sh.wire(db.p('5'), (66.04, db.p('5')[1]))
    sh.glabel('CANL', (66.04, db.p('5')[1]))
    sh.wire(db.p('3'), (66.04, db.p('3')[1]))
    sh.glabel('CANH', (66.04, db.p('3')[1]))
    g1 = db.p('1')
    sh.wire(g1, (58.42, g1[1]), (58.42, g1[1] + 2.54))
    sh.pwr('GND', (58.42, g1[1] + 2.54))
    sh.wire(db.p('0'), (db.p('0')[0], db.p('0')[1] + 2.54))
    sh.pwr('GND', (db.p('0')[0], db.p('0')[1] + 2.54))
    for n in ('2', '4', '6', '7', '8', '9'):
        sh.nc(db.p(n))
    d1 = fpart(sh, 'D23', (106.68, 60.96), tag='D_DB9', fields=((0, -6.35), (0, -3.81), None),
               desc='CAN ESD at the DB9 (CIF rule 8): H24VNT2B, no series resistors')
    sh.wire(d1.p('A1'), (92.71, 60.96))
    sh.glabel('CANH', (92.71, 60.96), 180)
    sh.wire(d1.p('A2'), (120.65, 60.96))
    sh.glabel('CANL', (120.65, 60.96), 0)
    sh.pwr('GND', d1.p('common'))
    sh.text('{J_DB9} XUNPU D-SUB-DR-9PCG-BB: DB9 male (pins), right angle,\n'
            '4-40 shell, KiCad DSUB-9 footprint (EdgePinOffset 7.70 mm).\n'
            'Pinout per the IPC: 1 = GND, 3 = CAN_H, 5 = CAN_L, the rest open.\n'
            'Shell / mounting holes to GND (as the RJ45 shield).\n'
            'Male on the board and on the IPC: use a straight-through\n'
            'female-female DB9 cable (1-1, 3-3, 5-5).\n'
            'Not the CiA 303-1 DB9 pinout (2 CAN_L, 7 CAN_H, 3 GND):\n'
            'a standard CAN DB9 cable or adapter will not match.\n'
            '{D_DB9} H24VNT2B: ESD at the connector, no series R (CIF rule 8).', (17.78, 88.90))
    # ---- 1x4 RJ45
    sh.box(143.51, 20.32, 403.86, 120.65, 'CAN ports: 1x4 RJ45, no magnetics')
    xs = (182.88, 238.76, 294.64, 350.52)
    yc = 60.96
    fp = B.LIBNAME + ':' + CP.RJ_FP
    for u, X in enumerate(xs, start=1):
        p = sh.part(B.LIBNAME + ':' + CP.RJ_NAME, 'J', 'HC-RJ45-059-4-4', (X, yc), unit=u, group='J_RJ',
                    fp=fp, lcsc=CP.RJ_LCSC, tag='J_RJ' if u == 1 else 'J_RJ%d' % u,
                    fields=((-7.62, -16.51), (-7.62, -13.97), 'left'), hide_value=(u != 1),
                    ds='https://www.lcsc.com/product-detail/C3000204.html',
                    desc='CAN ports: RJ45 1x4 ganged, shielded, no magnetics, no LEDs (HCTL HC-RJ45-059-4-4). '
                         'Each port: 1 CAN_H, 2 CAN_L, 3 GND (T568B white-orange / orange / white-green)')
        base = 8 * (u - 1)
        ph, pl, pg = p.p(str(base + 1)), p.p(str(base + 2)), p.p(str(base + 3))
        sh.wire(ph, (X - 15.24, ph[1]))
        sh.glabel('CANH', (X - 15.24, ph[1]), 180)
        sh.wire(pl, (X - 15.24, pl[1]))
        sh.glabel('CANL', (X - 15.24, pl[1]), 180)
        sh.wire(pg, (X - 12.70, pg[1]))
        sh.pwr('GND', (X - 12.70, pg[1]), 270)
        for k in range(4, 9):
            sh.nc(p.p(str(base + k)))
        if u == 1:
            for n in ('33', '34'):
                a = p.p(n)
                sh.wire(a, (a[0], a[1] + 2.54))
                sh.pwr('GND', (a[0], a[1] + 2.54))
    d2 = fpart(sh, 'D23', (172.72, 101.60), tag='D_RJ', fields=((0, -6.35), (0, -3.81), None),
               desc='CAN ESD at the RJ45 bank (CIF rule 8): H24VNT2B, no series resistors')
    sh.wire(d2.p('A1'), (158.75, 101.60))
    sh.glabel('CANH', (158.75, 101.60), 180)
    sh.wire(d2.p('A2'), (186.69, 101.60))
    sh.glabel('CANL', (186.69, 101.60), 0)
    sh.pwr('GND', d2.p('common'))
    sh.text('{J_RJ} HCTL HC-RJ45-059-4-4: 4 ports, shielded, no magnetics, no LEDs.\n'
            'Every port: 1 = CAN_H (white-orange), 2 = CAN_L (orange): one twisted pair;\n'
            '3 = GND (white-green); 4-8 open. T568B colours, CiA 303-1 pinout,\n'
            'same as the MES4-Flasher RJ45. Shield tabs to GND.\n'
            'Footprint: pad positions from the JLC library part, drills from the\n'
            'HCTL drawing (32 × Ø1.0, shield Ø1.7, pegs Ø3.2). Port fronts 17 mm\n'
            'in front of the pin-1 row: place them at the board edge.\n'
            '{D_RJ} H24VNT2B: ESD at the RJ45 bank.', (205.74, 88.90))
    # ---- rules
    sh.box(15.24, 123.19, 403.86, 157.48, 'CAN bus rules (CIF §5, rules 8-9)')
    sh.text('All five ports (DB9 + 4 × RJ45) are the same bus, wired in parallel to the module\'s CANH / CANL (fingers 1 / 3).\n'
            'Keep the bus a line: IPC → DB9 → this board → one RJ45 → next node → ... A port used as a branch is a stub:\n'
            'keep each stub ≤ 0.3 m at 500 kbit/s. More long branches need a hub with its own transceivers, not more ports.\n'
            'Exactly two 120 Ω terminators, at the two physical ends of the bus: bridge JP1 on the module only if this board is an end.\n'
            'All nodes on one solid ground: pin 3 (RJ45) / pin 1 (DB9) carry it. Check with power off: CAN_H-CAN_L ≈ 60 Ω.\n'
            'Never carry 24 V in a CAN cable or connector (CIF rule 9): these jacks carry only CAN_H, CAN_L and GND.\n'
            'No series resistors on CAN_H / CAN_L (CIF rule 8): the module must drive the 60 Ω bus directly.', (17.78, 130.81))
    return sh


# ---------------------------------------------------------------- aux power (new): IMU 9 V + screen USB-C 5 V
def aux_sheet():
    B.register_symbol(AP.urb_10w_symbol())
    B.register_symbol(AP.urb_20w_symbol())
    sh = Sheet('AuxPower', 'AuxPower.kicad_sch',
               'Sheet 9: IMU 9 V supply (as on the MES3.1 carrier) + screen 5 V USB-C power', 9)
    sh.ann_rows = (103,)
    gy = lambda xy: sh.pwr('GND_24V', xy)
    gl = lambda xy: sh.pwr('GND', xy)
    y = 45.72
    # ---- shared 24 V filter
    sh.box(15.24, 20.32, 119.38, 101.60, 'Aux 24 V filter')
    sh.pwr('+24V', (25.40, y))
    l2 = npart(sh, 'L_DC', 'L', (35.56, y), rot=90, tag='L_AUX',
               desc='aux pi-filter inductor (IMU + screen converters), Sunlord SWPA5040S100MT 10 uH 2.1 A')
    ca = fpart(sh, 'C12', (55.88, 49.53), tag='C_AUX10', desc='aux 24 V filter capacitor')
    cb = fpart(sh, 'C13', (71.12, 49.53), tag='C_AUX100', desc='aux 24 V bulk (both converters)')
    sh.wire((25.40, y), l2.p('1'))
    sh.wire(l2.p('2'), (45.72, y), ca.p('1'), cb.p('1'))
    sh.label('+24V_AUX', (45.72, y))
    gy(ca.p('2'))
    gy(cb.p('2'))
    sh.text('{L_AUX} 10 µH (same part as L1) + {C_AUX10} / {C_AUX100}: a pi filter\n'
            'of its own for the IMU and screen converters, so the screen\'s\n'
            '20 W converter neither loads nor disturbs the logic supply\n'
            '(L1, Power sheet). Load at 24 V: IMU ≤ 0.5 A + screen ≤ 0.95 A\n'
            '≈ 1.45 A; {L_AUX} is rated 2.1 A (2.9 A saturation).\n'
            'Both converters are isolated: input side on GND_24V,\n'
            'output side on GND (same scheme as the logic DC/DC).', (17.78, 68.58))
    # ---- IMU 9 V
    sh.box(121.92, 20.32, 403.86, 101.60, 'IMU power: 9 V (as on the MES3.1 carrier)')
    sh.label('+24V_AUX', (132.08, y))
    ci = npart(sh, 'C_IMU_IN', 'C', (142.24, 49.53))
    ui = npart(sh, 'U_IMU', 'U', (177.80, 48.26), fields=((0, -8.89), (0, 11.43), None))
    sh.wire((132.08, y), ci.p('1'), ui.p('VIN'))
    gy(ci.p('2'))
    sh.wire(ui.p('GND'), (163.83, 50.80), (163.83, 54.61))
    gy((163.83, 54.61))
    sh.nc(ui.p('CTRL'))
    sh.nc(ui.p('5'))
    sh.nc(ui.p('8'))
    sh.wire(ui.p('-Vo'), (191.77, 50.80), (191.77, 54.61))
    gl((191.77, 54.61))
    co = npart(sh, 'C_IMU_OUT', 'C', (200.66, 49.53))
    tp9 = fpart(sh, 'TP1', (213.36, y), value='+9V_IMU', tag='TP_9V', fields=((0, -6.35), (0, -3.81), None))
    sw = npart(sh, 'SW_IMU', 'SW', (238.76, y), tag='SW_IMU', fields=((0, -8.89), (0, -6.35), None))
    sh.wire(ui.p('+Vo'), co.p('1'), tp9.p('1'), (223.52, y), sw.p('B'))
    sh.label('+9V_IMU', (223.52, y))
    gl(co.p('2'))
    sh.nc(sw.p('C'))
    j = fpart(sh, 'J9', (289.56, y), tag='J_IMU', value='IMU 9V',
              desc='IMU power out: 1 = +9 V after the switch, 2 = GND (KF250NH 3.5 mm push-in, as CN10 on the MES3.1)')
    rl = fpart(sh, 'R5', (266.70, 49.53), tag='R_LEDIMU', value='2.2k',
               desc='IMU power LED resistor: (9 V - 2 V) / 2.2k = 3.2 mA, 22 mW (JLC Basic)')
    ld = fpart(sh, 'LED2', (266.70, 57.15), rot=90, tag='LED_IMU', fields=((3.81, -1.27), (3.81, 1.27), 'right'),
               desc='green: IMU 9 V on (after SW2, so it lights only when the IMU is powered); KT-0805G, JLC Basic')
    sh.wire(sw.p('A'), (254.00, sw.p('A')[1]), (254.00, y), rl.p('1'), j.p('1'))
    sh.label('IMU_9V', (256.54, y))
    sh.wire(rl.p('2'), ld.p('A'))
    gl(ld.p('K'))
    sh.wire(j.p('2'), (279.40, 48.26), (279.40, 52.07))
    gl((279.40, 52.07))
    sh.text('Same parts as the MES3.1-Carrier-LH "IMU Power Supply @ 9V":\n'
            '{U_IMU} YLPTEC URB2409S-10WR3 (9-36 V in, 9 V 1.11 A, 10 W isolated, short-circuit protected;\n'
            'MES3.1 U15), {C_IMU_IN} 47 µF / 100 V and {C_IMU_OUT} 22 µF / 16 V (the datasheet\'s Cin / Cout),\n'
            '{SW_IMU} SS12D10G5 slide switch (MES3.1 U22, common = pin 2), {J_IMU} KF250NH 2-pin (MES3.1 CN10).\n'
            'CTRL open = on. {SW_IMU} is rated 0.5 A: check the IMU draws less (the converter gives up to 1.11 A).\n'
            '{LED_IMU} green (+ {R_LEDIMU} 2.2k, 3.2 mA) sits after {SW_IMU}: it lights only when the IMU terminal is powered.\n'
            'LCSC stock of URB2409S-10WR3 is low (78 on 2026-10-27): order early.', (124.46, 68.58))
    # ---- screen USB-C 5 V
    y2 = 132.08
    sh.box(15.24, 104.14, 403.86, 190.50, 'Screen power: USB-C 5 V / 3 A (ARZOPA Z1C portable monitor)')
    sh.label('+24V_AUX', (25.40, y2))
    cs = npart(sh, 'C_SCR_IN', 'C', (35.56, 135.89))
    us = npart(sh, 'U_SCR', 'U', (71.12, 134.62), fields=((0, -8.89), (0, 8.89), None))
    sh.wire((25.40, y2), cs.p('1'), us.p('+Vin'))
    gy(cs.p('2'))
    sh.wire(us.p('-Vin'), (57.15, 137.16), (57.15, 140.97))
    gy((57.15, 140.97))
    sh.nc(us.p('CTRL'))
    sh.nc(us.p('Trim'))
    sh.wire(us.p('GND'), (85.09, 137.16), (85.09, 140.97))
    gl((85.09, 140.97))
    o1 = npart(sh, 'C_SCR_OUT', 'C', (93.98, 135.89), tag='C_SCR1')
    o2 = npart(sh, 'C_SCR_OUT', 'C', (109.22, 135.89), tag='C_SCR2')
    o3 = fpart(sh, 'C4', (124.46, 135.89), tag='C_SCR3', desc='5 V screen output bypass')
    tp5 = fpart(sh, 'TP1', (134.62, y2), value='+5V_SCR', tag='TP_5VS', fields=((0, -6.35), (0, -3.81), None))
    fs = npart(sh, 'F_CH', 'F', (149.86, y2), rot=90, tag='F_SCR',
               desc='screen USB-C PTC, LUTE 2920L300/36GR: 3 A hold (the connector is rated 3 A)')
    sh.wire(us.p('+Vo'), o1.p('1'), o2.p('1'), o3.p('1'), tp5.p('1'), (139.70, y2), fs.p('1'))
    sh.label('+5V_SCR', (139.70, y2))
    for c in (o1, o2, o3):
        gl(c.p('2'))
    tv = fpart(sh, 'D1', (167.64, 135.89), rot=270, tag='D_VBUS', fields='right',
               desc='screen VBUS TVS, SMF6.0A (as on the MES4-Flasher USB-C)')
    r2 = fpart(sh, 'R10', (182.88, 135.89), tag='R_CC2', value='10k',
               desc='CC2 Rp to 5 V: advertises Type-C current 3.0 A (USB Type-C spec, Rp 10k to 5 V)')
    r1 = fpart(sh, 'R10', (190.50, 135.89), tag='R_CC1', value='10k',
               desc='CC1 Rp to 5 V: advertises Type-C current 3.0 A (USB Type-C spec, Rp 10k to 5 V)')
    usb = fpart(sh, 'J2', (220.98, 139.70), mirror='y', tag='J_USB', value='SCREEN 5V',
                fields=((0, -15.24), (0, -12.70), None),
                desc='screen power out, USB-C power-only receptacle (as J2 on the MES4-Flasher, rated 5 V 3 A): '
                     'source, 5 V, Rp 10k on CC1 / CC2 = 3.0 A')
    sh.wire(fs.p('2'), (157.48, y2), tv.p('K'), r2.p('1'), r1.p('1'), usb.p('VBUS'))
    sh.label('VBUS_SCR', (157.48, y2))
    gl(tv.p('A'))
    sh.wire(r1.p('2'), (190.50, usb.p('CC1')[1]), usb.p('CC1'))
    sh.label('SCR_CC1', (194.31, usb.p('CC1')[1]))
    sh.wire(r2.p('2'), (182.88, usb.p('CC2')[1]), usb.p('CC2'))
    sh.label('SCR_CC2', (194.31, usb.p('CC2')[1]))
    g = usb.p('GND')
    sh.wire(g, (g[0], g[1] + 2.54))
    gl((g[0], g[1] + 2.54))
    shd = usb.p('SHIELD')
    rs = fpart(sh, 'R7', (shd[0], shd[1] + 6.35), tag='R_SHD', fields='left')
    csd = fpart(sh, 'C3', (shd[0] + 7.62, shd[1] + 6.35), tag='C_SHD')
    sh.wire(shd, rs.p('1'))
    sh.wire(rs.p('1'), csd.p('1'))
    sh.label('SCR_SHIELD', (shd[0], shd[1] + 1.27))
    gl(rs.p('2'))
    gl(csd.p('2'))
    sh.text('{U_SCR} YLPTEC URB2405LD-20WR3: 9-36 V in, 5 V 4 A, 20 W isolated, short-circuit protected, 2" x 1" DIP.\n'
            'CTRL and Trim open (on, 5.0 V). {C_SCR_IN} 47 µF (datasheet C1 47-100 µF), {C_SCR1} / {C_SCR2} 22 µF (C2 / C3 10-22 µF).\n'
            '{F_SCR} 3 A PTC (same part as the relay outputs) + {D_VBUS} SMF6.0A, then {J_USB}: the MES4-Flasher\'s USB-C\n'
            'power-only receptacle, rated 5 V 3 A (3 A on VBUS; GND pins 1.25 A each).\n'
            '{R_CC1} / {R_CC2} 10k Rp to 5 V on CC1 / CC2: the monitor sees a Type-C source offering 5 V at 3.0 A.\n'
            '{R_SHD} 1 MΩ || {C_SHD} 2.2 µF: shell to GND, as on the MES4-Flasher.', (17.78, 160.02))
    sh.text('ARZOPA Z1C label: input 5 / 9 / 12 / 15 / 20 V DC, 3 A max: a USB-PD sink.\n'
            'This port has no PD controller, so it offers 5 V only (15 W max).\n'
            'The sibling Z1RC draws about 9 W (≈ 1.8 A at 5 V), so 5 V / 3 A should\n'
            'run it; check full brightness on the bench. If it needs 9 V or more,\n'
            'the port needs a USB-PD source controller instead.\n'
            'VBUS is always on (no cold-socket switch): plug in the monitor, or\n'
            'another sink, only; never a charger or a laptop.\n'
            'Power only: the video goes over the monitor\'s own HDMI / USB-C\n'
            'from the IPC. Rp is to 5 V: the monitor sinks at most 3 A.', (248.92, 114.30))
    # ---- door servo: Feetech via FE-URT-2 (as CN5 / CN13 on the MES2 Harvester)
    sh.box(15.24, 193.04, 403.86, 248.92, 'Door servo: Feetech, via the FE-URT-2 board (as on the MES2 Harvester)')
    y3 = 215.90
    sh.pwr('+24V', (25.40, y3))
    fv = npart(sh, 'F_CH', 'F', (35.56, y3), rot=90, tag='F_SRV',
               desc='servo 24 V PTC, LUTE 2920L300/36GR: 3 A hold (a servo short trips only this output)')
    c1 = fpart(sh, 'C28', (53.34, 219.71), tag='C_SRV1', desc='servo 24 V bypass at the terminal (ESD / HF)')
    c2 = npart(sh, 'C_IMU_IN', 'C', (71.12, 219.71), tag='C_SRV2', desc='servo 24 V local bulk (stall / start current)')
    jp = fpart(sh, 'J9', (96.52, 218.44), mirror='x', tag='J_SRVP', value='SERVO 24V',
               fields=((2.54, -3.81), (2.54, -1.27), 'left'),
               desc='FE-URT-2 24 V supply (as CN5 on the MES2 Harvester): 1 = GND_24V, 2 = +24 V via a 3 A PTC')
    sh.wire((25.40, y3), fv.p('1'))
    sh.wire(fv.p('2'), (45.72, y3), c1.p('1'), c2.p('1'), jp.p('2'))
    sh.label('+24V_SRV', (45.72, y3))
    gy(c1.p('2'))
    gy(c2.p('2'))
    sh.wire(jp.p('1'), (88.90, jp.p('1')[1]), (88.90, 222.25))
    gy((88.90, 222.25))
    # 5 V for the FE-URT-2 logic, from the screen converter (keeps servo-side faults off the module's 5 V)
    sh.label('+5V_SCR', (109.22, 205.74))
    f5 = fpart(sh, 'F1', (119.38, 205.74), rot=90, tag='F_SRV5', value='1.1A',
               desc='FE-URT-2 5 V PTC (Littelfuse 1206L110): a cable short trips this, not the screen supply')
    c5 = fpart(sh, 'C4', (137.16, 209.55), tag='C_SRV5', desc='FE-URT-2 5 V bypass')
    sh.wire((109.22, 205.74), f5.p('1'))
    sh.wire(f5.p('2'), (129.54, 205.74), c5.p('1'), (144.78, 205.74))
    sh.label('+5V_SRV', (129.54, 205.74))
    gl(c5.p('2'))
    # UART (USART2): 100 Ω series + H5VSD3B ESD at the connector (CIF rule 8), RX pull-up for an idle line
    yr, yt = 226.06, 238.76
    sh.glabel('SRV_UART_RX', (160.02, yr), 180)
    rpu = fpart(sh, 'R10', (165.10, yr - 3.81), tag='R_SRVPU', value='10k', fields='left',
                desc='servo RX pull-up: idle HIGH with the FE-URT-2 unplugged')
    sh.pwr('+3V3_MOD', rpu.p('1'))
    rr = fpart(sh, 'R36', (177.80, yr), rot=90, tag='R_SRVRX', desc='servo RX series resistor (CIF rule 8: 22-100 Ω)')
    dr = fpart(sh, 'D2', (190.50, yr + 3.81), rot=270, tag='D_SRVRX', fields='right',
               desc='servo RX ESD, H5VSD3B (5 V, 1.5 pF)')
    sh.wire((160.02, yr), rpu.p('2'), rr.p('1'))
    sh.wire(rr.p('2'), dr.p('A1'), (198.12, yr))
    sh.label('SRV_RX', (198.12, yr))
    gl(dr.p('A2'))
    sh.glabel('SRV_UART_TX', (160.02, yt), 180)
    rt = fpart(sh, 'R36', (177.80, yt), rot=90, tag='R_SRVTX', desc='servo TX series resistor (CIF rule 8: 22-100 Ω)')
    dt = fpart(sh, 'D2', (190.50, yt + 3.81), rot=270, tag='D_SRVTX', fields='right',
               desc='servo TX ESD, H5VSD3B (5 V, 1.5 pF)')
    sh.wire((160.02, yt), rt.p('1'))
    sh.wire(rt.p('2'), dt.p('A1'), (198.12, yt))
    sh.label('SRV_TX', (198.12, yt))
    gl(dt.p('A2'))
    ju = npart(sh, 'J_SRVU', 'J', (271.78, 213.36), fields=((2.54, -5.08), (2.54, -2.54), 'left'))
    g1 = ju.p('1')
    sh.wire(g1, (261.62, g1[1]), (261.62, g1[1] - 3.81))
    sh.pwr('GND', (261.62, g1[1] - 3.81), 180)
    for n, lab in (('2', '+5V_SRV'), ('3', 'SRV_RX'), ('4', 'SRV_TX')):
        sh.wire(ju.p(n), (254.00, ju.p(n)[1]))
        sh.label(lab, (254.00, ju.p(n)[1]), 180)
    sh.text('{J_SRVP} SERVO 24V and {J_SRVU} SERVO UART: same pinout\n'
            'as CN5 / CN13 on the MES2 Harvester, so its cables fit.\n'
            'The FE-URT-2 turns the UART into the Feetech half-duplex\n'
            'servo bus and passes the 24 V on to the servos.\n'
            'UART from the SC16IS740 I²C bridge (Winch\n'
            'sheet, 0x48): TX → pin 4, pin 3 → RX.\n'
            '{F_SRV} 3 A PTC on the servo 24 V. {F_SRV5} 1.1 A PTC on the\n'
            'FE-URT-2 5 V, fed from the screen converter so a\n'
            'servo-side short can\'t pull down the module supply.\n'
            '24 V only for 24 V servo types.\n'
            'No module GPIO used (MES4 standard pin map).', (294.64, 198.12))
    return sh


# ---------------------------------------------------------------- winch (new): IM03GR direction relays
def winch_sheet():
    B.register_symbol(AP.im03gr_symbol())
    sh = Sheet('Winch', 'Winch.kicad_sch',
               'Sheet 10: winch direction relays (IM03GR, as on the MES2_Extension) with hardware interlock', 10)
    sh.box(15.24, 20.32, 199.39, 147.32, 'Winch direction relays (as U1 / U2 on the MES2_Extension)')
    out = {}
    for k, (name, gpio, y0) in enumerate((('CLK', 'PA0', 60.96), ('ACLK', 'PA1', 111.76))):
        tag = 'K_' + name
        kr = npart(sh, 'K_WINCH', 'K', (101.60, y0), tag=tag, fields=((-7.62, -12.70), (-7.62, -15.24), 'left'),
                   desc='winch %s relay, TE IM03GR (5 V coil 28 mA, DPDT 2 A / 220 VDC)' % name)
        cp, cm = kr.p('1'), kr.p('8')
        sh.pwr('+5V_24', (83.82, cp[1] - 5.08))
        df = fpart(sh, 'D25', (83.82, y0), rot=270, tag='D_' + name, fields='left',
                   desc='winch %s relay coil flyback' % name)
        sh.wire((83.82, cp[1] - 5.08), (83.82, cp[1]), cp)
        sh.wire((83.82, cp[1]), df.p('K'))
        sh.wire(df.p('A'), (83.82, cm[1]), cm)
        q = fpart(sh, 'Q1', (86.36, y0 + 12.70), tag='Q_' + name, value='AO3400A',
                  fields=((5.08, -1.27), (5.08, 1.27), 'left'))
        setf(q, value='AO3400A', lcsc='C20917', fp='Package_TO_SOT_SMD:SOT-23', lib='Transistor_FET:AO3400A',
             ds='http://www.aosmd.com/pdfs/datasheet/AO3400A.pdf', desc='winch %s relay coil driver' % name)
        sh.wire(q.p('D'), (q.p('D')[0], cm[1]))
        sh.pwr('GND', q.p('S'))
        g = q.p('G')
        rg = fpart(sh, 'R11', (g[0] - 13.97, g[1]), rot=90, tag='RG_' + name, value='100Ω',
                   desc='winch %s driver gate resistor' % name)
        setf(rg, lcsc='C25076')
        rp = fpart(sh, 'R10', (g[0] - 2.54, g[1] + 3.81), tag='RP_' + name, value='100k', fields='left',
                   desc='winch %s gate pull-down: relay OFF in reset / boot' % name)
        setf(rp, lcsc='C25741')
        sh.wire(rg.p('2'), rp.p('1'), g)
        sh.pwr('GND', rp.p('2'))
        sh.wire((g[0] - 25.40, g[1]), rg.p('1'))
        sh.glabel(gpio, (g[0] - 25.40, g[1]), 180)
        out[name] = kr
    # contacts: each direction's common passes through the other relay's NC (pole 2) = interlock
    kc, ka = out['CLK'], out['ACLK']
    stubs = [(kc, '3', 'ILK_CLK'), (kc, '4', 'WINCH_CLK'), (kc, '6', 'WINCH_COM'), (kc, '7', 'ILK_ACLK'),
             (ka, '3', 'ILK_ACLK'), (ka, '4', 'WINCH_ACLK'), (ka, '6', 'WINCH_COM'), (ka, '7', 'ILK_CLK')]
    for kr, pin, lab in stubs:
        pp = kr.p(pin)
        sh.wire(pp, (pp[0] + 10.16, pp[1]))
        sh.label(lab, (pp[0] + 10.16, pp[1]))
    for kr in (kc, ka):
        sh.nc(kr.p('2'))
        sh.nc(kr.p('5'))
    j = fpart(sh, 'J11', (180.34, 86.36), tag='J_WINCH', value='WINCH',
              fields=((2.54, -3.81), (2.54, -1.27), 'left'),
              desc='winch controller direction inputs (as CN1 on the MES2_Extension): 1 CLK, 2 COM, 3 ACLK')
    for pin, lab in (('1', 'WINCH_CLK'), ('2', 'WINCH_COM'), ('3', 'WINCH_ACLK')):
        pp = j.p(pin)
        sh.wire(pp, (pp[0] - 12.70, pp[1]))
        sh.label(lab, (pp[0] - 12.70, pp[1]), 180)
    sh.box(15.24, 149.86, 199.39, 200.66, 'Notes')
    sh.text('Same relays and terminal as the MES2_Extension "WINCH CONTROL": TE IM03GR, 5 V coil (178 Ω, 28 mA) from\n'
            '+5V_24, contacts 2 A / 220 VDC, 60 W DC. They only switch the 48 V winch controller\'s direction inputs to\n'
            '{J_WINCH} pin 2 (COM): pin 1 = CLK, pin 3 = ACLK. They are not rated for the winch motor current.\n'
            'TE terminal assignment: coil 1 (+) / 8 (-); pole 1: 3 COM, 2 NC, 4 NO; pole 2: 6 COM, 7 NC, 5 NO.\n\n'
            'Drivers as on the relay sheets (CIF §7a): AO3400A, 100 Ω gate, 100k pull-down, so both relays are OFF\n'
            'during reset and boot (PA0 / PA1 float then). The Extension used 2SC2884 transistors without a pull-down.\n\n'
            'Hardware interlock (new, uses the spare second pole): CLK closes COM → ILK_CLK → {K_CLK} NO1 → CLK only\n'
            'while {K_ACLK} rests (its NC2 feeds ILK_CLK), and the same the other way. If both relays are energised, both\n'
            'outputs stay open, so the winch can never see both directions at once. Firmware still drives only one.', (17.78, 156.21))
    # ---- servo UART: SC16IS740 I2C-UART bridge (no module GPIO needed)
    sh.box(201.93, 20.32, 403.86, 147.32, 'Servo UART: SC16IS740 I²C-UART bridge (I²C1 0x48)')
    u = npart(sh, 'U_BRG', 'U', (279.40, 76.20), fields=((-12.70, -20.32), (5.08, 20.32), 'left'))
    vdd = u.p('VDD')
    sh.wire(vdd, (vdd[0], vdd[1] - 2.54), (vdd[0], vdd[1] - 5.08))
    sh.pwr('+3V3_MOD', (vdd[0], vdd[1] - 5.08))
    cb = fpart(sh, 'C4', (vdd[0] + 5.08, vdd[1] - 2.54), rot=90, tag='C_BRG', desc='SC16IS740 VDD bypass')
    sh.wire((vdd[0], vdd[1] - 2.54), cb.p('1'))
    sh.pwr('GND', cb.p('2'), 90)
    sh.pwr('GND', u.p('VSS'))
    for n in ('I2C/~{SPI}', 'A0/~{CS}', 'A1/SI'):  # I2C mode, A1 = A0 = VDD -> 0x48
        pp = u.p(n)
        sh.wire(pp, (pp[0] - 5.08, pp[1]))
        sh.pwr('+3V3_MOD', (pp[0] - 5.08, pp[1]), 90)
    rs = u.p('~{RESET}')
    sh.wire(rs, (rs[0] - 10.16, rs[1]))
    rr = fpart(sh, 'R10', (rs[0] - 10.16, rs[1] - 3.81), tag='R_BRGRST', value='10k', fields='left',
               desc='SC16IS740 RESET pull-up (firmware uses the IOControl soft reset)')
    sh.pwr('+3V3_MOD', rr.p('1'))
    for n, lab in (('SCL/SCLK', 'I2C1_SCL'), ('SDA', 'I2C1_SDA')):
        pp = u.p(n)
        sh.wire(pp, (pp[0] - 10.16, pp[1]))
        sh.glabel(lab, (pp[0] - 10.16, pp[1]), 180)
    for n in ('SO', '~{IRQ}', '~{RTS}'):
        sh.nc(u.p(n))
    ct = u.p('~{CTS}')
    sh.wire(ct, (ct[0] + 2.54, ct[1]))
    sh.pwr('GND', (ct[0] + 2.54, ct[1]), 90)
    for n, lab in (('TX', 'SRV_UART_TX'), ('RX', 'SRV_UART_RX')):
        pp = u.p(n)
        sh.wire(pp, (pp[0] + 12.70, pp[1]))
        sh.glabel(lab, (pp[0] + 12.70, pp[1]), 0)
    # 16 MHz crystal + 12 pF load caps
    y = npart(sh, 'Y_BRG', 'Y', (254.00, 106.68), tag='Y_BRG', fields=((5.08, -5.08), (5.08, -2.54), 'left'))
    x1, x2 = u.p('XTAL1'), u.p('XTAL2')
    sh.wire(x1, (241.30, x1[1]), (241.30, y.p('1')[1]), y.p('1'))
    sh.wire(x2, (x2[0], y.p('3')[1]), y.p('3'))
    ca = npart(sh, 'C_XT', 'C', (241.30, 110.49), tag='C_XT1', fields='left')
    cc = npart(sh, 'C_XT', 'C', (x2[0], 110.49), tag='C_XT2')
    sh.pwr('GND', ca.p('2'))
    sh.pwr('GND', cc.p('2'))
    sh.pwr('GND', y.p('2'), 180)
    sh.pwr('GND', y.p('4'))
    sh.text('{U_BRG} NXP SC16IS740IPW: I²C1 slave at 0x48 (A1 = A0 = VDD; INA226s 0x40-0x45, TCA9535 0x20).\n'
            'TX / RX → servo UART terminal (AuxPower sheet, 100 Ω + ESD there) → FE-URT-2.\n'
            '{Y_BRG} 16 MHz (CL 9 pF) + {C_XT1} / {C_XT2} 12 pF: baud = 16 MHz / (16 × divisor):\n'
            '1 Mbit/s (Feetech default, divisor 1), 500k (2), 250k (4) are exact.\n'
            'IRQ not connected (no module pin free): poll the LSR / RXLVL registers.\n'
            'CTS tied low (always clear), RTS open, RESET pulled up (soft reset via IOControl).\n'
            'Uses no module GPIO, so the MES4 standard pin map stays intact.', (204.47, 121.92))
    return sh


# ---------------------------------------------------------------- power (new)
def power_sheet():
    sh = Sheet('Power', 'Power.kicad_sch',
               'Sheet 4: 24 V input + noise filtering, isolated 24 V → 5 V, module 5 V feed', 4)
    sh.ann_rows = (107, 186)
    gy = lambda xy: sh.pwr('GND_24V', xy)
    gl = lambda xy: sh.pwr('GND', xy)
    R = 'right'
    # ======== row 1: 24 V input
    y = 50.80
    sh.box(15.24, 20.32, 195.58, 106.68, '24 V input: XT30, fuse, reverse-polarity FET, TVS, bulk')
    j = fpart(sh, 'J8', (25.40, y), mirror='y', tag='J_IN', fields=((-3.81, -1.27), (-3.81, 1.27), 'left'),
              desc='24 V DC input (Amass XT30PW-M30.G.Y right-angle male, pin 1 = + flat end, pin 2 = - chamfered end)')
    sh.wire(j.p('2'), (35.56, 53.34), (35.56, 58.42))
    gy((35.56, 58.42))
    f = npart(sh, 'F_IN', 'F', (50.80, y), rot=90)
    sh.wire(j.p('1'), (38.10, y), f.p('1'))
    sh.label('+24V_IN', (38.10, y))
    q = npart(sh, 'Q_RP', 'Q', (71.12, 53.34), rot=90, fields=((-3.81, -10.16), (-3.81, -7.62), 'left'))
    sh.wire(f.p('2'), (58.42, y), q.p('D'))
    sh.label('+24V_F', (58.42, y))
    rg = fpart(sh, 'R12', (71.12, 66.04), tag='RG', fields='left',
               desc='P-FET gate pull-down: the FET turns on only with the right input polarity')
    zd = npart(sh, 'DZ', 'D', (81.28, 58.42), rot=270, fields=R)
    sh.wire(q.p('G'), rg.p('1'))
    sh.wire(rg.p('1'), zd.p('A'))
    gy(rg.p('2'))
    tvs = npart(sh, 'TVS', 'D', (99.06, 54.61), rot=270, fields=R)
    cb = fpart(sh, 'C13', (116.84, 54.61), tag='C_BULK',
               desc='24 V bulk + damping of the input cable inductance (hot-plug ringing)')
    c10 = fpart(sh, 'C12', (134.62, 54.61), tag='C_IN10', desc='24 V input bypass')
    c100 = fpart(sh, 'C28', (152.40, 54.61), tag='C_IN100', desc='24 V input HF bypass')
    rl = fpart(sh, 'R43', (170.18, 54.61), tag='R_LED24')
    led = fpart(sh, 'LED5', (170.18, 62.23), rot=90, tag='LED24', fields=((3.81, -1.27), (3.81, 1.27), 'right'),
                desc='green: 24 V present (after the reverse-polarity FET)')
    sh.wire(q.p('S'), (zd.p('K')[0], y), tvs.p('K'), cb.p('1'), c10.p('1'), c100.p('1'), rl.p('1'),
            (177.80, y), (187.96, y))
    sh.wire(zd.p('K'), (zd.p('K')[0], y))
    for p in (tvs.p('A'), cb.p('2'), c10.p('2'), c100.p('2'), led.p('K')):
        gy(p)
    sh.wire(rl.p('2'), led.p('A'))
    sh.pwr('PWR_FLAG', (177.80, y))
    sh.pwr('+24V', (187.96, y))
    sh.text('{J_IN} XT30 (as on the MES4-Flasher): pin 1 + flat end, pin 2 - chamfered end.\n'
            '{F_IN} {F_IN_VALUE} fast fuse (Nano2 2410, 65 V): protects the XT30 and the board copper; the 8.5 A worst case\n'
            'stays under its 75 % derating. Each relay output has its own 3 A PTC, so a load short never blows {F_IN}.\n'
            '{Q_RP} P-MOSFET reverse-polarity block: correct polarity turns it on (Vgs clamped by {DZ},\n'
            '{RG} 10k to GND_24V); a reversed lead leaves it off. It replaces the Flasher\'s SS56 Schottky,\n'
            'which would dissipate ≈ 3-4 W here. AGM60P90D: -60 V, 13 mΩ, ≈ 1 W at 8.5 A: copper on the drain tab.\n'
            '{TVS} SMBJ30A (600 W): surges and spikes from motors and solenoids on the 24 V bus (CIF §7a).\n'
            '{C_BULK} 100 µF / 63 V electrolytic: bulk, and its ESR damps the cable inductance (hot-plug ringing).\n'
            '{C_IN10} / {C_IN100}: HF bypass. {LED24} green = 24 V present (after {Q_RP}).\n'
            '+24V feeds the relay contacts, the INA226 VBUS inputs and the sensor supplies.', (17.78, 76.20))
    sh.box(198.12, 20.32, 403.86, 106.68, 'Power budget and noise strategy')
    sh.text('24 V current: relays ≤ 4 × 2 A (CIF §7; realistic 3-5 A: lamp ~0.3 A, DRL, 1.5 A solenoid), sensors\n'
            '2 × ≤ 100 mA, logic DC/DC ≈ 0.15 A, IMU 9 V ≤ 0.5 A + screen 5 V ≤ 0.95 A + door servo ≤ 3 A (page 9).\n'
            'Realistic total ≈ 6-8 A. Every load at its limit at once (≈ 13 A) would exceed {F_IN} {F_IN_VALUE}\'s 75 % derating\n'
            '(11 A) and the XT30\'s 15 A rating: don\'t stall the servo while all four relays carry 2 A.\n\n'
            'Noise and transients, from the cable inwards:\n'
            '1. {TVS} SMBJ30A clamps surges and inductive spikes on the 24 V bus.\n'
            '2. {C_BULK} electrolytic damps the cable LC: no ringing above 24 V on hot-plug.\n'
            '3. {C_IN10} / {C_IN100} ceramics: low impedance for HF at the input.\n'
            '4. Pi filter {C_IN10} + {L_DC} + {C_DC10} / {C_DC100} feeds only the DC/DC: the logic supply is decoupled\n'
            '   from the bus, and the converter\'s switching noise stays off it.\n'
            '5. Isolated DC/DC: the grounds meet only at {NT}, so relay load currents never flow in GND.\n'
            '6. Pi filter {F_MOD} + {FB_5V} + {C_5VA} / {C_5VB} on the module 5 V, and {LoadCell/lc:FB1} again on the ADS1232 AVDD.\n'
            '7. Flyback diodes at every relay coil (1N4148W) and every output (SS34).\n'
            '8. Sensor supplies: 100 mA PTC + 100 nF / 50 V at each terminal.', (200.66, 27.94))
    # ======== row 2: filter + DC/DC, module feed, grounds
    y = 137.16
    sh.box(15.24, 109.22, 172.72, 185.42, 'Noise filter + isolated 24 V → 5 V')
    sh.pwr('+24V', (25.40, y))
    l1 = npart(sh, 'L_DC', 'L', (35.56, y), rot=90)
    cd1 = fpart(sh, 'C12', (53.34, 140.97), tag='C_DC10', desc='DC/DC input filter capacitor (pi filter, after the inductor)')
    cd2 = fpart(sh, 'C13', (71.12, 140.97), tag='C_DC100',
                desc='URB2405S input capacitor (YLPTEC typical application: 100 µF)')
    u = fpart(sh, 'U12', (101.60, 139.70), tag='U_DCDC', fields=((0, -8.89), (0, 11.43), None))
    sh.wire((25.40, y), l1.p('1'))
    sh.wire(l1.p('2'), (45.72, y), cd1.p('1'), cd2.p('1'), u.p('VIN'))
    sh.label('+24V_DC', (45.72, y))
    for p in (cd1.p('2'), cd2.p('2')):
        gy(p)
    sh.wire(u.p('GND'), (86.36, 142.24), (86.36, 147.32))
    gy((86.36, 147.32))
    sh.nc(u.p('CTRL'))
    sh.nc(u.p('5'))
    sh.nc(u.p('8'))
    sh.wire(u.p('-Vo'), (116.84, 142.24), (116.84, 147.32))
    gl((116.84, 147.32))
    co1 = fpart(sh, 'C14', (124.46, 140.97), tag='C_5V24A')
    co2 = fpart(sh, 'C15', (139.70, 140.97), tag='C_5V24B')
    sh.wire(u.p('+Vo'), co1.p('1'), co2.p('1'), (152.40, y), (162.56, y))
    gl(co1.p('2'))
    gl(co2.p('2'))
    sh.pwr('PWR_FLAG', (152.40, y))
    sh.pwr('+5V_24', (162.56, y))
    sh.text('{L_DC} 10 µH + {C_DC10} / {C_DC100}, with {C_IN10} on +24V: pi filter in front of the DC/DC only.\n'
            'Relay contacts, INA226s and sensors use the unfiltered +24V.\n'
            '{U_DCDC} URB2405S-6WR3 (as on the MES4-Flasher): 9-36 V in, 5 V 1.2 A, short-circuit protected.\n'
            'CTRL open = on. {C_DC100} = the maker\'s 100 µF input cap; {C_5V24A} / {C_5V24B} = output caps.\n'
            'The maker\'s EMC circuit adds a 470 µH common-mode choke + 1 nF Y caps: not fitted, because\n'
            '{NT} ties the grounds (the 1.5 kV isolation is not used). The maker lists hot-plug as unsupported:\n'
            '{L_DC} slows the inrush into {C_DC100}; {Q_RP} / {TVS} / {C_BULK} take the XT30 plug-in.\n'
            'Load: module ≤ 240 mA + 4 coils 285 mA + 2 winch coils 56 mA + load cell 13 mA ≈ 0.6 A (50 %).', (17.78, 157.48))
    sh.box(175.26, 109.22, 309.88, 185.42, 'Module + ADC 5 V feed (CIF rule 4)')
    sh.pwr('+5V_24', (182.88, y))
    fm = fpart(sh, 'F1', (193.04, y), rot=90, tag='F_MOD', value='1.1A',
               desc='module slot PTC (CIF rule 4: fuse per slot)')
    fb = npart(sh, 'FB_5V', 'FB', (208.28, y), rot=90)
    cm1 = fpart(sh, 'C16', (223.52, 140.97), tag='C_5VA', desc='module +5V bulk: place at the M.2 socket (fingers 20 / 22)')
    cm2 = fpart(sh, 'C2', (241.30, 140.97), tag='C_5VB', desc='module +5V bypass: place at the M.2 socket')
    sh.wire((182.88, y), fm.p('1'))
    sh.wire(fm.p('2'), fb.p('1'))
    sh.wire(fb.p('2'), cm1.p('1'), cm2.p('1'), (254.00, y), (264.16, y))
    gl(cm1.p('2'))
    gl(cm2.p('2'))
    sh.pwr('PWR_FLAG', (254.00, y))
    sh.pwr('+5V', (264.16, y))
    sh.text('{F_MOD} 1.1 A PTC: the fuse per module slot (CIF rule 4).\n'
            '{FB_5V} + {C_5VA} / {C_5VB}: pi filter, so relay-coil switching on\n'
            '+5V_24 stays off the module and the load-cell excitation.\n'
            '+5V → module fingers 20 / 22 (4.75-5.5 V, CIF rule 2) and the\n'
            'ADS1232 AVDD (LoadCell sheet). Place {C_5VA} / {C_5VB} at the socket.', (177.80, 160.02))
    sh.box(312.42, 109.22, 403.86, 185.42, 'Grounds')
    nt = fpart(sh, 'NT1', (342.90, 132.08), tag='NT', fields='above')
    sh.wire(nt.p('1'), (335.28, 132.08), (335.28, 137.16))
    gy((335.28, 137.16))
    sh.wire(nt.p('2'), (350.52, 132.08), (350.52, 137.16))
    gl((350.52, 137.16))
    sh.pwr('PWR_FLAG', (335.28, 132.08))
    sh.text('GND_24V: 24 V return (XT30 pin 2, relay outputs,\n'
            'sensor 0 V, TVS, bulk caps, DC/DC input side).\n'
            'GND: logic (module, INA226, ADS1232, DC/DC output).\n'
            '{NT}: the only joint between them (the INA226s\n'
            'measure +24V against GND). Place it at the DC/DC.', (314.96, 152.40))
    # ======== row 3: test points, bring-up
    sh.box(15.24, 187.96, 203.20, 248.92, 'Test points (bring-up)')
    tps = [('+24V', 'TP1'), ('+24V_DC', 'TP1'), ('+5V_24', 'TP2'), ('+5V', 'TP4'), ('+3V3_MOD', 'TP5'),
           ('GND', 'TP6'), ('GND_24V', 'TP7')]
    x = 30.48
    for net, old in tps:
        tp = fpart(sh, old, (x, 210.82), value=net, tag='TP_' + net, fields=((-1.27, -3.81), (-1.27, -1.27), 'right'))
        if net.startswith('GND'):
            sh.wire(tp.p('1'), (x, 215.90))
            sh.pwr(net, (x, 215.90))
        elif net == '+24V_DC':
            sh.wire(tp.p('1'), (x + 7.62, 210.82))
            sh.label('+24V_DC', (x + 7.62, 210.82))
        else:
            sh.wire(tp.p('1'), (x + 7.62, 210.82))
            sh.pwr(net, (x + 7.62, 210.82))
        x += 27.94
    sh.text('2 mm pads with a 1 mm hole: probe tip, or solder a wire loop for clips (not in the BOM).\n'
            'Clip the scope ground to GND for the module side and to GND_24V for the 24 V side.',
            (17.78, 236.22))
    sh.box(205.74, 187.96, 403.86, 248.92, 'First power-up')
    sh.text('1. No module fitted. Apply 24 V on {J_IN} from a current-limited supply: {LED24} lights;\n'
            '   +24V, +24V_DC, +5V_24 and +5V present ({Main/LED1} on).\n'
            '2. Reverse the lead briefly: nothing lights and +24V stays at 0 V ({Q_RP} blocks).\n'
            '3. Unplug 24 V, fit the module, plug in again: {Main/LED2} lights (module 3V3).\n'
            '   Then flash over STDC14 ({Main/J3}).', (208.28, 195.58))
    return sh


def add_expander(sh):
    """TCA9535 coil-feedback expander in the Relays 3-4 sheet's left column."""
    B.register_symbol(AP.tca9535_symbol())
    for it in sh.items:  # the template's left notes column ends above the expander
        if it[0] == 'rectangle' and float(first(it, 'start')[1]) == 15.24 and float(first(it, 'end')[2]) > 240:
            first(it, 'end')[2] = 138.43
    sh.box(15.24, 140.97, 106.68, 250.19, 'Coil feedback expander (I²C1 0x20)')
    u = npart(sh, 'U_EXP', 'U', (55.88, 190.50), fields=((-12.70, -27.94), (5.08, 27.94), 'left'))
    # supply + decoupling
    vdd = u.p('VDD')
    sh.wire(vdd, (vdd[0], vdd[1] - 2.54), (vdd[0], vdd[1] - 5.08))
    sh.pwr('+3V3_MOD', (vdd[0], vdd[1] - 5.08))
    c = fpart(sh, 'C4', (vdd[0] + 5.08, vdd[1] - 2.54), rot=90, tag='C_EXP', desc='TCA9535 VCC bypass')
    sh.wire((vdd[0], vdd[1] - 2.54), c.p('1'))
    sh.pwr('GND', c.p('2'), 90)
    sh.pwr('GND', u.p('VSS'))
    # address 0x20: A2 / A1 / A0 = GND
    xs = u.p('A0')[0] - 2.54
    for n in ('A0', 'A1', 'A2'):
        sh.wire(u.p(n), (xs, u.p(n)[1]))
    sh.wire((xs, u.p('A0')[1]), (xs, u.p('A1')[1]), (xs, u.p('A2')[1]), (xs, u.p('A2')[1] + 2.54))
    sh.pwr('GND', (xs, u.p('A2')[1] + 2.54))
    # I2C + INT
    for n, lab in (('SCL', 'I2C1_SCL'), ('SDA', 'I2C1_SDA')):
        sh.wire(u.p(n), (u.p(n)[0] - 7.62, u.p(n)[1]))
        sh.glabel(lab, (u.p(n)[0] - 7.62, u.p(n)[1]), 180)
    sh.nc(u.p('~{INT}'))  # PA0 now drives the winch: the expander is polled
    # inputs: relay coil feedback on P00-P03, the rest spare
    for k in range(4):
        pp = u.p('IO0_%d' % k)
        sh.wire(pp, (pp[0] + 7.62, pp[1]))
        sh.glabel('RLY%d_FB' % (k + 1), (pp[0] + 7.62, pp[1]), 0)
    for n in ['IO0_%d' % k for k in range(4, 8)] + ['IO1_%d' % k for k in range(8)]:
        sh.nc(u.p(n))
    sh.text('{U_EXP} TCA9535PWR: A2 / A1 / A0 = GND → I²C1 0x20 (no clash with\n'
            'the INA226s at 0x40-0x45). P00-P03 = relay 1-4 coil feedback\n'
            '(10k / 15k + 10 nF dividers, 3.0 V = coil off; inputs 5.5 V-tolerant).\n'
            'INT not connected: PA0 drives the winch, so poll the expander.\n'
            'P04-P17 spare (12 inputs for later): no internal pull-ups, so set\n'
            'them as outputs, LOW, at start-up. Read input port 0 (reg 0x00)\n'
            '≥ 30 ms after switching a relay (CIF §7b).', (17.78, 226.06))


# ---------------------------------------------------------------- root page: block diagram + sheets
RED, ORA, BLU, GRY = (200, 30, 30), (225, 115, 0), (30, 80, 200), (110, 110, 110)


def root_items(sh, sheets):
    it = sh.items

    def rect(x1, y1, x2, y2, col, fill):
        it.append(['rectangle', ['start', x1, y1], ['end', x2, y2],
                   ['stroke', ['width', 0.5], ['type', 'solid'], ['color'] + list(col) + [1]],
                   ['fill', ['type', 'color'], ['color'] + list(fill) + [1]], ['uuid', U('rr')]])

    def txt(s, x, y, size=1.8, bold=False, col=None):
        font = ['font', ['size', size, size]]
        if bold:
            font.append(['bold', 'yes'])
        if col:
            font.append(['color'] + list(col) + [1])
        it.append(['text', Q(s), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                   ['effects', font, ['justify', 'left', 'top']], ['uuid', U('rt')]])

    def line(pts, col, w=0.8):
        it.append(['polyline', ['pts'] + [['xy', x, y] for x, y in pts],
                   ['stroke', ['width', w], ['type', 'solid'], ['color'] + list(col) + [1]],
                   ['fill', ['type', 'none']], ['uuid', U('rl')]])

    def arrow(pts, col, both=False):
        line(pts, col)
        for (x0, y0), (x1, y1) in ([(pts[-2], pts[-1])] + ([(pts[1], pts[0])] if both else [])):
            dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
            px, py = -dy, dx
            tri = [(x1, y1), (x1 - 2.8 * dx + 1.1 * px, y1 - 2.8 * dy + 1.1 * py),
                   (x1 - 2.8 * dx - 1.1 * px, y1 - 2.8 * dy - 1.1 * py), (x1, y1)]
            it.append(['polyline', ['pts'] + [['xy', round(a, 2), round(b, 2)] for a, b in tri],
                       ['stroke', ['width', 0.1], ['type', 'solid'], ['color'] + list(col) + [1]],
                       ['fill', ['type', 'color'], ['color'] + list(col) + [1]], ['uuid', U('ra')]])

    def block(x1, y1, x2, y2, col, fill, title, body):
        rect(x1, y1, x2, y2, col, fill)
        txt(title, x1 + 2.54, y1 + 2.29, 2.2, True)
        txt(body, x1 + 2.54, y1 + 7.62)

    txt('How the MES4-Carrier-EC works', 17.78, 18.29, 4, True)
    for x, col, name in ((17.78, RED, '24 V'), (50.80, ORA, '5 V'), (83.82, BLU, 'signals and buses')):
        line([(x, 28.58), (x + 7.62, 28.58)], col)
        txt(name, x + 9.4, 27.43, 1.8, False, col)
    LP = (255, 238, 220)
    block(17.78, 40.64, 83.82, 66.04, RED, LP, '24 V DC in ({Power/J_IN}, XT30)',
          'XT30 → {Power/F_IN} {F_IN_VALUE} fuse → {Power/Q_RP} reverse-\n'
          'polarity P-FET → {Power/TVS} SMBJ30A TVS +\n{Power/C_BULK} 100 µF bulk → +24V rail.\n'
          '{Power/LED24} = 24 V present.')
    block(17.78, 76.20, 83.82, 101.60, ORA, LP, 'Filter + 24 V → 5 V ({Power/U_DCDC})',
          '{Power/L_DC} pi filter → URB2405S-6WR3\n(isolated, 1.2 A) → +5V_24:\nrelay coils and the module feed.')
    block(17.78, 111.76, 83.82, 132.08, ORA, LP, 'Module 5 V feed',
          '{Power/F_MOD} 1.1 A PTC + {Power/FB_5V} ferrite pi\n→ +5V: module fingers 20 / 22\nand the ADS1232 excitation.')
    block(17.78, 142.24, 83.82, 167.64, GRY, (238, 238, 238), 'ST-Link + reset ({Main/J3}, {Main/SW1})',
          'STDC14: SWD, NRST, VCP.\nSW1 pulls NRST low.\nH5VSD3B ESD on every pin.')
    block(17.78, 177.80, 83.82, 203.20, GRY, (238, 238, 238), 'CAN ({CAN/J_DB9} DB9, {CAN/J_RJ} RJ45 x4)',
          'DB9 male to the IPC (1 GND, 3 H, 5 L)\n+ 1x4 RJ45 (1 H, 2 L, 3 GND), one bus.\nH24VNT2B ESD at each, no series R.')
    block(106.68, 40.64, 182.88, 203.20, BLU, (222, 232, 252), 'MES4-MCU module ({Main/J1}, M.2 socket)',
          'STM32G0B1, 64 MHz, CAN transceiver.\n'
          'Gets +5V on fingers 20 / 22.\n'
          'Makes its own 3.3 V → +3V3_MOD\n(finger 4, ≤ 50 mA) for the I²C\n'
          'pull-ups, INA226s, PC817 outputs\nand the ADS1232 logic.\n\n'
          'All 14 GPIOs are used\n(GPIO map on the Main sheet).\n\n'
          '{Main/LED1} = module +5V, {Main/LED2} = 3V3.\n'
          'Hold-down: {Main/H5} M3 standoff.\n\n'
          'No hot-plug: unplug the XT30\nbefore fitting a module.')
    block(205.74, 40.64, 297.18, 106.68, RED, (222, 242, 222), '4 relay outputs (CIF §7)',
          '1 safety light: PA8 drive, PA0 FB, INA226 0x40\n'
          '2 LED DRL: PC6 drive, PA1 FB, 0x41\n'
          '3 battery stopper: PB3 drive, PA2 FB, 0x44\n'
          '4 spare: PA7 drive, PA3 FB, 0x45\n\n'
          'GPIO → 100 Ω → AO3400A → 5 V coil\n(SRD-5VDC-SL-A, on +5V_24).\n'
          '+24V → 30 mΩ shunt → contact →\n{F_CH_VALUE} PTC → output (2 A continuous).\n'
          'Coil feedback 10k / 15k → TCA9535 (I²C).\n'
          'INA226 per channel: load current +\n24 V rail, ALERT → PA15.')
    block(205.74, 116.84, 297.18, 147.32, RED, (222, 242, 222), '2 Autonics sensor inputs',
          '+24V → 100 mA PTC → sensor supply.\n'
          'Sensor OUT → 10k → PC817 → PB6 / PC15\n(HIGH = sensor ON). PNP 24 V sensors.')
    block(205.74, 157.48, 297.18, 203.20, BLU, (238, 228, 250), 'Load cell ({LoadCell/lc:U13} ADS1232)',
          '4-wire bridge, excited from +5V\n(ratiometric, as on the MES4-Flasher).\n'
          '100 Ω / 100 nF / 10 nF filters,\nBAV199 clamps. 24 bit, gain 128,\n10 SPS.\n'
          'DRDY PA4, SCLK PA5, PDWN PA6.')
    # arrows
    arrow([(50.80, 66.04), (50.80, 76.20)], RED)
    txt('+24V', 52.07, 67.82, 1.6, False, RED)
    arrow([(50.80, 101.60), (50.80, 111.76)], ORA)
    txt('+5V_24', 52.07, 103.38, 1.6, False, ORA)
    arrow([(83.82, 121.92), (95.25, 121.92), (95.25, 60.96), (106.68, 60.96)], ORA)
    txt('+5V', 86.36, 118.11, 1.6, False, ORA)
    line([(50.80, 40.64), (50.80, 33.02), (302.26, 33.02), (302.26, 132.08)], RED)
    arrow([(302.26, 55.88), (297.18, 55.88)], RED)
    arrow([(302.26, 132.08), (297.18, 132.08)], RED)
    txt('+24V rail: relay contacts, INA226 VBUS and sensor supplies', 120.65, 29.21, 1.6, False, RED)
    block(309.88, 142.24, 403.86, 190.50, ORA, LP, 'IMU 9 V + screen 5 V (page 9)',
          'Own L pi filter from +24V.\n'
          '{AuxPower/U_IMU} URB2409S-10WR3 → 9 V →\n{AuxPower/SW_IMU} switch → {AuxPower/J_IMU} IMU terminal\n(as on the MES3.1 carrier).\n'
          '{AuxPower/U_SCR} URB2405LD-20WR3 → 5 V 4 A\n→ 3 A PTC → {AuxPower/J_USB} USB-C (Rp 10k:\n5 V / 3 A) → ARZOPA Z1C screen.\n'
          'Door servo (FE-URT-2): {AuxPower/J_SRVP} 24 V\n+ {AuxPower/J_SRVU} UART via the I²C bridge.')
    line([(302.26, 132.08), (302.26, 157.48)], RED)
    block(309.88, 40.64, 403.86, 96.52, GRY, (238, 238, 238), 'Winch control (page 10)',
          'Two IM03GR relays, as on the\nMES2_Extension: PA0 → CLK,\nPA1 → ACLK (AO3400A drivers).\n'
          'Contacts switch the 48 V winch\ncontroller\'s direction inputs.\n'
          'Hardware interlock: both on =\nboth open.')
    arrow([(302.26, 157.48), (309.88, 157.48)], RED)
    arrow([(83.82, 154.94), (106.68, 154.94)], BLU, both=True)
    txt('SWD, NRST,\nVCP', 86.36, 147.32, 1.6, False, BLU)
    arrow([(83.82, 190.50), (106.68, 190.50)], BLU, both=True)
    txt('CAN', 86.36, 186.69, 1.6, False, BLU)
    arrow([(182.88, 63.50), (205.74, 63.50)], BLU)
    txt('PA8 / PC6 /\nPB3 / PA7', 185.42, 56.52, 1.6, False, BLU)
    arrow([(205.74, 81.28), (182.88, 81.28)], BLU)
    txt('coil FB (I²C)', 185.42, 77.47, 1.6, False, BLU)
    arrow([(182.88, 96.52), (205.74, 96.52)], BLU, both=True)
    txt('I²C1 + PA15', 185.42, 92.71, 1.6, False, BLU)
    arrow([(205.74, 132.08), (182.88, 132.08)], BLU)
    txt('PB6 / PC15', 185.42, 128.27, 1.6, False, BLU)
    arrow([(182.88, 180.34), (205.74, 180.34)], BLU, both=True)
    txt('PA4-PA6', 185.42, 176.53, 1.6, False, BLU)
    # GPIO budget + notes
    rect(17.78, 213.36, 248.92, 248.92, (60, 60, 60), (250, 250, 250))
    txt('Notes', 20.32, 215.65, 2.2, True)
    txt('E-Crawler carrier for one MES4-MCU module (MES4-CIF rev A-d6). Circuits taken from the MES4-Flasher: PC817 sensor inputs,\n'
        'ADS1232 load cell, relay channels (driver, coil feedback, INA226) and the XT30 / URB2405S 24 V input.\n'
        'GPIO budget: 4 relay drives + ALERT + 3 ADS1232 + 2 sensors + winch (2) = 12; PA2 / PA3 free (servo on the I²C bridge).\n'
        'Relay coil feedback goes through a TCA9535 I²C expander (MES4-CIF §7c).\n'
        'Relay drive per CIF §7a (AO3400A, 100 Ω, 100k pull-down); the Flasher uses a 2SC2884 BJT for the same job.\n'
        'No hot-plug: unplug the 24 V XT30 before inserting or removing the module.\n'
        'Pages: Main (2), CAN (3), Power (4), Relays 1-2 (5), Relays 3-4 (6), Sensors (7), LoadCell (8), AuxPower (9), Winch (10).', 20.32, 221.0)
    it.append(['rectangle', ['start', 254.00, 208.28], ['end', 403.86, 248.92],
               ['stroke', ['width', 0.35], ['type', 'dash'], ['color', 30, 30, 160, 1]],
               ['fill', ['type', 'none']], ['uuid', U('rp')]])
    txt('Pages', 256.54, 210.57, 2, True)


def sheet_symbol(sh, x, y, root_uuid, w=38.10, h=7.62):
    return ['sheet', ['at', x, y], ['size', w, h], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
            ['on_board', 'yes'], ['dnp', 'no'],
            ['stroke', ['width', 0.35], ['type', 'solid'], ['color', 200, 110, 0, 1]],
            ['fill', ['color', 255, 240, 220, 1.0]], ['uuid', sh.uuid],
            ['property', Q('Sheetname'), Q(sh.name), ['at', x, y - 0.71, 0],
             ['effects', ['font', ['size', 2, 2], ['thickness', 0.4], ['bold', 'yes']], ['justify', 'left', 'bottom']]],
            ['property', Q('Sheetfile'), Q(sh.file), ['at', x, y + h + 0.76, 0],
             ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]],
            ['instances', ['project', Q(B.PROJECT), ['path', Q('/' + root_uuid), ['page', Q(str(sh.page))]]]]]


# ---------------------------------------------------------------- write everything
def main():
    sheets = [main_sheet(), can_sheet(), power_sheet(),
              relay_sheet('Relays1-2', 'Relays12.kicad_sch', 5, [1, 2],
                          'Sheet 5: relay outputs 1-2 (safety light, LED DRL) with coil and load-current feedback'),
              relay_sheet('Relays3-4', 'Relays34.kicad_sch', 6, [3, 4],
                          'Sheet 6: relay outputs 3-4 (battery stopper, spare) with coil and load-current feedback'),
              sensor_sheet(), loadcell_sheet(), aux_sheet(), winch_sheet()]
    S = {s.name: s for s in sheets}
    S['Relays1-2'].box(15.24, 20.32, 106.68, 250.19)
    S['Relays1-2'].text(RELAY_DIAG[0], (17.78, 22.86), size=2, bold=True)
    S['Relays1-2'].text(RELAY_DIAG[1].replace('U? DC/DC', '{Power/U_DCDC} DC/DC'), (17.78, 27.94))
    S['Relays3-4'].text(RELAY_LOADS[0], (17.78, 22.86), size=2, bold=True)
    S['Relays3-4'].text(RELAY_LOADS[1].replace('U? URB2405S', '{Power/U_DCDC} URB2405S'), (17.78, 27.94))
    add_expander(S['Relays3-4'])
    for s in sheets:
        s.clean()
    B.assign_refs(sheets)
    tagmap = {}
    for s in sheets:
        for p in s.parts:
            if p.tag:
                tagmap[(s.name, p.tag[4:] if p.tag.startswith('old:') else p.tag)] = p.ref
    consts = {'F_CH_VALUE': NEWP['F_CH']['value'], 'F_IN_VALUE': NEWP['F_IN']['value']}

    def resolve(sh, s):
        def rep(m):
            k = m.group(1)
            if k in consts:
                return consts[k]
            sn, t = k.split('/', 1) if '/' in k else (sh.name, k)
            if (sn, t) not in tagmap:
                raise KeyError('unresolved tag %s on %s' % (k, sh.name))
            return tagmap[(sn, t)]
        return re.sub(r'\{([^{}]+)\}', rep, s)

    root_uuid = U('root')
    os.makedirs(OUT, exist_ok=True)
    for s in sheets:
        open(OUT + s.file, 'w').write(dump(s.node(root_uuid, TITLE, DATE, REV, COMPANY, AUTHOR, resolve)) + '\n')
    # root
    rs = Sheet('Root', 'MES4_Carrier_EC.kicad_sch',
               'E-Crawler carrier for the MES4-MCU M.2 module', 1)
    root_items(rs, sheets)
    for it in rs.items:
        if it[0] == 'text':
            it[1] = Q(resolve(rs, it[1]))
    root = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')], ['generator_version', Q('9.0')],
            ['uuid', root_uuid], ['paper', Q('A3')],
            ['title_block', ['title', Q(TITLE)], ['date', Q(DATE)], ['rev', Q(REV)], ['company', Q(COMPANY)],
             ['comment', 1, Q(AUTHOR)], ['comment', 2, Q(rs.comment)]],
            ['lib_symbols']] + rs.items
    pos = [(256.54 + 29.21 * (i % 5), 219.71 + 16.51 * (i // 5)) for i in range(len(sheets))]
    for s, (x, y) in zip(sheets, pos):
        root.append(sheet_symbol(s, x, y, root_uuid, w=26.67))
    root.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    root.append(['embedded_fonts', 'no'])
    open(OUT + 'MES4_Carrier_EC.kicad_sch', 'w').write(dump(root) + '\n')
    # project file
    pro = json.load(open(FL + 'MES4-Flasher.kicad_pro'))
    pro['meta']['filename'] = 'MES4_Carrier_EC.kicad_pro'
    pro['sheets'] = [[str(root_uuid), 'Root']] + [[str(s.uuid), s.name] for s in sheets]
    ns = pro['net_settings']
    for c in ns['classes']:
        if c['name'] == 'Out_1A5':
            c['name'] = 'Out_2A'
            c['track_width'] = 1.0
    ns['netclass_patterns'] = (
        [{'netclass': 'Power', 'pattern': p} for p in ('+5V', '+5V_24', '+3V3_MOD', 'GND')] +
        [{'netclass': '24V_Power', 'pattern': p} for p in ('+24V', 'GND_24V', '/Power/+24V_IN', '/Power/+24V_F')] +
        [{'netclass': 'Power', 'pattern': '/Power/+24V_DC'}] +
        [{'netclass': 'Out_2A', 'pattern': p} for p in ('/Relays*/RLY*_OUT', 'Net-(U*-Vin-)', 'Net-(F*-Pad1)')])
    pro.get('pcbnew', {}).pop('last_paths', None)
    json.dump(pro, open(OUT + 'MES4_Carrier_EC.kicad_pro', 'w'), indent=2)
    return sheets


if __name__ == '__main__':
    main()
    print('written')
