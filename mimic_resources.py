"""Mimic-Resources.FCStd: the Dimensions VarSet and a master proportion sketch."""
import os
import FreeCAD as App
import Part, Sketcher
from mimic_params import PARAMS, TYPES

def build_resources(out_dir, scale_override=None):
    doc = App.newDocument("Mimic-Resources")
    vs = doc.addObject("App::VarSet", "Dimensions")
    for p in PARAMS:
        name, typ, val, group, docstr = p[:5]
        vs.addProperty(TYPES[typ], name, group, docstr)
        if name == "Scale" and scale_override is not None:
            val = scale_override
        setattr(vs, name, val)
    for p in PARAMS:
        if len(p) > 5:
            vs.setExpression(p[0], p[5])
    # derived helpers used all over the parts
    vs.addProperty("App::PropertyFloat", "JointCupOffset", "Joints",
                   "Ball centre to flat mating face, as a fraction of ball radius.")
    vs.setExpression("JointCupOffset", "sqrt(1 - JointCupRatio ^ 2)")
    doc.recompute()

    _master_sketch(doc, vs)
    doc.recompute()
    path = os.path.join(out_dir, "Mimic-Resources.FCStd")
    doc.saveAs(path)
    return doc, vs

def values_from(vs):
    """Evaluated numeric values (mm / deg / plain) for build-time decisions."""
    out = {}
    for name in vs.PropertiesList:
        if name in ("Label", "Label2", "ExpressionEngine", "Visibility", "Proxy"):
            continue
        val = getattr(vs, name)
        if hasattr(val, "Value"):
            val = val.Value
        if isinstance(val, (int, float)):
            out[name] = float(val)
    out["JointCupOffset"] = float(vs.JointCupOffset)
    return out

def _master_sketch(doc, vs):
    """Front-view stick figure (XZ plane): a vertical stack for the body and one arm.
    Every length is an expression on the VarSet, so it tracks Scale and the proportions."""
    sk = doc.addObject("Sketcher::SketchObject", "MasterSketch")
    sk.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90))  # XZ plane
    S = lambda n: f"Dimensions.{n} * Dimensions.Scale"
    stack = [  # (label, scaled-length expression) bottom to top
        ("Foot",     S("FootHeight")),
        ("Shin",     S("ShinLength")),
        ("Thigh",    S("ThighLength")),
        ("PelvisDrop", S("PelvisDrop")),
        ("Spine",    S("SpineLength")),
        ("ShoulderHub", S("HubHeight")),
        ("Neck",     S("NeckLength")),
        ("Head",     f"({S('NeckPost')} + {S('HeadCageRadius')} * 1.95)"),
    ]
    y = 0.0
    prev = None
    for label, expr in stack:
        g = sk.addGeometry(Part.LineSegment(App.Vector(0, y, 0), App.Vector(0, y + 10, 0)), False)
        sk.addConstraint(Sketcher.Constraint("Vertical", g))
        if prev is None:
            sk.addConstraint(Sketcher.Constraint("Coincident", -1, 1, g, 1))
        else:
            sk.addConstraint(Sketcher.Constraint("Coincident", prev, 2, g, 1))
        c = sk.addConstraint(Sketcher.Constraint("DistanceY", g, 1, g, 2, 10.0))
        sk.renameConstraint(c, label)
        sk.setExpression(f".Constraints.{label}", expr)
        prev = g
        y += 10
    # arm: shoulder point hangs off the chest top, out by ShoulderWidth/2
    g = sk.addGeometry(Part.LineSegment(App.Vector(0, y, 0), App.Vector(20, y, 0)), False)
    sk.addConstraint(Sketcher.Constraint("Horizontal", g))
    # shoulders hang off the shoulder-hub segment (index 5), ShoulderDrop below its top
    sk.addConstraint(Sketcher.Constraint("PointOnObject", g, 1, 5))
    c = sk.addConstraint(Sketcher.Constraint("DistanceY", g, 1, 5, 2, 10.0))
    sk.renameConstraint(c, "ShoulderDrop")
    sk.setExpression(".Constraints.ShoulderDrop", S("ShoulderDrop"))
    c = sk.addConstraint(Sketcher.Constraint("DistanceX", g, 1, g, 2, 20.0))
    sk.renameConstraint(c, "HalfShoulder")
    sk.setExpression(".Constraints.HalfShoulder", f"{S('ShoulderWidth')} / 2")
    prev = g
    for label, expr in (("UpperArm", S("UpperArmLength")), ("Forearm", S("ForearmLength")), ("Hand", S("HandLength"))):
        g = sk.addGeometry(Part.LineSegment(App.Vector(20, y, 0), App.Vector(20, y - 10, 0)), False)
        sk.addConstraint(Sketcher.Constraint("Vertical", g))
        sk.addConstraint(Sketcher.Constraint("Coincident", prev, 2, g, 1))
        c = sk.addConstraint(Sketcher.Constraint("DistanceY", g, 2, g, 1, 10.0))
        sk.renameConstraint(c, label)
        sk.setExpression(f".Constraints.{label}", expr)
        prev = g
        y -= 10
    return sk
