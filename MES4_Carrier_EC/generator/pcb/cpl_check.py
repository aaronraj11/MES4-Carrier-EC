"""JLC placement check: every part in the production CPL against JLC's own footprint for its LCSC part.

    cpl_check.py <pcb> <schematic> <positions.csv>

JLC places each part from its EasyEDA footprint at the CPL's Mid X / Mid Y, turned by the CPL's Rotation (counter-
clockwise, seen from the top, y up). For every placed part this fetches that footprint (EasyEDA's API answers a plain
curl user agent; cached in $TMPDIR/jlc_easyeda), matches its pads to ours (by pin name where both symbols name a
polarity, K / A or + / -, else by pad number), fits the rotation and offset that put JLC's pads on ours, and compares
them with the CPL. A two-pad part with no polarity may be off by 180 deg. EasyEDA units are 10 mil, y down."""
import sys, os, re, csv, json, math, time, shutil, subprocess, tempfile, xml.etree.ElementTree as ET, pcbnew

P, SCH, CPL = sys.argv[1:4]; T = pcbnew.ToMM
CLI = shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
CACHE = os.path.join(tempfile.gettempdir(), 'jlc_easyeda'); os.makedirs(CACHE, exist_ok=True)
POL = {'K': 'K', 'C': 'K', 'CATHODE': 'K', '-': 'K', 'NEG': 'K', 'A': 'A', 'ANODE': 'A', '+': 'A', 'POS': 'A'}


def easyeda(lcsc):
    f = os.path.join(CACHE, lcsc + '.json')
    for k in range(5):                                      # the API throttles bursts (HTML 403): back off and retry
        if not os.path.exists(f):
            subprocess.run(['curl', '-s', '-m', '20', '-A', 'curl/8.4.0', '-o', f,
                            f'https://easyeda.com/api/products/{lcsc}/components?version=6.4.19.5'])
            time.sleep(1.0)
        try:
            r = json.load(open(f)).get('result') or {}; break
        except ValueError:
            os.remove(f); time.sleep(5 * (k + 1))
    else:
        return None
    pk = (r.get('packageDetail') or {}).get('dataStr') or {}
    if not pk: return None
    hx, hy = float(pk['head']['x']), float(pk['head']['y'])
    pads = {}
    for s in pk.get('shape', []):
        if s.startswith('PAD~'):
            a = s.split('~'); pads.setdefault(a[8], []).append(((float(a[2]) - hx) * 0.254, -(float(a[3]) - hy) * 0.254))
    names = {}
    for sub in [r.get('dataStr') or {}] + [(p.get('dataStr') or {}) for p in r.get('subparts') or []]:
        for s in sub.get('shape', []):
            if s.startswith('P~'):
                g = s.split('^^')
                if len(g) > 4: names[g[4].split('~')[4]] = g[3].split('~')[4].strip().upper()
    return dict(pkg=r['packageDetail'].get('title'), pads=pads, names=names)


tmp = tempfile.mktemp(suffix='.xml')
subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', tmp, SCH], capture_output=True)
root = ET.parse(tmp).getroot(); os.remove(tmp)
libpins = {(lp.get('lib'), lp.get('part')): {p.get('num'): (p.get('name') or '').upper() for p in lp.iter('pin')}
           for lp in root.find('libparts')}
ourpins = {c.get('ref'): libpins.get((c.find('libsource').get('lib'), c.find('libsource').get('part')), {})
           for c in root.find('components')}

b = pcbnew.LoadBoard(P)
rows = list(csv.DictReader(open(CPL, encoding='utf-8-sig')))
bad, nofp, ok = [], [], 0
for r in rows:
    ref = r['Designator']; f = b.FindFootprintByReference(ref); lcsc = f.GetFieldText('LCSC') if f.HasFieldByName('LCSC') else ''
    j = easyeda(lcsc) if lcsc else None
    if not j or not j['pads']:
        nofp.append(f'{ref} ({lcsc or "no LCSC"}, {f.GetFPIDAsString().split(":")[-1]})'); continue
    ours = {}
    for p in f.Pads():
        if p.GetNumber(): ours.setdefault(p.GetNumber(), []).append((T(p.GetPosition().x), -T(p.GetPosition().y)))
    # pad correspondence: by polarity name when both sides name it, else by number (unique pads only)
    on = {n: POL.get(ourpins.get(ref, {}).get(n, ''), '') for n in ours}
    jn = {n: POL.get(j['names'].get(n, ''), '') for n in j['pads']}
    pairs, how = [], 'number'
    if len(ours) == 2 and all(on.values()) and sorted(on.values()) == sorted(v for v in jn.values() if v) == ['A', 'K']:
        inv = {v: n for n, v in jn.items() if v}
        pairs = [(j['pads'][inv[on[n]]][0], ours[n][0]) for n in ours]
        how = 'name' if any(inv[on[n]] != n for n in ours) else 'number'
    else:
        pairs = [(j['pads'][n][0], ours[n][0]) for n in ours if n in j['pads'] and len(ours[n]) == 1 and len(j['pads'][n]) == 1]
    def fit(pairs):
        mq = [sum(q[i] for q, _ in pairs) / len(pairs) for i in (0, 1)]; mp = [sum(p[i] for _, p in pairs) / len(pairs) for i in (0, 1)]
        sx = sum((q[0] - mq[0]) * (p[1] - mp[1]) - (q[1] - mq[1]) * (p[0] - mp[0]) for q, p in pairs)
        sc = sum((q[0] - mq[0]) * (p[0] - mp[0]) + (q[1] - mq[1]) * (p[1] - mp[1]) for q, p in pairs)
        a = math.atan2(sx, sc); ca, sa = math.cos(a), math.sin(a)
        tx, ty = mp[0] - (ca * mq[0] - sa * mq[1]), mp[1] - (sa * mq[0] + ca * mq[1])
        rms = math.sqrt(sum((ca * q[0] - sa * q[1] + tx - p[0]) ** 2 + (sa * q[0] + ca * q[1] + ty - p[1]) ** 2 for q, p in pairs) / len(pairs))
        return a, tx, ty, rms
    allq = [q for v in j['pads'].values() for q in v]; allp = [p for v in ours.values() for p in v]
    if (len(pairs) < 2 or fit(pairs)[3] > 0.3) and len(allq) == len(allp) and len(allp) >= 2:
        best = None                                         # numbering differs: match the pad patterns as shapes
        for deg in range(0, 360, 90):
            ca, sa = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            rq = [(ca * x - sa * y, sa * x + ca * y) for x, y in allq]
            cq = [sum(v[i] for v in rq) / len(rq) for i in (0, 1)]; cp = [sum(v[i] for v in allp) / len(allp) for i in (0, 1)]
            pr = [(allq[min(range(len(rq)), key=lambda k: math.hypot(rq[k][0] - cq[0] + cp[0] - p[0], rq[k][1] - cq[1] + cp[1] - p[1]))], p) for p in allp]
            if len({id(q) for q, _ in pr}) == len(pr) and (best is None or fit(pr)[3] < best[1][3]): best = (pr, fit(pr))
        if best and best[1][3] < 0.3: pairs, how = best[0], 'shape'
    if len(pairs) < 2:
        nofp.append(f'{ref} (pads don\'t match JLC\'s {j["pkg"]})'); continue
    a, tx, ty, rms = fit(pairs)
    need = math.degrees(a) % 360; cpl = float(r['Rotation']) % 360
    d = (cpl - need + 180) % 360 - 180
    polar = how == 'name' or any(on.values()) or len(ours) > 2
    off = math.hypot(float(r['Mid X']) - tx, float(r['Mid Y']) - ty)
    note = []
    if abs(d) > 2 and not (not polar and abs(abs(d) - 180) < 2): note.append(f'ROTATION: CPL {cpl:g}, JLC needs {need:.0f} (off {d:+.0f})')
    if rms > 0.3: note.append(f'pads fit badly (rms {rms:.2f} mm): JLC footprint {j["pkg"]} differs')
    if off > 0.3: note.append(f'position {off:.2f} mm from JLC\'s origin')
    anc = math.hypot(T(f.GetPosition().x) - tx, -T(f.GetPosition().y) - ty)
    if note: bad.append(f'{ref:5} {f.GetFPIDAsString().split(":")[-1][:34]:34} {lcsc:10} {j["pkg"][:30]:30} ' + '; '.join(note)
                        + (f' [matched by {how}]' if how != 'number' else '') + f' [JLC origin {anc:.2f} mm from our anchor; JLC pos {tx:.2f}, {ty:.2f}]')
    else: ok += 1
print(f'CPL parts {len(rows)}: {ok} match JLC\'s footprints, {len(bad)} to fix, {len(nofp)} with no JLC footprint to check')
for x in bad: print('  ' + x)
for x in nofp: print('  no footprint: ' + x)
