"""Bring the board's footprints in line with the schematic (what KiCad's Update PCB from Schematic does for these
items). Runs first in the rebuild chain, right after the base board is restored.

    parts_sync.py <pcb> <schematic>

- A footprint changed in the schematic (U9: URB2409S-10WR3 -> URB2409S-6WR3, review B1) is loaded from the project
  library and put where the old one sat, pad 1 on pad 1 (both are the same SIP-8 pad pattern, so every track still
  lands), with the old one's nets, schematic link, group and reference / value text placement.
- Value, Datasheet, Description, LCSC and the Fabrication Toolkit's placement fields ("FT Rotation Offset", "FT Position
  Offset": JLC's footprint turned / offset from ours, found by cpl_check.py) come from the schematic; an "FT" field
  the schematic no longer has is removed, and an empty field the schematic has is kept (KiCad 10's parity check, R4 E3).
  Parts the schematic keeps out of the BOM (the bare test pads TP1-TP9) are kept out of the BOM and the placement file
  too.
- Project-library footprints take their 3D models from the library (libs.py places the EasyEDA STEP models whose origin
  differs from their VRML's, e.g. J1's M.2 socket).
- The "LCSC Part" field that EasyEDA footprints carry is dropped: the Fabrication Toolkit reads it ahead of "LCSC",
  so a stale one put a 5 V converter at U9 and the wrong switch at SW2 in the production BOM (review B1)."""
import sys, os, shutil, subprocess, tempfile, xml.etree.ElementTree as ET, pcbnew

P, SCH = sys.argv[1], sys.argv[2]; T = pcbnew.ToMM
CLI = shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LIBDIR = os.path.join(os.path.dirname(os.path.abspath(SCH)), 'MES4-Carrier-EC.pretty')
tmp = tempfile.mktemp(suffix='.xml')
subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', tmp, SCH], capture_output=True)
comps = {}
for c in ET.parse(tmp).getroot().find('components'):
    comps[c.get('ref')] = dict(value=c.findtext('value'), fp=c.findtext('footprint'),
                               fields={f.get('name'): f.text or '' for f in c.find('fields')},
                               bom='exclude_from_bom' not in {p.get('name') for p in c.findall('property')})
os.remove(tmp)

b = pcbnew.LoadBoard(P)


def set_field(f, name, text):
    fld = f.GetFieldByName(name)
    if fld is not None: fld.SetText(text); return
    fld = pcbnew.PCB_FIELD(f, f.GetNextFieldId(), name); fld.SetText(text)    # text first: AddField takes it over
    fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab); fld.SetPosition(f.GetPosition()); f.AddField(fld)


def swap(f, libfp):
    lib, name = libfp.split(':')
    n = pcbnew.PCB_IO_KICAD_SEXPR().FootprintLoad(LIBDIR, name); n.SetFPID(pcbnew.LIB_ID(lib, name))   # (FootprintLoad()
    n.SetParent(b)                                          # finds no plugin in KiCad 9's Python)
    n.SetOrientation(f.GetOrientation()); n.SetPosition(f.GetPosition())
    n.Move(f.FindPadByNumber('1').GetPosition() - n.FindPadByNumber('1').GetPosition())
    for p in n.Pads():
        o = f.FindPadByNumber(p.GetNumber())
        assert o and (o.GetPosition() - p.GetPosition()).EuclideanNorm() < pcbnew.FromMM(0.01), f'{f.GetReference()} pad {p.GetNumber()} moved'
        p.SetNet(o.GetNet())
    for new_t, old_t in ((n.Reference(), f.Reference()), (n.Value(), f.Value())):
        new_t.SetLayer(old_t.GetLayer()); new_t.SetVisible(old_t.IsVisible()); new_t.SetPosition(old_t.GetPosition())
        new_t.SetTextAngle(old_t.GetTextAngle()); new_t.SetTextSize(old_t.GetTextSize()); new_t.SetTextThickness(old_t.GetTextThickness())
    n.SetReference(f.GetReference()); n.SetPath(f.GetPath()); n.SetSheetname(f.GetSheetname()); n.SetSheetfile(f.GetSheetfile())
    b.Add(n)
    g = f.GetParentGroup()
    if g: g.RemoveItem(f); g.AddItem(n)
    return n


old, swapped, dropped, nobom, models = [], [], 0, [], 0
for f in list(b.GetFootprints()):
    c = comps.get(f.GetReference())
    if c is None: continue                                  # board-only parts (the FE-URT-2 standoffs)
    if c['fp'] and f.GetFPIDAsString() != c['fp']:
        old.append(f); swapped.append(f'{f.GetReference()} {f.GetFPIDAsString()} -> {c["fp"]}'); f = swap(f, c['fp'])
    f.SetValue(c['value'])
    for name in ('Datasheet', 'Description', 'LCSC') + tuple(k for k in c['fields'] if k.startswith('FT ')):
        if name in c['fields'] or f.GetFieldByName(name) is not None: set_field(f, name, c['fields'].get(name, ''))
    for x in [x for x in f.GetFields() if x.GetName().startswith('FT ') and x.GetName() not in c['fields']]:
        f.RemoveField(x.GetName())                          # an offset the schematic dropped (J5, review R4 E2)
    if f.GetFieldByName('LCSC Part') is not None: f.RemoveField('LCSC Part'); dropped += 1
    if f.GetFPID().GetLibNickname() == 'MES4-Carrier-EC':     # 3D models as in the library
        lib = pcbnew.PCB_IO_KICAD_SEXPR().FootprintLoad(LIBDIR, f.GetFPID().GetLibItemName().wx_str())
        key = lambda fp: [(m.m_Filename, m.m_Offset.x, m.m_Offset.y, m.m_Offset.z, m.m_Rotation.z) for m in fp.Models()]
        if lib and key(lib) != key(f):
            f.Models().clear()
            for m in lib.Models(): f.Models().push_back(m)
            models += 1
    a = f.GetAttributes() & ~(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    if not c['bom']: a |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES; nobom.append(f.GetReference())
    f.SetAttributes(a)
for f in old: b.Remove(f)
pcbnew.SaveBoard(P, b)
print('parts_sync: swapped', swapped, '| "LCSC Part" dropped on', dropped, '| 3D models updated on', models,
      '| out of BOM / CPL:', ' '.join(sorted(nobom)))
