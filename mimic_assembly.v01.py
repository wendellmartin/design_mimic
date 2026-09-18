"""Mimic-Assembly.FCStd: App::Links to every printable piece, posed as a standing figure.

Placements are computed numerically from the evaluated VarSet at build time (they are NOT
expression-linked); re-run build.py after changing proportions or pose.  World: +Z up, +Y forward.
"""
import os
import FreeCAD as App

ROT0 = App.Rotation()
ROT_PX = App.Rotation(App.Vector(0, 1, 0), 90)
ROT_NX = App.Rotation(App.Vector(0, 1, 0), -90)
V = App.Vector
P = App.Placement

def build_assembly(out_dir, v, built):
    s = lambda n: v[n] * v["Scale"]
    co, cr = v["JointCupOffset"], v["JointCupRatio"]

    def seg_len(L, a, b):
        return s(L) - s(a) / 2 * co - s(b) / 2 * co

    def ball_distal(dia_scaled, bend):
        c = dia_scaled / 2 * co
        return P(V(0, 0, c) + bend.multVec(V(0, 0, c)), bend)

    def seg_distal(length):
        return P(V(0, 0, length), ROT0)

    # ---- torso frames --------------------------------------------------------------
    PH = s("PelvisHeight"); bar = s("PelvisWidth") - s("HipBall")
    CH, CD, SD, RD = s("ChestHeight"), s("ChestDepth"), s("SpineDiameter"), s("RibDiameter")
    y_sp = -(CD / 2 - SD / 2) * 0.85
    b = CD / 2 - RD / 2
    clav_len = s("ShoulderWidth") - s("ShoulderBall")
    clav_y, clav_z = y_sp + b * 0.4, CH - SD * 0.45
    rz = (s("HeadHeight") - s("JawHeight")) / 2
    z_flat = s("JawHeight") + rz * 0.25

    world = {}   # part name -> Placement of the part's local frame
    world["Pelvis"] = P()
    world["Spine"] = world["Pelvis"] * P(V(0, 0, PH * 0.5), ROT0)
    world["Chest"] = world["Spine"] * seg_distal(s("SpineGap"))
    neckball_dia = s("NeckDiameter") * 1.6
    world["NeckBall"] = world["Chest"] * P(V(0, y_sp, CH), ROT0)
    tilt = App.Rotation(V(1, 0, 0), -v["HeadTilt"])
    world["Neck"] = world["NeckBall"] * ball_distal(neckball_dia, tilt)
    world["Head"] = world["Neck"] * seg_distal(s("NeckLength"))
    world["Jaw"] = world["Head"] * P(V(0, s("HeadDepth") * 0.18, z_flat), ROT0)

    # ---- limbs, left (-X) and right (+X) ------------------------------------------
    for side, sx, rot_out in (("L", -1, ROT_NX), ("R", 1, ROT_PX)):
        hip = world["Pelvis"] * P(V(sx * bar / 2, 0, 0), rot_out)
        world[f"HipBall{side}"] = hip
        thigh = hip * ball_distal(s("HipBall"), App.Rotation(V(0, 1, 0), sx * 90))
        world[f"Thigh{side}"] = thigh
        knee = thigh * seg_distal(seg_len("ThighLength", "HipBall", "KneeBall"))
        world[f"KneeBall{side}"] = knee
        shin = knee * ball_distal(s("KneeBall"), App.Rotation(V(1, 0, 0), v["KneeBend"]))
        world[f"Shin{side}"] = shin
        ankle = shin * seg_distal(seg_len("ShinLength", "KneeBall", "AnkleBall"))
        world[f"AnkleBall{side}"] = ankle
        world[f"Foot{side}"] = ankle * ball_distal(s("AnkleBall"), ROT0)

        sh = world["Chest"] * P(V(sx * clav_len / 2, clav_y, clav_z), rot_out)
        world[f"ShoulderBall{side}"] = sh
        ua = sh * ball_distal(s("ShoulderBall"), App.Rotation(V(0, 1, 0), sx * (90 - v["ArmSplay"])))
        world[f"UpperArm{side}"] = ua
        el = ua * seg_distal(seg_len("UpperArmLength", "ShoulderBall", "ElbowBall"))
        world[f"ElbowBall{side}"] = el
        fa = el * ball_distal(s("ElbowBall"), App.Rotation(V(1, 0, 0), -v["ElbowBend"]))
        world[f"Forearm{side}"] = fa
        wr = fa * seg_distal(seg_len("ForearmLength", "ElbowBall", "WristBall"))
        world[f"WristBall{side}"] = wr
        world[f"Hand{side}"] = wr * ball_distal(s("WristBall"), ROT0)

    # which part file serves each frame (sided files exist only for chiral parts)
    def file_for(frame):
        for base in ("HipBall", "ShoulderBall", "Hand"):
            if frame.startswith(base):
                return frame if frame in built else base
        for base in ("Thigh", "KneeBall", "Shin", "AnkleBall", "Foot", "UpperArm", "ElbowBall", "Forearm", "WristBall"):
            if frame.startswith(base):
                return base
        return frame

    doc = App.newDocument("Mimic-Assembly")
    doc.saveAs(os.path.join(out_dir, "Mimic-Assembly.FCStd"))
    links, zmin = [], 0.0
    for frame, pl in world.items():
        part = file_for(frame)
        if part not in built:
            continue
        for lbl, obj, _pdoc in built[part]:
            ln = doc.addObject("App::Link", f"{frame}_{lbl}".replace("-", "_"))
            ln.LinkedObject = obj
            ln.Placement = pl
            ln.Label = f"{frame}:{lbl}"
            links.append(ln)
            if part == "Foot":
                bb = obj.Shape.BoundBox
                bb2 = bb.transformed(pl.toMatrix())
                zmin = min(zmin, bb2.ZMin)
    # stand the figure on the floor
    for ln in links:
        ln.Placement = P(V(0, 0, -zmin), ROT0) * ln.Placement
    doc.recompute()
    zmax = max((ln.Shape.BoundBox.ZMax for ln in links if not ln.Shape.isNull()), default=0)
    print(f"[mimic] assembly: {len(links)} links, standing height {zmax:.0f} mm "
          f"(target {v['TargetHeight'] * v['Scale']:.0f} mm)")
    import json
    rows = []
    for ln in links:
        m = ln.Placement.toMatrix()
        rows.append({"label": ln.Label, "stl": f"STL/Mimic-{ln.Label.split(':')[1]}.stl",
                     "matrix": [m.A[i] for i in range(16)]})
    with open(os.path.join(out_dir, "Mimic-Assembly.json"), "w") as f:
        json.dump({"scale": v["Scale"], "height": zmax, "links": rows}, f, indent=1)
    doc.save()
    return doc
