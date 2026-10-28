#!/bin/zsh
# render.sh <pcb> <out.png> <x0> <y0> <w> <h> [layers] [px_width]
PCB=$1; OUT=$2; X=$3; Y=$4; W=$5; H=$6; L=${7:-F.Cu,F.Silkscreen,Edge.Cuts}; PX=${8:-1600}
D=$(dirname $OUT); B=${OUT:r}
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb export svg --layers $L --mode-single --exclude-drawing-sheet -o $B.svg $PCB >/dev/null 2>&1
python3 - $B.svg $X $Y $W $H <<'PY'
import sys,re
f,x,y,w,h=sys.argv[1:]; s=open(f).read()
s=re.sub(r'viewBox="[^"]*"', f'viewBox="{x} {y} {w} {h}"', s, count=1)
s=re.sub(r'(<svg[^>]*?)width="[^"]*"', r'\1width="100%"', s, count=1)
s=re.sub(r'(<svg[^>]*?)height="[^"]*"', r'\1height="100%"', s, count=1)
s=s.replace('<svg','<svg style="background:#111"',1)
open(f,'w').write(s)
PY
PH=$(python3 -c "print(int($PX*$H/$W))")
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --window-size=$PX,$PH --screenshot=$OUT file://$B.svg >/dev/null 2>&1
echo $OUT
