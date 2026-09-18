"""Build every Mimic document.  Run with FreeCADCmd (see run.ps1):

    FreeCADCmd.exe -c "exec(open('C:/Users/wende/dev/Claude/3D/mimic/build.py').read())"

Environment:
    MIMIC_OUT    output folder (default: G:/My Drive/Projects/3D/Weyland/FNAF/Mimic)
    MIMIC_SCALE  overrides the Scale parameter (e.g. 0.25 for the proof of concept, 1 for life size)
    MIMIC_PARTS  comma list of part builders to run (default: all)
"""
import os, sys, importlib, traceback

HERE = "C:/Users/wende/dev/Claude/3D/mimic"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in list(sys.modules):
    if m.startswith("mimic_"):
        del sys.modules[m]          # fresh import every run inside a long-lived FreeCADCmd

import FreeCAD as App
import mimic_resources, mimic_lib, mimic_parts, mimic_assembly

OUT = os.environ.get("MIMIC_OUT", "G:/My Drive/Projects/3D/Weyland/FNAF/Mimic")
SCALE = os.environ.get("MIMIC_SCALE")
SCALE = float(SCALE) if SCALE else None
ONLY = os.environ.get("MIMIC_PARTS")
ONLY = [p.strip() for p in ONLY.split(",")] if ONLY else None

def main():
    os.makedirs(OUT, exist_ok=True)
    stl_dir = os.path.join(OUT, "STL")
    os.makedirs(stl_dir, exist_ok=True)
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)

    res_doc, vs = mimic_resources.build_resources(OUT, SCALE)
    values = mimic_resources.values_from(vs)
    print(f"[mimic] Scale={values['Scale']}  figure height={values['TargetHeight']*values['Scale']:.0f} mm")

    manifest = []      # (part, piece label, bbox, volume_cm3, note)
    built = {}         # part name -> list of (piece label, obj, doc)
    for name, builder in mimic_parts.BUILDERS:
        if ONLY and name not in ONLY:
            continue
        try:
            doc = mimic_lib.new_part_doc(f"Mimic-{name}", OUT)
            ctx = mimic_lib.Ctx(doc, values)
            pieces = builder(ctx)            # list of (label, printable obj)
            mimic_lib.finish(doc, [o for _, o in pieces])
            # reopen: a fresh recompute from disk is more reliable than the incremental one
            # (OCC sometimes drops a body from a long fuse chain the first time through)
            path, names = doc.FileName, [o.Name for _, o in pieces]
            App.closeDocument(doc.Name)
            doc = App.openDocument(path)
            doc.recompute()
            pieces = [(lbl, doc.getObject(n)) for (lbl, _), n in zip(pieces, names)]
            built[name] = [(lbl, o, doc) for lbl, o in pieces]
            for lbl, o in pieces:
                path = os.path.join(stl_dir, f"Mimic-{lbl}.stl")
                bbox, vol = mimic_lib.export_stl(o, path)
                over = " OVERSIZE" if max(bbox) > values["BuildVolume"] else ""
                manifest.append((name, lbl, bbox, vol / 1000.0, over))
                print(f"[mimic]   {lbl:28s} {bbox[0]:6.1f} x {bbox[1]:6.1f} x {bbox[2]:6.1f} mm  {vol/1000:7.1f} cm3{over}")
        except Exception:
            print(f"[mimic] FAILED {name}")
            traceback.print_exc()

    try:
        mimic_assembly.build_assembly(OUT, values, built)
    except Exception:
        print("[mimic] FAILED assembly")
        traceback.print_exc()

    with open(os.path.join(OUT, "Mimic-Manifest.md"), "w", encoding="utf-8") as f:
        f.write(f"# Mimic build manifest\n\nScale {values['Scale']}, figure height "
                f"{values['TargetHeight']*values['Scale']:.0f} mm, build cube {values['BuildVolume']:.0f} mm.\n\n")
        f.write("| Part | Piece | X | Y | Z | cm3 | |\n|---|---|---|---|---|---|---|\n")
        for part, lbl, bb, vol, over in manifest:
            f.write(f"| {part} | {lbl} | {bb[0]:.1f} | {bb[1]:.1f} | {bb[2]:.1f} | {vol:.1f} | {over} |\n")
    import shutil
    shutil.copy(os.path.join(HERE, "viewer.html"), os.path.join(OUT, "Mimic-Viewer.html"))
    with open(os.path.join(OUT, "index.html"), "w") as f:      # the folder root opens the viewer
        f.write('<meta http-equiv="refresh" content="0; url=Mimic-Viewer.html?view=front">')
    print("[mimic] done")

main()
