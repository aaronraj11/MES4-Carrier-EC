"""VRML -> STEP for the project 3D models that only exist as VRML. KiCad's STEP export drops VRML models, so these
parts were missing from the board STEP; with a same-named .step beside the .wrl, `--subst-models` uses it.

    freecadcmd -c "import sys; sys.argv = ['wrl2step.py', '<3dshapes dir>', 'name', ...]; exec(open('generator/pcb/wrl2step.py').read())"

Each VRML Shape (one colour) becomes a solid built from its faces, at exactly the VRML's coordinates (KiCad VRML units
are 0.1 in = 2.54 mm), so the STEP sits where KiCad's 3D view shows the part; coplanar triangles are merged into faces.
Colours aren't kept (FreeCAD writes STEP colours only from its GUI)."""
import sys, os, re, Part, FreeCAD

D, names = sys.argv[1], sys.argv[2:]
for name in names:
    w = open(os.path.join(D, name + '.wrl')).read()
    solids = []
    for blk in re.split(r'\bShape\s*\{', w)[1:]:
        pt = re.search(r'point\s*\[([^\]]*)\]', blk); ix = re.search(r'coordIndex\s*\[([^\]]*)\]', blk)
        if not pt or not ix: continue
        v = [float(t) * 2.54 for t in re.split(r'[\s,]+', pt.group(1).strip()) if t]
        P = [FreeCAD.Vector(*v[i:i + 3]) for i in range(0, len(v), 3)]
        faces, poly = [], []
        for k in (int(t) for t in re.split(r'[\s,]+', ix.group(1).strip()) if t):
            if k >= 0: poly.append(k); continue
            q = [P[i] for i in poly]; poly = []
            q = [a for n, a in enumerate(q) if (a - q[n - 1]).Length > 1e-6]      # drop repeated points
            if len(q) < 3: continue
            try: faces.append(Part.Face(Part.makePolygon(q + [q[0]])))
            except Exception: pass                                                  # degenerate polygon
        if not faces: continue
        sh = Part.Shell(faces)
        try:
            s = Part.Solid(sh); s = s.removeSplitter() if s.isValid() else sh.removeSplitter()
        except Exception:
            s = sh
        solids.append(s)
    out = Part.makeCompound(solids)
    out.exportStep(os.path.join(D, name + '.step'))
    b = out.BoundBox
    print('%-40s %d shapes -> STEP  x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (name, len(solids), b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax))
