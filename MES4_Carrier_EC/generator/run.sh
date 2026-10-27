#!/bin/zsh
# Regenerate the MES4-Carrier-EC schematic, libraries and checks.
# Usage: ./run.sh   (KiCad must be CLOSED: it overwrites the .kicad_pro on exit)
G="$(cd "$(dirname "$0")" && pwd)"
OUT="$(dirname "$G")"
CHK="${TMPDIR:-/tmp}/mes4ec_check"; mkdir -p "$CHK"
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
python3 "$G/gen.py" || exit 1
python3 "$G/libs.py" > /dev/null || exit 1
cd "$OUT"
$CLI sch erc --format json --severity-all -o "$CHK/erc.json" MES4_Carrier_EC.kicad_sch 2>&1 | grep Found
python3 -c "
import json
d=json.load(open('$CHK/erc.json'))
for sh in d['sheets']:
    for v in sh['violations']:
        print('  ', v['severity'], v['type'], v['description'][:100], [i['description'][:50] for i in v['items']][:2])
"
$CLI sch export netlist --format kicadsexpr -o "$CHK/ec.net" MES4_Carrier_EC.kicad_sch 2>&1 | grep -v -i fontconfig
python3 "$G/checks.py" "$CHK/ec.net" "$OUT" || exit 1
$CLI sch export pdf -o MES4_Carrier_EC.pdf MES4_Carrier_EC.kicad_sch 2>&1 | grep -v -i fontconfig | grep -v Plotted
echo "netlist: $CHK/ec.net  (dump a sheet: python3 $G/netdump.py $CHK/ec.net /Winch)"
