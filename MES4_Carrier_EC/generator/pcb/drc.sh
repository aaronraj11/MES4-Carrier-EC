#!/bin/zsh
S=${TMPDIR:-/tmp}   # drc.json goes here
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --schematic-parity --format json --severity-all -o $S/drc.json $1 >/dev/null 2>&1
python3 - "$2" <<PY
import json,collections,sys
d=json.load(open('$S/drc.json')); keys=[k for k in sys.argv[1].split(',') if k]
c=collections.Counter(v['type'] for v in d['violations']); print('violations',len(d['violations']),dict(c)); print('unconnected',len(d['unconnected_items']),'parity',len(d['schematic_parity']))
for v in d['violations']:
    if v['type']!='silk_edge_clearance' and 'Circle of J1' not in str(v): print(v['type'], [(i['description'],round(i['pos']['x'],2),round(i['pos']['y'],2)) for i in v['items']])
for u in d['unconnected_items']:
    if any(k in str(u) for k in keys): print('UNC',[i['description'] for i in u['items']])
PY
