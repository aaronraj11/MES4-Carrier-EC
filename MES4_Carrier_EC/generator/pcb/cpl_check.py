"""JLC placement check, a gate (exits 1 on any problem): every part in the production CPL placed the way JLC
places it, from its EasyEDA footprint for the LCSC part at the CPL's Mid X / Mid Y, turned by the CPL's Rotation
(counter-clockwise, seen from the top, y up), and compared with our pads.

    cpl_check.py <pcb> <schematic> <positions.csv>

Every JLC pad has to land on one of our pads (its centre on our pad's copper within 0.6 mm of our pad's centre, or
within 0.3 mm of it: NPTH pegs too), and no two pins on the same pad. Where the pads also fit at another turn, pin n
has to land on our pin n (by pin name where both symbols name a polarity, K / A or + / -; pins only one side numbers,
such as pegs, shields and lugs, aren't compared): only a two-pad part with no polarity (NONPOLAR: R, C, L, fuses,
bidirectional TVS) may sit 180 deg round. Where they fit one way only, JLC's pin numbers are its own (the SRD relays,
the XT30) and are listed as notes. The old version fitted JLC's pads onto ours, let a 180 deg turn through on every
two-pad part whose symbol names no polarity, so all seven electrolytics passed reversed (review R4 E1), and left J5's
pegs out (E2). A failing part gets the CPL rotation and position that would put JLC's pads on ours, where one of the
other three turns does. Footprints come from EasyEDA's API (it answers a plain curl user agent; cached in
$TMPDIR/jlc_easyeda); EasyEDA units are 10 mil, y down."""
import sys, os, csv, json, math, time, shutil, subprocess, tempfile, xml.etree.ElementTree as ET, pcbnew

P, SCH, CPL = sys.argv[1:4]; T = pcbnew.ToMM
CLI = shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
CACHE = os.path.join(tempfile.gettempdir(), 'jlc_easyeda'); os.makedirs(CACHE, exist_ok=True)
POL = {'K': 'K', 'C': 'K', 'CATHODE': 'K', '-': 'K', 'NEG': 'K', 'A': 'A', 'ANODE': 'A', '+': 'A', 'POS': 'A'}
NONPOLAR = {'R', 'C', 'L', 'FerriteBead', 'Fuse', 'Polyfuse', 'D_TVS'}
num = lambda n: n.lstrip('0') or n                         # JLC's "09" is our "9"


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
    pads = []
    for s in pk.get('shape', []):
        if s.startswith('PAD~'):
            a = s.split('~'); pads.append((num(a[8]), (float(a[2]) - hx) * 0.254, -(float(a[3]) - hy) * 0.254))
    names = {}
    for sub in [r.get('dataStr') or {}] + [(p.get('dataStr') or {}) for p in r.get('subparts') or []]:
        for s in sub.get('shape', []):
            if s.startswith('P~'):
                g = s.split('^^')
                if len(g) > 4: names[num(g[4].split('~')[4])] = g[3].split('~')[4].strip().upper()
    return dict(pkg=r['packageDetail'].get('title'), pads=pads, names=names)


tmp = tempfile.mktemp(suffix='.xml')
subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', tmp, SCH], capture_output=True)
root = ET.parse(tmp).getroot(); os.remove(tmp)
libpins = {(lp.get('lib'), lp.get('part')): {p.get('num'): (p.get('name') or '').upper() for p in lp.iter('pin')}
           for lp in root.find('libparts')}
sym = {c.get('ref'): (c.find('libsource').get('lib'), c.find('libsource').get('part')) for c in root.find('components')}

b = pcbnew.LoadBoard(P)
AX, AY = (T(v) for v in b.GetDesignSettings().GetAuxOrigin())
rows = list(csv.DictReader(open(CPL, encoding='utf-8-sig')))
bad, nofp, notes, ok = [], [], [], 0
for r in rows:
    ref = r['Designator']; f = b.FindFootprintByReference(ref); lcsc = f.GetFieldText('LCSC') if f.HasFieldByName('LCSC') else ''
    j = easyeda(lcsc) if lcsc else None
    if not j or not j['pads']:
        nofp.append(f'{ref} ({lcsc or "no LCSC"}, {f.GetFPIDAsString().split(":")[-1]})'); continue
    ours = [(num(p.GetNumber()) if p.GetNumber() else '', p, T(p.GetPosition().x) - AX, AY - T(p.GetPosition().y))
            for p in f.Pads()]                              # CPL frame
    # the pin JLC's pad n has to land on: by polarity name where both symbols name one (2-pad parts), else n
    on = {num(n): POL.get(nm, '') for n, nm in libpins.get(sym.get(ref), {}).items()}
    jn = {n: POL.get(j['names'].get(n, ''), '') for n, *_ in j['pads']}
    want = {}
    if len(on) == 2 and sorted(on.values()) == sorted(v for v in jn.values() if v) == ['A', 'K']:
        want = {n: next(m for m, v in on.items() if v == jn[n]) for n in jn if jn[n]}
    both = {o[0] for o in ours} & set(jn)
    nonpolar = sym.get(ref, ('', ''))[1] in NONPOLAR and len({o[0] for o in ours if o[0]}) == 2

    def land(rot, mx, my, numbers=True):
        """JLC's footprint at (mx, my) turned rot: the problems, [] if it sits on our pads."""
        ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot)); used, out = {}, []
        for n, qx, qy in j['pads']:
            x, y = mx + ca * qx - sa * qy, my + sa * qx + ca * qy
            pt = pcbnew.VECTOR2I(pcbnew.FromMM(AX + x), pcbnew.FromMM(AY - y))
            m, p, px, py = min(ours, key=lambda o: math.hypot(x - o[2], y - o[3])); d = math.hypot(x - px, y - py)
            if not (d <= 0.3 or (d <= 0.6 and p.HitTest(pt))):
                out.append(f'pad {n} off our pads ({d:.2f} mm from {m or "NPTH"})'); continue
            if used.get(id(p), n) != n: out.append(f'pads {used[id(p)]} and {n} both on our {m or "NPTH"}')
            used[id(p)] = n
            if numbers and n in both and m in both and m != want.get(n, n) and not nonpolar: out.append(f'pin {n} on our pin {m}, not {want.get(n, n)}')
        return out

    mx, my, rot = float(r['Mid X']), float(r['Mid Y']), float(r['Rotation'])
    err = land(rot, mx, my)
    if not err: ok += 1; continue

    def turns(numbers=True):
        """The other turns that land JLC's pads on ours: at the CPL point or with JLC's pad centroid on ours."""
        for k in (90, 180, 270):
            rr = (rot + k) % 360; ca, sa = math.cos(math.radians(rr)), math.sin(math.radians(rr)); q = j['pads']
            jc = (sum(ca * a[1] - sa * a[2] for a in q) / len(q), sum(sa * a[1] + ca * a[2] for a in q) / len(q))
            oc = (sum(o[2] for o in ours) / len(ours), sum(o[3] for o in ours) / len(ours))
            for px, py in ((mx, my), (oc[0] - jc[0], oc[1] - jc[1])):
                if not land(rr, px, py, numbers): yield rr, px, py; break
    line = f'{ref:5} {f.GetFPIDAsString().split(":")[-1][:30]:30} {lcsc:10} {j["pkg"][:34]:34} CPL {rot:g}: ' + '; '.join(err)
    if not land(rot, mx, my, False) and not next(turns(False), None):
        notes.append(line + ' (JLC numbers its pins its own way: the pads fit ours this way only)'); ok += 1; continue
    fix = next(turns(), None)
    line += f' -> JLC needs rotation {fix[0]:g} at {fix[1]:.2f}, {fix[2]:.2f}' if fix else ' -> no turn fits'
    bad.append(line)
print(f'CPL parts {len(rows)}: {ok} on our pads, {len(bad)} to fix, '
      f'{len(nofp)} with no JLC footprint (check those in JLC\'s placement preview)')
for x in bad: print('  FIX ' + x)
for x in notes: print('  ok  ' + x)
for x in nofp: print('  no footprint: ' + x)
sys.exit(1 if bad else 0)
