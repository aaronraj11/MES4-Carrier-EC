"""Build sim/report.html (inline SVG plots) from the LTspice .raw files. Run run_sims.py first."""
import html, os
from run_sims import read_raw, HERE

COL = ['#185FA5', '#D85A30', '#1D9E75', '#993556']


def plot(name, sigs, t0, t1, title, unit, scale=1.0, limits=()):
    d = read_raw(name)
    t = d['time']
    W, H, L, R, T, B = 640, 260, 56, 16, 28, 36
    series = []
    lo, hi = float('inf'), float('-inf')
    for s in sigs:
        y = d[s]
        pts = [(x, v * scale) for x, v in zip(t, y) if t0 <= x <= t1]
        n = max(1, len(pts) // 350)  # keep min / max per bucket so peaks survive
        red = []
        for k in range(0, len(pts), n):
            b = pts[k:k + n]
            red += [min(b, key=lambda p: p[1]), max(b, key=lambda p: p[1])] if n > 1 else b
        red.sort()
        series.append((s, red))
        lo, hi = min(lo, min(p[1] for p in red)), max(hi, max(p[1] for p in red))
    for v, _ in limits:
        lo, hi = min(lo, v), max(hi, v)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    X = lambda x: L + (x - t0) / (t1 - t0) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    out = ['<svg viewBox="0 0 %d %d" width="100%%" role="img"><title>%s</title>' % (W, H, html.escape(title))]
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="ax" text-anchor="end">%.3g</text>'
                   % (L, W - R, Y(v), Y(v), L - 6, Y(v) + 4, v))
    for k in range(6):
        x = t0 + (t1 - t0) * k / 5
        lab = '%.3g ms' % (x * 1e3) if t1 >= 1e-3 else '%.3g µs' % (x * 1e6)
        out.append('<text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>' % (X(x), H - B + 16, lab))
    for v, lab in limits:
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="lim"/><text x="%d" y="%.1f" class="limt" text-anchor="end">%s</text>'
                   % (L, W - R, Y(v), Y(v), W - R - 4, Y(v) - 4, html.escape(lab)))
    for i, (s, red) in enumerate(series):
        pts = ' '.join('%.1f,%.1f' % (X(x), Y(v)) for x, v in red)
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.4"/>' % (pts, COL[i % 4]))
        out.append('<rect x="%d" y="8" width="10" height="3" fill="%s"/><text x="%d" y="13" class="lg">%s</text>'
                   % (L + i * 150, COL[i % 4], L + 14 + i * 150, html.escape(s)))
    out.append('<text x="12" y="%d" class="ax">%s</text></svg>' % (T - 6, unit))
    return '<figure><figcaption>%s</figcaption>%s</figure>' % (html.escape(title), ''.join(out))


def plot_ac(name, sigs, title):
    import math
    d = read_raw(name)
    f = d['frequency']
    W, H, L, R, T, B = 640, 260, 56, 16, 28, 36
    lf0, lf1 = math.log10(f[0]), math.log10(f[-1])
    def trace(s):  # 'V(a,b)' = V(a) - V(b), complex
        a, b = s[2:-1].split(',') if ',' in s else (s[2:-1], None)
        return [x - (d['V(%s)' % b][k] if b else 0) for k, x in enumerate(d['V(%s)' % a])]
    ser = [(s, [20 * math.log10(max(abs(v), 1e-12)) for v in trace(s)]) for s in sigs]
    lo = min(min(v) for _, v in ser); hi = max(max(v) for _, v in ser)
    lo, hi = math.floor(lo / 20) * 20, max(10, math.ceil(hi / 20) * 20)
    X = lambda x: L + (math.log10(x) - lf0) / (lf1 - lf0) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    out = ['<svg viewBox="0 0 %d %d" width="100%%" role="img"><title>%s</title>' % (W, H, html.escape(title))]
    for v in range(int(lo), int(hi) + 1, 20):
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="ax" text-anchor="end">%d</text>'
                   % (L, W - R, Y(v), Y(v), L - 6, Y(v) + 4, v))
    for e in range(int(lf0), int(lf1) + 1):
        x = 10 ** e
        lab = ('%g Hz' % x) if x < 1e3 else ('%g kHz' % (x / 1e3)) if x < 1e6 else ('%g MHz' % (x / 1e6))
        out.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="grid"/><text x="%.1f" y="%d" class="ax" text-anchor="middle">%s</text>'
                   % (X(x), X(x), T, H - B, X(x), H - B + 16, lab))
    for i, (s, v) in enumerate(ser):
        pts = ' '.join('%.1f,%.1f' % (X(x), Y(y)) for x, y in zip(f, v))
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.4"/>' % (pts, COL[i % 4]))
        out.append('<rect x="%d" y="8" width="10" height="3" fill="%s"/><text x="%d" y="13" class="lg">%s</text>'
                   % (L + i * 260, COL[i % 4], L + 14 + i * 260, html.escape(s)))
    out.append('<text x="12" y="%d" class="ax">dB</text></svg>' % (T - 6))
    return '<figure><figcaption>%s</figcaption>%s</figure>' % (html.escape(title), ''.join(out))


if __name__ == '__main__':
    V36, V50 = (36, 'converter max input 36 V'), (50, 'INA236 / 50 V ceramics')
    figs = {
        'pwr1v': plot('pwr1_hotplug', ['V(v24)', 'V(vdc)', 'V(vaux)'], 0, 2e-3, 'PWR1 · bus voltages after the XT30 closes', 'V', limits=[V36, V50]),
        'pwr1i': plot('pwr1_hotplug', ['I(Lcab)', 'I(L1)', 'I(L2)'], 0.09e-3, 0.3e-3, 'PWR1 · inrush (cable, L1, L2)', 'A', limits=[(2.9, 'L1 / L2 saturation 2.9 A')]),
        'pwr2': plot('pwr2_tvs_pulse', ['V(v24)', 'V(vaux)', 'I(D9)'], 0, 3e-3, 'PWR2 · 12.4 A 10/1000 µs pulse (I(D9) negative = clamping, in A)', 'V / A', limits=[V36, V50]),
        'pwr3': plot('pwr3_iec_surge', ['V(v24)', 'V(vaux)'], 0.05e-3, 0.4e-3, 'PWR3 · IEC 61000-4-5 0.5 kV, 2 Ω', 'V', limits=[V50, V36]),
        'pwr6': plot('pwr6_changeover', ['V(v24)', 'V(vdc)', 'V(vaux)'], 0, 20e-3, 'PWR6 · DDR stops at 2 ms (pack takes over via the AB20), pack cut at 12 ms', 'V', limits=[(9, 'converter UVLO ≈ 9 V')]),
        'pwr5': plot('pwr5_5v_rail', ['V(v5_24)', 'V(v5)'], 1e-3, 14e-3, 'PWR5 · +5V_24 and module +5V (240 mA module step at 2 ms, coils on at 5 ms)', 'V', limits=[(4.75, 'module min 4.75 V')]),
        'rly1v': plot('rly1_coil_driver', ['V(d)', 'V(g)'], 0, 20e-3, 'RLY1 · coil driver: Q2 drain and gate', 'V', limits=[(30, 'AO3400A 30 V')]),
        'rly1i': plot('rly1_coil_driver', ['I(Lk)'], 0, 20e-3, 'RLY1 · coil current', 'A'),
        'rly2': plot('rly2_solenoid_off', ['V(out)', 'I(Lsol)'], 3e-3, 15e-3, 'RLY2 · solenoid output when K3 opens (V, A)', 'V / A', limits=[(-0.3, 'INA236 input min −0.3 V')]),
        'wch1': plot('wch1_coil_driver', ['V(d)', 'I(Lk)'], 0, 10e-3, 'WCH1 · IM03GR driver: Q6 drain (V) and coil current (A)', 'V / A'),
        'sns1': plot('sns1_pc817', ['V(pb)'], 0, 2.5e-3, 'SNS1 · PB6 with a 20 V sensor and a CTR 50 % PC817', 'V', limits=[(0.99, 'STM32 VIL 0.99 V'), (2.31, 'STM32 VIH 2.31 V')]),
        'lc1': plot_ac('lc1_input_filter', ['V(ainp,ainn)', 'V(ainp2,ainn2)'], 'LC1 · differential response (blue) and common-mode to differential conversion (orange)'),
        'aux1i': plot('aux1_u10_startup', ['I(L2)', 'I(Rf11)'], 0, 8e-3, 'AUX1 · U10 start-up: L2 and F11 current', 'A', limits=[(2.9, 'L2 saturation 2.9 A'), (3.0, 'F11 hold 3 A')]),
        'aux1v': plot('aux1_u10_startup', ['V(vaux)', 'V(scr)'], 0, 8e-3, 'AUX1 · +24V_AUX and +5V_SCR', 'V'),
        'aux2': plot('aux2_servo_step', ['V(v24)', 'V(vsrv)', 'V(vaux)'], 0, 10e-3, 'AUX2 · 3 A servo stall step from 1 to 6 ms', 'V'),
        'aux3': plot('aux3_servo_uart', ['V(fe4)', 'V(pa3)'], 0, 6e-6, 'AUX3 · servo UART at 1 Mbit/s: FE-URT-2 input (TX) and PA3 (RX)', 'V', limits=[(0.99, 'VIL'), (2.31, 'VIH')]),
        'imu1v': plot('imu1_devkit_switch_on', ['V(imu)', 'V(vaux)'], 0.98e-3, 1.1e-3, 'IMU1 · J14 and the dev board Vaux when SW2 closes', 'V', limits=[(28, 'Vaux max 28 V'), (5.2, 'Vaux min 5.2 V')]),
        'imu1i': plot('imu1_devkit_switch_on', ['I(Lcab)'], 0, 6e-3, 'IMU1 · J14 current (inrush, then buck soft-start, then steady)', 'A', limits=[(0.5, 'SW2 rating 0.5 A')]),
        'main1': plot('main1_i2c', ['V(scl)', 'V(alert)'], 0, 10e-6, 'MAIN1 · I²C1 SCL at 400 kHz (2.2k, 60 pF) and ALERT (10k, 40 pF)', 'V', limits=[(0.99, '0.3 × VDD'), (2.31, '0.7 × VDD')]),
    }
    tpl = open(os.path.join(HERE, 'report_template.html')).read()
    for k, v in figs.items():
        tpl = tpl.replace('{{%s}}' % k, v)
    open(os.path.join(HERE, 'report.html'), 'w').write(tpl)
    print('written report.html')
