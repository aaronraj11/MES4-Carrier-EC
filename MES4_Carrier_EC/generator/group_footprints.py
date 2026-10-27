"""Group the footprints that must sit together into named KiCad groups, packed as blocks below the board
outline, ready to drag onto the board. Footprints already inside the outline are left where they are.

Run with KiCad's Python, KiCad closed:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      generator/group_footprints.py
Rerunnable: groups with these names are rebuilt; the sheet labels from import_footprints.py are removed.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, 'MES4_Carrier_EC.kicad_pcb')
OUTLINE = (49.9, 49.4, 249.9, 149.4)
X0, Y0, ROW_W, GAP, GGAP = 50.0, 165.0, 200.0, 1.5, 8.0

R = lambda a, b, p='R': ['%s%d' % (p, k) for k in range(a, b + 1)]
# (group name, why the parts belong together, refs)
GROUPS = [
    ('PWR-IN 24 V input', 'XT30 -> F1 -> Q1 (D8, R6) -> D9 + C1-C3: one tight high-current loop at the board edge',
     ['J5', 'F1', 'Q1', 'D8', 'R6', 'D9', 'C1', 'C2', 'C3', 'TP1', 'LED3', 'R7']),
    ('PWR-DCDC logic 24 V -> 5 V', 'L1 pi filter + C4/C5 at U1 input, C6/C7 at its output',
     ['L1', 'C4', 'C5', 'U1', 'C6', 'C7', 'TP2', 'TP3']),
    ('PWR-5V module feed', 'F2 + FB1 + C8/C9: next to J1 fingers 20/22', ['F2', 'FB1', 'C8', 'C9', 'TP4']),
    ('GND joint', 'NT1 (only GND_24V-GND joint) and the ground test pads; keep J15/J17 near it (review L3)',
     ['NT1', 'TP5', 'TP6', 'TP7']),
    ('MOD M.2 socket', 'J1 + H1 hold-down (40.25 mm from the socket posts), power LEDs, I2C / ALERT pull-ups',
     ['J1', 'H1', 'LED1', 'R1', 'LED2', 'R2', 'R3', 'R4', 'R5']),
    ('DBG ST-Link + reset', 'STDC14 with its five ESD clamps and the reset button', ['J2', 'D1', 'D2', 'D3', 'D4', 'D5', 'SW1']),
    ('MECH mounting holes', 'board corners', ['H2', 'H3', 'H4', 'H5']),
    ('CAN DB9', 'D6 ESD right at the DB9 (board edge)', ['J3', 'D6']),
    ('CAN RJ45 x4', 'D7 ESD right at the RJ45 bank (board edge)', ['J4', 'D7']),
] + [
    ('RLY%d %s' % (n, load), 'shunt -> INA236 (Kelvin, short), driver + flyback at the coil, PTC + SS34 + LED at the output',
     ['K%d' % n, 'Q%d' % (n + 1), r_g, r_pd, 'D%d' % d_fb, r_sh, 'U%d' % (n + 1), 'C%d' % c, 'F%d' % (n + 2),
      'D%d' % d_out, 'J%d' % (n + 5), 'LED%d' % (n + 3), r_led])
    for n, load, r_g, r_pd, d_fb, r_sh, c, d_out, r_led in (
        (1, 'safety light', 'R9', 'R10', 10, 'R8', 10, 12, 'R14'),
        (2, 'LED DRL', 'R12', 'R13', 11, 'R11', 11, 13, 'R15'),
        (3, 'battery stopper', 'R17', 'R18', 14, 'R16', 12, 16, 'R22'),
        (4, 'spare', 'R20', 'R21', 15, 'R19', 13, 17, 'R23'))
] + [
    ('SNS1 sensor PB6', 'terminal, 100 mA PTC, opto input', ['J10', 'F7', 'C14', 'R24', 'D18', 'U6', 'R25']),
    ('SNS2 sensor PC15', 'terminal, 100 mA PTC, opto input', ['J11', 'F8', 'C15', 'R26', 'D19', 'U7', 'R27']),
    ('LC load cell', 'J12/J13 -> R28-R31 + C16-C21 + BAV199 -> U8 pins; C22/C23/C24/C25/FB2 at U8; away from the 24 V terminals (M2)',
     ['J12', 'J13', 'U8', 'FB2'] + R(28, 34) + R(16, 25, 'C') + ['D20', 'D21']),
    ('AUX 24 V filter', 'L2 pi filter for the IMU and screen converters', ['L2', 'C26', 'C27']),
    ('AUX IMU 9 V', 'U9 with its in/out caps, SW2, LED8, J14', ['U9', 'C28', 'C29', 'SW2', 'LED8', 'R35', 'J14', 'TP8']),
    ('AUX screen 5 V', 'U10 with its caps, F11, D22, USB-C J16 with CC / shield parts',
     ['U10', 'C30', 'C33', 'C34', 'C35', 'F11', 'D22', 'J16', 'R40', 'R41', 'R42', 'C37', 'TP9']),
    ('AUX servo', 'J15 24 V + J17 UART with F9/F10, bulk, series R, ESD; near NT1 (L3)',
     ['J15', 'F9', 'C31', 'C32', 'J17', 'F10', 'C36', 'R36', 'R37', 'R38', 'R39', 'D23', 'D24']),
    ('WCH winch relays', 'K5/K6 with drivers and flybacks; J18 + contact side isolated (Winch_48V, >= 2 mm)',
     ['K5', 'K6', 'Q6', 'Q7', 'R43', 'R44', 'R45', 'R46', 'D25', 'D26', 'J18']),
]


def mm(v):
    return pcbnew.FromMM(v)


def bbox_mm(fp):
    bb = fp.GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), bb


def inside(fp):
    x, y = pcbnew.ToMM(fp.GetX()), pcbnew.ToMM(fp.GetY())
    return OUTLINE[0] < x < OUTLINE[2] and OUTLINE[1] < y < OUTLINE[3]


def strip_previous(names):
    """Drop what this script (and import_footprints.py) added before: the Cmts.User labels and the groups with
    these names. Done on the file text, so pcbnew never has to delete items (its SWIG bindings break on that)."""
    txt = open(PCB).read()

    def blocks(kind):
        i = 0
        while True:
            k = txt.find('\t(%s "' % kind, i)
            if k < 0:
                return
            depth, j = 0, k + 1
            while True:
                c = txt[j]
                if c == '"':
                    j = txt.index('"', j + 1)
                elif c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            name = txt[k + len('\t(%s "' % kind):txt.index('"', k + len('\t(%s "' % kind))]
            yield k, j + 1, name, txt[k:j + 1]
            i = j + 1

    cut = [(a, b) for a, b, n, blk in blocks('gr_text')
           if '(layer "Cmts.User")' in blk and (n.endswith(' parts)') or n in names)]
    cut += [(a, b) for a, b, n, blk in blocks('group') if n in names]
    for a, b in sorted(cut, reverse=True):
        txt = txt[:a] + txt[b + 1 if txt[b:b + 1] == '\n' else b:]
    open(PCB, 'w').write(txt)


def main():
    strip_previous({g[0] for g in GROUPS})
    board = pcbnew.LoadBoard(PCB)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    listed = [r for _, _, refs in GROUPS for r in refs]
    dup = {r for r in listed if listed.count(r) > 1}
    missing = [r for r in listed if r not in fps]
    unlisted = sorted(set(fps) - set(listed))
    if dup or missing or unlisted:
        sys.exit('group table mismatch: duplicates %s, missing %s, not grouped %s' % (sorted(dup), missing, unlisted))

    gx, gy, row_h = X0, Y0, 0.0
    for name, why, refs in GROUPS:
        members = [fps[r] for r in refs]
        free = [f for f in members if not inside(f)]
        if free:
            # pack this group's free footprints into a roughly square block
            area = sum(bbox_mm(f)[0] * bbox_mm(f)[1] for f in free)
            width = max(max(bbox_mm(f)[0] for f in free), min(90.0, math.sqrt(area) * 1.6))
            free.sort(key=lambda f: -bbox_mm(f)[1])
            x = y = shelf = bw = 0.0
            spots = []
            for f in free:
                w, h, _ = bbox_mm(f)
                if x + w > width and x > 0:
                    x, y, shelf = 0.0, y + shelf + GAP, 0.0
                spots.append((f, x, y))
                x += w + GAP
                shelf = max(shelf, h)
                bw = max(bw, x - GAP)
            bh = y + shelf + 5.0  # room for the label under the block
            bw = max(bw, 1.25 * len(name))  # and for the label's width
            if gx + bw > X0 + ROW_W and gx > X0:
                gx, gy, row_h = X0, gy + row_h + GGAP, 0.0
            for f, x, y in spots:
                w, h, bb = bbox_mm(f)
                ox, oy = pcbnew.ToMM(f.GetX() - bb.GetX()), pcbnew.ToMM(f.GetY() - bb.GetY())
                f.SetPosition(pcbnew.VECTOR2I(mm(gx + x + ox), mm(gy + y + oy)))
            lab = pcbnew.PCB_TEXT(board)
            lab.SetText(name)
            lab.SetLayer(pcbnew.Cmts_User)
            lab.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
            lab.SetTextThickness(mm(0.2))
            lab.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
            lab.SetPosition(pcbnew.VECTOR2I(mm(gx), mm(gy + bh - 2.0)))
            board.Add(lab)
            members.append(lab)
            gx += bw + GGAP
            row_h = max(row_h, bh)
        grp = pcbnew.PCB_GROUP(board)
        grp.SetName(name)
        for m in members:
            grp.AddItem(m)
        board.Add(grp)
        print('%-28s %2d parts  %s' % (name, len(refs), why))
    pcbnew.SaveBoard(PCB, board)
    print('%d groups, %d footprints' % (len(GROUPS), len(listed)))


if __name__ == '__main__':
    main()
