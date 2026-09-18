"""Part builders.  Each takes a Ctx and returns [(piece label, printable object), ...].

Frame convention for every chained part:  origin = centre of the PROXIMAL mating face,
local +Z = chain direction (toward the extremity).  Sockets live on proximal faces,
pegs on distal faces, both oriented so the peg travels local +Z into its socket.
"""
import math
import FreeCAD as App
from mimic_lib import R, S, half, mul, add, sub, neg, peg_count, split_count

ROT0 = App.Rotation()
BIG = 5000.0   # slab size for splitting cuts, mm
CREST_ROOT = 1.11   # shoulder crest (solid sector) outer radius, as a fraction of ball radius
GEAR_TIP = 1.4834   # tip radius of the gear spikes on it (was 0.97 * 1.22 + 0.3 when the crest was 1.22 r)

# ============================================================== snap test
def build_snaptest(ctx):
    """Two 24 mm coupons: pegs on one, sockets in the other.  Print first, verify the click."""
    dia, dia_n = "24 mm", 24.0
    top = ctx.cylinder("PegCouponBody", half(dia), "6 mm", z="-6 mm")
    pegs, n = ctx.peg_pattern("Pegs", dia, dia_n, "peg")
    peg_coupon = ctx.fuse("PegCoupon", [top, pegs])
    bot = ctx.cylinder("SocketCouponBody", half(dia), "8 mm")
    socks, _ = ctx.peg_pattern("Sockets", dia, dia_n, "socket")
    sock_coupon = ctx.cut("SocketCoupon", bot, socks)
    sock_coupon.Placement = App.Placement(App.Vector(40, 0, 0), ROT0)
    return [("SnapTest-Pegs", peg_coupon), ("SnapTest-Sockets", sock_coupon)]

# ============================================================== generic limb strut
def segment(ctx, name, length, length_n, dia, dia_n, prox_face, prox_face_n, dist_face, dist_face_n,
            rods=True, collar=True, extras=None):
    """A strut from z=0 (proximal face, dia prox_face) to z=length (distal face, dia dist_face).
    `length` etc. are expression strings, `*_n` the scaled numeric values.  Splits itself to fit the build cube."""
    cup = "0.35"                                    # cup height as a fraction of face diameter
    prox_cup_h = mul(prox_face, cup)
    dist_cup_h = mul(dist_face, cup)
    feats = []
    feats.append(ctx.cone(f"{name}_ProxCup", half(prox_face), half(dia), prox_cup_h))
    feats.append(ctx.cylinder(f"{name}_Strut", half(dia), length))
    feats.append(ctx.cone(f"{name}_DistCup", half(dia), half(dist_face), dist_cup_h,
                          z=sub(length, dist_cup_h)))
    if rods:
        rod_r = mul(dia, 0.15)
        rod_len = sub(length, add(prox_cup_h, dist_cup_h))
        for i, ang in enumerate((90, 270)):
            x = f"{mul(dia, 0.55)} * cos({ang} deg)"
            y = f"{mul(dia, 0.55)} * sin({ang} deg)"
            feats.append(ctx.cylinder(f"{name}_Rod{i+1}", rod_r, rod_len, x=x, y=y, z=prox_cup_h))
    if collar:
        feats.append(ctx.cylinder(f"{name}_Collar", mul(dia, 0.65), mul(length, 0.12), z=mul(length, 0.42)))
    body = ctx.fuse(f"{name}_Body", feats + list(extras or []))

    n = split_count(length_n, ctx.v)
    pieces = []
    for i in range(n):
        if n == 1:
            piece = body
        else:
            z0 = f"{length} * {i} / {n}"
            slab = ctx.box(f"{name}_Slab{i+1}", BIG, BIG, f"{length} / {n}", x=-BIG / 2, y=-BIG / 2, z=z0)
            piece = ctx.common(f"{name}_Cut{i+1}", body, slab)
        # proximal side: sockets (from the ball, or from the previous piece)
        if i == 0:
            socks, _ = ctx.peg_pattern(f"{name}_ProxSockets", prox_face, prox_face_n, "socket")
        else:
            socks, _ = ctx.peg_pattern(f"{name}_SplitSockets{i}", dia, dia_n, "socket", z=f"{length} * {i} / {n}")
        piece = ctx.cut(f"{name}_S{i+1}", piece, socks)
        # distal side: pegs (into the ball, or into the next piece)
        if i == n - 1:
            pegs, _ = ctx.peg_pattern(f"{name}_DistPegs", dist_face, dist_face_n, "peg", z=length)
        else:
            pegs, _ = ctx.peg_pattern(f"{name}_SplitPegs{i+1}", dia, dia_n, "peg", z=f"{length} * {i+1} / {n}")
        piece = ctx.fuse(f"{name}{'' if n == 1 else i+1}", [piece, pegs])
        piece.Label = f"{name}" if n == 1 else f"{name}-{i+1}of{n}"
        pieces.append((piece.Label, piece))
    return pieces

# ============================================================== generic ball joint
def ball(ctx, name, dia, dia_n, bend=ROT0, detail=True, crest=None):
    """Sphere with two flat mating faces.  Proximal face at z=0 (sockets), distal face rotated by `bend`
    (pegs).  Face diameter = dia * JointCupRatio; centre sits JointCupOffset * r above the proximal face."""
    r = half(dia)
    c = f"({r} * {R('JointCupOffset')})"
    face = mul(dia, R("JointCupRatio"))
    face_n = dia_n * ctx.v["JointCupRatio"]
    c_n = dia_n / 2 * ctx.v["JointCupOffset"]
    ax = up = None
    if crest is not None:
        ax = App.Vector(crest["axis"]); ax.normalize()
        up = App.Vector(crest["up"]); up = up - ax * up.dot(ax); up.normalize()
    # with a crest, put the sphere's poles on the crest axis: the sector edges crossing the sphere's
    # seam otherwise leave a face OCC can't tessellate (the STL came out hollow)
    sph = ctx.sphere(f"{name}_Sphere", r, z=c, rot=App.Rotation(App.Vector(0, 0, 1), ax) if ax is not None else None)
    feats = [sph]
    if detail:
        # equatorial ring: reads as the socket cup of an endoskeleton joint
        feats.append(ctx.cylinder(f"{name}_Ring", mul(r, 0.92), mul(r, 0.5), z=sub(c, mul(r, 0.25))))
    body = ctx.fuse(f"{name}_Body", feats)
    # flatten proximal face
    below = ctx.box(f"{name}_ProxTrim", BIG, BIG, BIG, x=-BIG / 2, y=-BIG / 2, z=-BIG)
    body = ctx.cut(f"{name}_P", body, below)
    # flatten distal face: a slab beyond the plane at centre + c * d, rotated by bend
    d = bend.multVec(App.Vector(0, 0, 1))
    dist = {"x": f"({c} * {d.x:.6f})", "y": f"({c} * {d.y:.6f})", "z": f"({c} + {c} * {d.z:.6f})"}
    above = ctx.box(f"{name}_DistTrim", BIG, BIG, BIG, rot=bend)
    # box origin is its corner: shift so its -Z face passes through the distal plane, centred in X/Y
    above.Placement = App.Placement(App.Vector(0, 0, 0), bend)
    corner = bend.multVec(App.Vector(-BIG / 2, -BIG / 2, 0))
    for a_, comp in zip("xyz", (corner.x, corner.y, corner.z)):
        above.setExpression(f".Placement.Base.{a_}", f"{dist[a_]} + {comp:.6f} mm")
    body = ctx.cut(f"{name}_D", body, above)
    socks, _ = ctx.peg_pattern(f"{name}_Sockets", face, face_n, "socket")
    body = ctx.cut(f"{name}_S", body, socks)
    pegs, _ = ctx.peg_pattern(f"{name}_Pegs", face, face_n, "peg", rot=bend)
    if pegs is not None:
        for a_ in "xyz":
            pegs.setExpression(f".Placement.Base.{a_}", dist[a_])
    crest_feats = []
    if crest is not None:
        # gear crest: a toothed sector standing proud of the ball, lying in the coronal plane
        # (axis = crest["axis"], sector centred on crest["up"], both given in the ball's own frame)
        # sector from theta0 to theta1, degrees about ax measured from "up" (right-hand rule)
        th0, th1 = crest.get("theta0", -90.0), crest.get("theta1", 90.0)
        span = th1 - th0
        nt = crest.get("teeth") or max(3, int(round(span / crest.get("pitch", 15.0))))
        start = App.Rotation(ax, th0).multVec(up)                             # sector start direction
        ydir = ax.cross(start)
        rot = App.Rotation(App.Matrix(start.x, ydir.x, ax.x, 0, start.y, ydir.y, ax.y, 0, start.z, ydir.z, ax.z, 0, 0, 0, 0, 1))
        th_e = mul(r, 0.4)                                                    # crest thickness (axial)
        rg = mul(r, CREST_ROOT)                                               # crest root radius (proud of the ball)
        sec = ctx.cylinder(f"{name}_Crest", rg, th_e, rot=rot)
        sec.Angle = span
        for a_, comp in zip("xyz", (ax.x, ax.y, ax.z)):
            sec.setExpression(f".Placement.Base.{a_}", f"({c} * {1.0 if a_ == 'z' else 0.0} - {th_e} / 2 * {comp:.6f})")
        crest_feats.append(sec)
        # trapezoidal teeth (wide at the root, narrow at the tip), as many as fit at ~0.55 pitch root width
        pitch = span / nt
        arc = math.radians(pitch)
        for i in range(nt):
            ang = th0 + pitch * (i + 0.5)
            dv = App.Rotation(ax, ang).multVec(up)                             # radial
            tv = dv.cross(ax)                                                  # tangential; (tv, dv, ax) right-handed
            trot = App.Rotation(App.Matrix(tv.x, dv.x, ax.x, 0, tv.y, dv.y, ax.y, 0, tv.z, dv.z, ax.z, 0, 0, 0, 0, 1))
            tooth = ctx.obj("Part::Wedge", f"{name}_Tooth{i+1}")
            # local X tangential (width), Y radial (depth), Z axial (thickness); base at Y=0, tip at Y=depth
            tooth.setExpression("Xmin", f"(-{rg} * {arc * 0.30:.6f})"); tooth.setExpression("Xmax", f"({rg} * {arc * 0.30:.6f})")
            tooth.setExpression("X2min", f"(-{rg} * {arc * 0.17:.6f})"); tooth.setExpression("X2max", f"({rg} * {arc * 0.17:.6f})")
            tooth.setExpression("Zmin", f"(-{th_e} / 2)"); tooth.setExpression("Zmax", f"({th_e} / 2)")
            tooth.setExpression("Z2min", f"(-{th_e} / 2)"); tooth.setExpression("Z2max", f"({th_e} / 2)")
            tooth.Ymin = 0.0; tooth.setExpression("Ymax", mul(r, GEAR_TIP - 0.97 * CREST_ROOT))
            tooth.Placement = App.Placement(App.Vector(0, 0, 0), trot)
            for a_, dc, cz in zip("xyz", (dv.x, dv.y, dv.z), (0.0, 0.0, 1.0)):
                tooth.setExpression(f".Placement.Base.{a_}", f"({c} * {cz} + {rg} * 0.97 * {dc:.6f})")
            crest_feats.append(tooth)
    out = ctx.fuse(name, [body, pegs] + crest_feats)
    out.Label = name
    return [(name, out)]

# ============================================================== limbs
def _seg(ctx, name, L, D, prox_ball, dist_ball, **kw):
    """Strut between two balls; its length is the joint-centre distance minus both ball cup offsets."""
    cr = R("JointCupRatio"); co = R("JointCupOffset")
    length = f"({S(L)} - {S(prox_ball)} / 2 * {co} - {S(dist_ball)} / 2 * {co})"
    length_n = ctx.s(L) - ctx.s(prox_ball) / 2 * ctx.v["JointCupOffset"] - ctx.s(dist_ball) / 2 * ctx.v["JointCupOffset"]
    prox_face = mul(S(prox_ball), cr); prox_n = ctx.s(prox_ball) * ctx.v["JointCupRatio"]
    dist_face = mul(S(dist_ball), cr); dist_n = ctx.s(dist_ball) * ctx.v["JointCupRatio"]
    return segment(ctx, name, length, length_n, S(D), ctx.s(D), prox_face, prox_n, dist_face, dist_n, **kw)

def build_thigh(ctx):    return _seg(ctx, "Thigh", "ThighLength", "ThighDiameter", "HipBall", "KneeBall")
def build_shin(ctx):     return _seg(ctx, "Shin", "ShinLength", "ShinDiameter", "KneeBall", "AnkleBall")
def build_upperarm(ctx): return _seg(ctx, "UpperArm", "UpperArmLength", "UpperArmDiameter", "ShoulderBall", "ElbowBall")
def build_forearm(ctx):  return _seg(ctx, "Forearm", "ForearmLength", "ForearmDiameter", "ElbowBall", "WristBall")

def build_hipball_l(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "HipBallL", S("HipBall"), ctx.s("HipBall"), bend=ball_bend(ctx.v, "pelvis", -1))
def build_hipball_r(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "HipBallR", S("HipBall"), ctx.s("HipBall"), bend=ball_bend(ctx.v, "pelvis", 1))
def build_kneeball(ctx):
    return ball(ctx, "KneeBall", S("KneeBall"), ctx.s("KneeBall"), bend=App.Rotation(App.Vector(1, 0, 0), ctx.v["KneeBend"]))
def build_ankleball(ctx):
    return ball(ctx, "AnkleBall", S("AnkleBall"), ctx.s("AnkleBall"))
CREST_LEEWAY_DEG = 10.0     # gap between the socket flat and the first tooth (room for the joint to move)

def _shoulder_crest(ctx, sx):
    """Gear crest in the ball frame: lies in the coronal plane (axis = world Y) and runs from the edge of
    the socket (proximal) flat, plus leeway, over the top of the ball to the edge of the humerus (distal) flat."""
    from mimic_geom import yoke_side, ball_bend
    inv = yoke_side(ctx.v, "shoulder", sx)["rot"].inverted()
    ax = inv.multVec(App.Vector(0, 1, 0)); ax.normalize()
    up = inv.multVec(App.Vector(0, 0, 1)); up = up - ax * up.dot(ax); up.normalize()
    w = ax.cross(up)                                            # direction at theta = +90 deg
    co = ctx.v["JointCupOffset"]                                # flat sits at c = r * co from the centre

    def flat_edge(n):
        """Angle (deg from up, about ax) where the flat with outward normal n meets the crest plane,
        taking the intersection nearest the top of the ball."""
        A, B = up.dot(n), w.dot(n)
        m = math.hypot(A, B)
        base = math.degrees(math.atan2(B, A))
        half = math.degrees(math.acos(min(1.0, co / m)))
        cands = [base + half, base - half]
        return min(cands, key=lambda t: abs((t + 180) % 360 - 180))

    th_p = flat_edge(App.Vector(0, 0, -1))                      # socket flat (proximal, faces the yoke)
    th_d = flat_edge(ball_bend(ctx.v, "shoulder", sx).multVec(App.Vector(0, 0, 1)))   # humerus flat
    th_p = (th_p + 180) % 360 - 180; th_d = (th_d + 180) % 360 - 180
    if th_p < th_d:
        th0, th1 = th_p + CREST_LEEWAY_DEG, th_d
    else:
        th0, th1 = th_d, th_p - CREST_LEEWAY_DEG
    return {"axis": ax, "up": up, "theta0": th0, "theta1": th1}
def build_shoulderball_l(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "ShoulderBallL", S("ShoulderBall"), ctx.s("ShoulderBall"), bend=ball_bend(ctx.v, "shoulder", -1), crest=_shoulder_crest(ctx, -1))
def build_shoulderball_r(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "ShoulderBallR", S("ShoulderBall"), ctx.s("ShoulderBall"), bend=ball_bend(ctx.v, "shoulder", 1), crest=_shoulder_crest(ctx, 1))
def build_elbowball(ctx):
    return ball(ctx, "ElbowBall", S("ElbowBall"), ctx.s("ElbowBall"), bend=App.Rotation(App.Vector(1, 0, 0), -ctx.v["ElbowBend"]))
def build_wristball(ctx):
    return ball(ctx, "WristBall", S("WristBall"), ctx.s("WristBall"))

from mimic_parts_body import (build_foot, build_hand_l, build_hand_r, build_head, build_jaw, build_neck,
                              build_spine, build_shoulderyoke, build_pelvis, build_systembox)

BUILDERS = [
    ("SnapTest", build_snaptest),
    ("Head", build_head), ("Jaw", build_jaw), ("Neck", build_neck),
    ("ShoulderYoke", build_shoulderyoke), ("Spine", build_spine), ("SystemBox", build_systembox), ("Pelvis", build_pelvis),
    ("HipBallL", build_hipball_l), ("HipBallR", build_hipball_r), ("Thigh", build_thigh), ("KneeBall", build_kneeball),
    ("Shin", build_shin), ("AnkleBall", build_ankleball), ("Foot", build_foot),
    ("ShoulderBallL", build_shoulderball_l), ("ShoulderBallR", build_shoulderball_r), ("UpperArm", build_upperarm), ("ElbowBall", build_elbowball),
    ("Forearm", build_forearm), ("WristBall", build_wristball), ("HandL", build_hand_l), ("HandR", build_hand_r),
]
