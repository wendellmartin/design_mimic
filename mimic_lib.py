"""Helpers shared by all Mimic part builders (run inside FreeCADCmd)."""
import math, os
import FreeCAD as App
import Part

RES_DOC = "Mimic_Resources"          # internal document Name of Mimic-Resources.FCStd
VS = "Dimensions"                    # VarSet object name inside it

# ---------------------------------------------------------------- expressions
def R(name):
    """Cross-document reference to an unscaled parameter."""
    return f"{RES_DOC}#{VS}.{name}"

def S(name):
    """Scaled body dimension:  (param * Scale)."""
    return f"({R(name)} * {R('Scale')})"

def half(expr):
    return f"({expr} / 2)"

def mul(expr, k):
    return f"({expr} * {k})"

def _q(e):
    """Numbers are lengths in mm; strings are already expressions."""
    return f"{e} mm" if isinstance(e, (int, float)) else str(e)

def add(*exprs):
    return "(" + " + ".join(_q(e) for e in exprs) + ")"

def sub(a, b):
    return f"({_q(a)} - {_q(b)})"

def neg(a):
    return f"(-{a})"

# ---------------------------------------------------------------- object helpers
class Ctx:
    """Build context for one part document: numeric values + document handle."""
    def __init__(self, doc, values):
        self.doc = doc
        self.v = values          # dict name -> float (mm / deg / plain), from the evaluated VarSet
        self.scale = values["Scale"]

    def s(self, name):
        """Numeric scaled value."""
        return self.v[name] * self.scale

    def obj(self, typ, name, **props):
        o = self.doc.addObject(typ, name)
        for k, val in props.items():
            setattr(o, k, val)
        return o

    def place(self, o, x=None, y=None, z=None, rot=None):
        """Placement.Base components from expressions (strings) or numbers; rot = App.Rotation (numeric)."""
        if rot is not None:
            o.Placement = App.Placement(App.Vector(0, 0, 0), rot)
        for axis, val in (("x", x), ("y", y), ("z", z)):
            if val is None:
                continue
            if isinstance(val, str):
                o.setExpression(f".Placement.Base.{axis}", val)
            else:
                b = o.Placement.Base
                setattr(b, axis, float(val))
                o.Placement.Base = b
        return o

    # primitives ------------------------------------------------------------
    def cylinder(self, name, radius, height, **pl):
        o = self.obj("Part::Cylinder", name)
        self._set(o, "Radius", radius); self._set(o, "Height", height)
        return self.place(o, **pl)

    def cone(self, name, r1, r2, height, **pl):
        o = self.obj("Part::Cone", name)
        self._set(o, "Radius1", r1); self._set(o, "Radius2", r2); self._set(o, "Height", height)
        return self.place(o, **pl)

    def sphere(self, name, radius, **pl):
        o = self.obj("Part::Sphere", name)
        self._set(o, "Radius", radius)
        return self.place(o, **pl)

    def ellipsoid(self, name, rz, rx, ry, **pl):
        o = self.obj("Part::Ellipsoid", name)
        self._set(o, "Radius1", rz); self._set(o, "Radius2", rx); self._set(o, "Radius3", ry)
        return self.place(o, **pl)

    def box(self, name, lx, ly, lz, **pl):
        o = self.obj("Part::Box", name)
        self._set(o, "Length", lx); self._set(o, "Width", ly); self._set(o, "Height", lz)
        return self.place(o, **pl)

    def torus(self, name, r_major, r_minor, angle3=None, **pl):
        o = self.obj("Part::Torus", name)
        self._set(o, "Radius1", r_major); self._set(o, "Radius2", r_minor)
        if angle3 is not None:
            self._set(o, "Angle3", angle3)
        return self.place(o, **pl)

    def _set(self, o, prop, val):
        if isinstance(val, str):
            o.setExpression(prop, val)
        else:
            setattr(o, prop, val)

    # booleans --------------------------------------------------------------
    def fuse(self, name, shapes):
        shapes = [s for s in shapes if s is not None]
        if len(shapes) == 1:
            return shapes[0]
        o = self.obj("Part::MultiFuse", name)
        o.Shapes = shapes
        o.Refine = True
        for s in shapes:
            s.Visibility = False
        self.doc.recompute()
        biggest = max((s.Shape.Volume for s in shapes if hasattr(s, "Shape") and not s.Shape.isNull()), default=0.0)
        if o.Shape.isNull() or not o.Shape.Solids or not o.Shape.isValid() or o.Shape.Volume < biggest * 0.999 \
                or not _covers(o.Shape, shapes, name):
            # OCC occasionally returns nothing (or an invalid shape) for a many-body MultiFuse (e.g. tori sharing poles);
            # a chain of pairwise fuses gets through.
            self.doc.removeObject(o.Name)
            acc = shapes[0]
            for i, s in enumerate(shapes[1:]):
                f = self.obj("Part::Fuse", f"{name}_f{i+1}" if i < len(shapes) - 2 else name)
                f.Base = acc; f.Tool = s
                f.Refine = False       # refine on complex lofted bodies can empty the result
                acc.Visibility = False; s.Visibility = False
                self.doc.recompute()
                if not f.Shape.isNull() and not acc.Shape.isNull() and not s.Shape.isNull()                         and f.Shape.Volume < max(acc.Shape.Volume, s.Shape.Volume) * 0.999:
                    print(f"[mimic]   WARNING fuse {f.Name}: result ({f.Shape.Volume:.0f}) smaller than an input "
                          f"({acc.Name} {acc.Shape.Volume:.0f}, {s.Name} {s.Shape.Volume:.0f}); a body was dropped")
                acc = f
            o = acc
        return o

    def cut(self, name, base, tool):
        if tool is None:
            return base
        o = self.obj("Part::Cut", name)
        o.Base = base; o.Tool = tool
        o.Refine = True
        base.Visibility = False; tool.Visibility = False
        return o

    def common(self, name, base, tool):
        o = self.obj("Part::Common", name)
        o.Base = base; o.Tool = tool
        o.Refine = True
        base.Visibility = False; tool.Visibility = False
        return o

    # ------------------------------------------------------------- snap joint
    def peg(self, name, x=0, y=0, z=0, rot=None):
        """One barbed peg: mating plane at (x,y,z) in the given rotation frame, protruding local +Z.
        Geometry copied from Shelf-with-Rail v0.2.0 (shaft, round-over approximated by a short cone, tip cone)."""
        shaft = self.cylinder(f"{name}_Shaft", R("PegRadius"), add(R("PegEmbed"), R("PegFlareDepth")),
                              z=neg(R("PegEmbed")))
        barb = self.cone(f"{name}_Barb", R("PegBarbRadius"), R("PegFlareRadius"),
                         sub(R("PegBarbTop"), R("PegFlareDepth")), z=R("PegFlareDepth"))
        tip = self.cone(f"{name}_Tip", R("PegFlareRadius"), 0.0,
                        sub(R("PegTip"), R("PegBarbTop")), z=R("PegBarbTop"))
        f = self.fuse(name, [shaft, barb, tip])
        return self._frame(f, x, y, z, rot)

    def socket(self, name, x=0, y=0, z=0, rot=None):
        """Negative of the peg + tolerance, same frame convention (peg enters going local +Z)."""
        bore = self.cylinder(f"{name}_Bore", R("SocketBoreRadius"), add(R("SocketExtend"), R("SocketLipTop")),
                             z=neg(R("SocketExtend")))
        lip = self.cone(f"{name}_Lip", R("SocketBoreRadius"), R("SocketLipRadius"),
                        sub(R("SocketLipBottom"), R("SocketLipTop")), z=R("SocketLipTop"))
        cav = self.cylinder(f"{name}_Cavity", R("SocketCavityRadius"),
                            sub(R("SocketCavityTop"), R("SocketLipBottom")), z=R("SocketLipBottom"))
        tip = self.cone(f"{name}_Tip", R("SocketCavityRadius"), 0.0,
                        sub(R("SocketTip"), R("SocketCavityTop")), z=R("SocketCavityTop"))
        f = self.fuse(name, [bore, lip, cav, tip])
        return self._frame(f, x, y, z, rot)

    def _frame(self, o, x, y, z, rot):
        """Put a fused feature into a frame: numeric rotation, expression or numeric position."""
        o.Placement = App.Placement(App.Vector(0, 0, 0), rot or App.Rotation())
        return self.place(o, x=x, y=y, z=z)

    def peg_pattern(self, name, face_dia_expr, face_dia_num, kind, z=0, rot=None):
        """Ring of pegs or sockets on a circular mating face centred on the local origin, mating plane at z.
        Returns (fused feature or None, count).  count = 0 means the face is too small for pegs."""
        n = peg_count(face_dia_num, self.v)
        if os.environ.get("MIMIC_LOG_PEGS"):
            print(f"[pegs] {self.doc.Name} {name} {kind} face={face_dia_num:.2f}mm n={n}")
        if n == 0:
            return None, 0
        ring_r = f"({face_dia_expr} / 2 - {R('SocketCavityRadius')} - 1.2 mm)"
        feats = []
        for i in range(n):
            ang = 360.0 * i / n
            x = f"{ring_r} * cos({ang:.4f} deg)"
            y = f"{ring_r} * sin({ang:.4f} deg)"
            f = (self.peg if kind == "peg" else self.socket)(f"{name}{i+1}", x=x, y=y, z=0)
            feats.append(f)
        grp = self.fuse(name, feats)
        return self._frame(grp, 0, 0, z, rot), n

def _covers(result, inputs, name, tol=0.05):
    """True when the result's bounding box contains every input's (a silently dropped body fails this)."""
    rb = result.BoundBox
    for s in inputs:
        if not hasattr(s, "Shape") or s.Shape.isNull():
            continue
        b = s.Shape.BoundBox
        if (b.XMin < rb.XMin - tol or b.YMin < rb.YMin - tol or b.ZMin < rb.ZMin - tol or
                b.XMax > rb.XMax + tol or b.YMax > rb.YMax + tol or b.ZMax > rb.ZMax + tol):
            print(f"[mimic]   fuse {name}: {s.Name} missing from result; falling back to pairwise")
            return False
    return True

def peg_count(face_dia_scaled_mm, v):
    """Pegs on a face: 0 below PegMinFace, else 2..8 growing with diameter."""
    if face_dia_scaled_mm < v["PegMinFace"]:
        return 0
    cavity = v["SocketCavityRadius"] * 2 + 2.4          # cavity dia + 1.2 mm wall each side
    ring = face_dia_scaled_mm - cavity                    # ring diameter through peg centres
    if ring < cavity * 0.8:
        return 2
    n = int((math.pi * ring) // (cavity * 1.6))           # keep neighbours ~1.6 cavities apart
    return max(2, min(8, n))

def split_count(length_scaled_mm, v):
    """How many pieces a straight feature of this length needs to fit the build cube."""
    usable = v["BuildVolume"] - v["SocketTip"] - 2.0
    return max(1, math.ceil(length_scaled_mm / usable))

# ---------------------------------------------------------------- documents
def new_part_doc(label, out_dir):
    """Create and immediately save a part document (cross-document expressions need a saved owner)."""
    doc = App.newDocument(label)
    path = os.path.join(out_dir, f"{label}.FCStd")
    doc.saveAs(path)
    return doc

def finish(doc, printable):
    """Mark the printable solids (list of objects) and save."""
    for o in doc.Objects:
        o.Visibility = False
    for o in printable:
        o.Visibility = True
    doc.recompute()
    for o in printable:
        if o.Shape.isNull() or "Invalid" in o.State:
            print(f"[mimic]   {o.Label}: first recompute failed ({o.State}); retrying")
            for x in doc.Objects:
                if "Invalid" in x.State:
                    print(f"[mimic]      invalid: {x.Name} {x.TypeId}")
            for x in doc.Objects:
                x.touch()
            doc.recompute()
            print(f"[mimic]   {o.Label}: after retry null={o.Shape.isNull()} state={o.State}")
    save_doc(doc)

def save_doc(doc):
    """doc.save() with a recovery: FreeCAD writes the whole document to <FileName>.<uuid> and then
    renames it into place, and on this machine that rename is sometimes refused ("Failed to write all
    data to file / Permission denied") although the temp file is a complete, valid zip and a rename
    from Python a moment later succeeds (an on-close virus scan holding the file, most likely).  So
    when the save fails, finish the rename ourselves."""
    import time, glob, zipfile
    err = None
    for attempt in range(4):
        try:
            doc.save()
            return
        except Exception as ex:
            err = ex
        tmps = sorted(glob.glob(doc.FileName + ".*"), key=os.path.getmtime)
        for tmp in reversed(tmps):
            try:
                if zipfile.ZipFile(tmp).testzip() is None:
                    os.replace(tmp, doc.FileName)
                    print(f"[mimic]   {doc.Name}: FreeCAD's save rename was refused ({err}); moved the temp file into place by hand")
                    for old in tmps:
                        if old != tmp and os.path.exists(old):
                            os.remove(old)
                    return
            except Exception:
                continue
        time.sleep(1)
    raise RuntimeError(f"{doc.Name}: could not save ({err})")
    return printable

def export_stl(obj, path, deflection=0.05):
    import MeshPart
    shape = obj.Shape
    if shape.isNull():
        raise RuntimeError(f"{obj.Label}: empty shape, not exported")
    if not shape.isValid():
        fixed = shape.copy()
        fixed.fix(0.01, 0.01, 0.01)
        if fixed.isValid():
            shape = fixed
            print(f"[mimic]   {obj.Label}: shape needed fixing before export")
        else:
            print(f"[mimic]   {obj.Label}: WARNING shape reports invalid; exporting anyway, check the STL")
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=deflection, AngularDeflection=0.3, Relative=False)
    m.write(path)
    bb = shape.BoundBox
    return (bb.XLength, bb.YLength, bb.ZLength), shape.Volume
