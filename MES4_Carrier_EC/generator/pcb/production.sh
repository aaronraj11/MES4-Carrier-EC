#!/bin/zsh
# JLC production files (Fabrication Toolkit, headless), then the placement gate: the order zip only stays when every
# part in the CPL sits on our pads the way JLC places it (cpl_check.py; review R4 E1 / E2).
#   generator/pcb/production.sh        (KiCad closed)
G="$(cd "$(dirname "$0")" && pwd)"
OUT="$(dirname "$(dirname "$G")")"
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
FT=~/Documents/KiCad/9.0/3rdparty/plugins/com_github_bennymeg_JLC-Plugin-for-KiCad
W=${TMPDIR:-/tmp}/mes4ec_ft; rm -rf $W; mkdir -p $W; cp -R $FT $W/jlcft     # the plugin folder's name isn't importable
PCB="$OUT/MES4_Carrier_EC.kicad_pcb"
(cd $W && $PY -m jlcft.cli -p "$PCB" -t -f > $W/ft.log 2>&1) || { tail -5 $W/ft.log; exit 1; }
$PY "$G/cpl_check.py" "$PCB" "$OUT/MES4_Carrier_EC.kicad_sch" "$OUT/production/positions.csv" 2>&1 | grep -v 'wxApp\|stdpbase\|assert'
if [ ${pipestatus[1]} -ne 0 ]; then
    rm -f "$OUT/production/MES4_Carrier_EC.zip"; echo "CPL check failed: production/MES4_Carrier_EC.zip removed"; exit 1
fi
