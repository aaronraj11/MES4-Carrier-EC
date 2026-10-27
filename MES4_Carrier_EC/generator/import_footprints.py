"""One-time import of every footprint and net into MES4_Carrier_EC.kicad_pcb (what KiCad's F8 does on an
empty board), with the footprints grouped by schematic sheet below the board outline, ready to place.

Run with KiCad's Python, KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      generator/import_footprints.py <netlist from run.sh>
Afterwards use Update PCB from Schematic (F8) in KiCad: footprints carry the schematic symbol paths, so F8
matches them instead of adding duplicates. The script refuses to run on a board that already has footprints,
unless --add-missing is given: then it adds only the symbols that have no footprint yet, in a row below the
outline (KiCad's F8 without opening KiCad).
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find, first

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, 'MES4_Carrier_EC.kicad_pcb')
KICAD_FP = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
SHEETS = ['Main', 'CAN', 'Power', 'Relays1-2', 'Relays3-4', 'Sensors', 'LoadCell', 'AuxPower', 'Winch']
X0, Y0, ROW_W, GAP = 50.0, 165.0, 200.0, 2.0  # below the 200 x 100 mm outline (x 49.9-249.9, y 49.4-149.4)


def mm(v):
    return pcbnew.FromMM(v)


def lib_dir(lib):
    own = os.path.join(HERE, lib + '.pretty')
    return own if os.path.isdir(own) else os.path.join(KICAD_FP, lib + '.pretty')


def main(net_file, add_missing=False):
    board = pcbnew.LoadBoard(PCB)
    have = {f.GetReference() for f in board.GetFootprints()}
    if have and not add_missing:
        sys.exit('board already has footprints: use F8 (Update PCB from Schematic) in KiCad, or --add-missing')
    d = parse(open(net_file).read())[0]

    # symbols marked "exclude from BOM" in the schematic (test pads, net tie)
    no_bom = set()
    for f in os.listdir(HERE):
        if f.endswith('.kicad_sch'):
            for sy in find(parse(open(os.path.join(HERE, f)).read())[0], 'symbol'):
                if first(sy, 'in_bom') and first(sy, 'in_bom')[1] == 'no' and first(sy, 'uuid'):
                    no_bom.add(first(sy, 'uuid')[1])

    comps = []
    for c in find(first(d, 'components'), 'comp'):
        props = {first(p, 'name')[1]: (first(p, 'value') or [None, ''])[1] for p in find(c, 'property')}
        sp = first(c, 'sheetpath')
        comps.append(dict(ref=first(c, 'ref')[1], value=first(c, 'value')[1], fp=first(c, 'footprint')[1],
                          path=first(sp, 'tstamps')[1] + first(c, 'tstamps')[1],
                          sheet=props.get('Sheetname', ''), file=props.get('Sheetfile', ''),
                          lcsc=props.get('LCSC', ''), no_bom=first(c, 'tstamps')[1] in no_bom))

    # nets, then pad -> net
    nets, pad_net = {}, {}
    for n in find(first(d, 'nets'), 'net'):
        name = first(n, 'name')[1]
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
        nets[name] = ni
        for nd in find(n, 'node'):
            pad_net[(first(nd, 'ref')[1], first(nd, 'pin')[1])] = ni

    # load footprints
    groups = {s: [] for s in SHEETS}
    if add_missing:
        comps = [c for c in comps if c['ref'] not in have]
    for c in comps:
        lib, name = c['fp'].split(':', 1)
        fp = pcbnew.FootprintLoad(lib_dir(lib), name)
        if fp is None:
            sys.exit('footprint not found: ' + c['fp'])
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(c['ref'])
        fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH(c['path']))
        fp.SetSheetname(c['sheet'])
        fp.SetSheetfile(c['file'])
        fp.SetExcludedFromBOM(c['no_bom'])
        if c['lcsc']:
            f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldId(), 'LCSC')
            f.SetText(c['lcsc'])
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
            fp.AddField(f)
        for pad in fp.Pads():
            ni = pad_net.get((c['ref'], pad.GetNumber()))
            if ni is not None:
                pad.SetNet(ni)
        board.Add(fp)
        groups.setdefault(c['sheet'], []).append(fp)

    if add_missing:
        x = X0
        for c in comps:
            fp = next(f for f in board.GetFootprints() if f.GetReference() == c['ref'])
            fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(Y0 - 10.0)))
            x += 10.0
        board.BuildConnectivity()
        pcbnew.SaveBoard(PCB, board)
        print('added %d footprints: %s' % (len(comps), ' '.join(c['ref'] for c in comps)))
        return
    # shelf-pack each sheet's footprints in a block, blocks stacked below the outline, one label per block
    y = Y0
    for sheet in SHEETS + [s for s in groups if s not in SHEETS]:
        fps = groups.get(sheet) or []
        if not fps:
            continue
        lab = pcbnew.PCB_TEXT(board)
        lab.SetText('%s (%d parts)' % (sheet, len(fps)))
        lab.SetLayer(pcbnew.Cmts_User)
        lab.SetTextSize(pcbnew.VECTOR2I(mm(2), mm(2)))
        lab.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        lab.SetPosition(pcbnew.VECTOR2I(mm(X0), mm(y)))
        board.Add(lab)
        y += 4.0
        fps.sort(key=lambda f: -f.GetBoundingBox(False).GetHeight())
        x, row_h = X0, 0.0
        for fp in fps:
            bb = fp.GetBoundingBox(False)
            w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
            if x + w > X0 + ROW_W and x > X0:
                x, y, row_h = X0, y + row_h + GAP, 0.0
            pos = fp.GetPosition()
            off_x, off_y = pcbnew.ToMM(pos.x - bb.GetX()), pcbnew.ToMM(pos.y - bb.GetY())
            fp.SetPosition(pcbnew.VECTOR2I(mm(x + off_x), mm(y + off_y)))
            x += w + GAP
            row_h = max(row_h, h)
        y += row_h + 8.0

    board.BuildConnectivity()
    pcbnew.SaveBoard(PCB, board)
    print('imported %d footprints, %d nets' % (len(comps), len(nets)))


if __name__ == '__main__':
    main(sys.argv[1], '--add-missing' in sys.argv[2:])
