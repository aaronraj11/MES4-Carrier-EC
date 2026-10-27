"""Run the MES4-Carrier-EC LTspice test benches and print the .meas results.
Usage: python3 run_sims.py   (LTspice for macOS in /Applications)"""
import glob, os, re, struct, subprocess, sys

LT = '/Applications/LTspice.app/Contents/MacOS/LTspice'
HERE = os.path.dirname(os.path.abspath(__file__))
BENCHES = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(HERE, '*.net')))


def run(name):
    for ext in ('.log', '.raw'):
        try:
            os.remove(os.path.join(HERE, name + ext))
        except FileNotFoundError:
            pass
    subprocess.run([LT, '-b', name + '.net'], cwd=HERE, timeout=600, check=False)
    log = open(os.path.join(HERE, name + '.log'), 'rb').read()
    txt = log.decode('utf-16-le') if log[1:2] == b'\x00' else log.decode('utf-8', 'replace')
    meas = {}
    for line in txt.splitlines():  # 'name: expr=value', 'name=value FROM..', AC 'name: expr=(xdB,y°)'
        m = re.match(r'^(\w+)(?::\s.*?)?=\(?([-\d.eE+]+)(dB)?', line)
        if m and m.group(1).lower() not in ('tnom', 'temp', 'method', 'solver'):
            when = re.search(r'\sAT\s([-\d.eE+]+)', line)  # WHEN results: the crossing time / frequency
            meas[m.group(1).lower() + ('_db' if m.group(3) else '')] = float(when.group(1) if when else m.group(2))
    errs = [l for l in txt.splitlines() if re.search(r"error|fail|singular|timestep too small", l, re.I)]
    return meas, errs


def read_raw(name):
    b = open(os.path.join(HERE, name + '.raw'), 'rb').read()
    mark = 'Binary:\n'.encode('utf-16-le')
    i = b.find(mark)
    head = b[:i].decode('utf-16-le')
    nvar = int(re.search(r'No. Variables:\s*(\d+)', head).group(1))
    npts = int(re.search(r'No. Points:\s*(\d+)', head).group(1))
    names = re.findall(r'^\t\d+\t(\S+)\t', head, re.M)
    data = b[i + len(mark):]
    cols = {n: [] for n in names}
    if 'complex' in re.search(r'Flags:(.*)', head).group(1):  # AC: every value is a complex double
        rec = 16 * nvar
        for k in range(npts):
            vals = struct.unpack_from('<%dd' % (2 * nvar), data, k * rec)
            for j, n in enumerate(names):
                re_, im = vals[2 * j], vals[2 * j + 1]
                cols[n].append(re_ if j == 0 else complex(re_, im))
        return cols
    rec = 8 + 4 * (nvar - 1)
    for k in range(npts):
        off = k * rec
        cols[names[0]].append(abs(struct.unpack_from('<d', data, off)[0]))
        vals = struct.unpack_from('<%df' % (nvar - 1), data, off + 8)
        for n, v in zip(names[1:], vals):
            cols[n].append(v)
    return cols


if __name__ == '__main__':
    for n in (sys.argv[1:] or BENCHES):
        meas, errs = run(n)
        print('==', n)
        for k, v in meas.items():
            print('   %-10s %.4g' % (k, v))
        for e in errs:
            print('   !', e)
