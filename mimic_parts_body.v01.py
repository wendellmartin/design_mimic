"""Body parts that are not plain struts or balls: foot, hand, head, jaw, pelvis, spine, chest."""
import math
import FreeCAD as App
from mimic_lib import R, S, half, mul, add, sub, neg, peg_count, split_count

ROT0 = App.Rotation()
BIG = 5000.0
ROT_PX = App.Rotation(App.Vector(0, 1, 0), 90)     # local +Z -> +X
ROT_NX = App.Rotation(App.Vector(0, 1, 0), -90)    # local +Z -> -X
ROT_NZ = App.Rotation(App.Vector(1, 0, 0), 180)    # local +Z -> -Z

def _face(ctx, ball):
    return mul(S(ball), R("JointCupRatio")), ctx.s(ball) * ctx.v["JointCupRatio"]

# ============================================================== foot
def build_foot(ctx):
    """Origin at the ankle face (top of foot).  Local +Z = down, toes along local +Y
    (the leg chain frame is a 180 deg turn about Y, so local +Y stays world +Y = forward)."""
    face, face_n = _face(ctx, "AnkleBall")
    H, L, W = S("FootHeight"), S("FootLength"), S("FootWidth")
    feats = []
    feats.append(ctx.cone("Foot_Cup", half(face), mul(S("ShinDiameter"), 0.45), mul(face, 0.35)))
    feats.append(ctx.cylinder("Foot_Shank", mul(S("ShinDiameter"), 0.45), mul(H, 0.8)))
    plate_h = mul(H, 0.25)
    # sole plate: heel behind (-Y local), toes ahead (+Y local)
    feats.append(ctx.box("Foot_Sole", W, L, plate_h, x=neg(half(W)), y=neg(mul(L, 0.28)), z=sub(H, plate_h)))
    # heel block
    feats.append(ctx.box("Foot_Heel", mul(W, 0.7), mul(L, 0.25), mul(H, 0.6),
                         x=neg(mul(W, 0.35)), y=neg(mul(L, 0.28)), z=mul(H, 0.4)))
    # three toe bars
    for i, fx in enumerate((-0.33, 0.0, 0.33)):
        feats.append(ctx.cylinder(f"Foot_Toe{i+1}", mul(W, 0.13), mul(L, 0.45),
                                  x=mul(W, fx), y=mul(L, 0.27), z=sub(H, mul(W, 0.13)),
                                  rot=App.Rotation(App.Vector(1, 0, 0), -90)))
    body = ctx.fuse("Foot_Body", feats)
    socks, _ = ctx.peg_pattern("Foot_Sockets", face, face_n, "socket")
    foot = ctx.cut("Foot", body, socks)
    foot.Label = "Foot"
    return [("Foot", foot)]

# ============================================================== hand
def build_hand_l(ctx): return _hand(ctx, "HandL", -1)
def build_hand_r(ctx): return _hand(ctx, "HandR", 1)

def _hand(ctx, name, tx):
    """Origin at the wrist face, fingers along local +Z, palm flat in the local XZ plane; thumb toward local tx*X."""
    face, face_n = _face(ctx, "WristBall")
    L, PW, FD = S("HandLength"), S("PalmWidth"), S("FingerDiameter")
    palm_len = mul(L, 0.42)
    feats = []
    feats.append(ctx.cone("Hand_Cup", half(face), mul(PW, 0.28), mul(face, 0.35)))
    feats.append(ctx.box("Hand_Palm", mul(PW, 0.85), mul(FD, 1.3), palm_len,
                         x=neg(mul(PW, 0.425)), y=neg(mul(FD, 0.65)), z=mul(face, 0.3)))
    fl = sub(L, palm_len)
    for i, fx in enumerate((-0.36, -0.12, 0.12, 0.36)):
        x = mul(PW, fx)
        flen = mul(fl, (0.9, 1.0, 0.95, 0.8)[i])
        feats.append(ctx.sphere(f"Hand_Knuckle{i+1}", mul(FD, 0.6), x=x, z=palm_len))
        feats.append(ctx.cylinder(f"Hand_Finger{i+1}", half(FD), flen, x=x, z=palm_len))
        feats.append(ctx.sphere(f"Hand_Tip{i+1}", half(FD), x=x, z=add(palm_len, flen)))
    # thumb: out to the side and forward, from mid palm
    thumb_rot = App.Rotation(App.Vector(0, 1, 0), 50 * tx)
    feats.append(ctx.sphere("Hand_ThumbKnuckle", mul(FD, 0.6), x=mul(PW, 0.42 * tx), z=mul(palm_len, 0.35)))
    feats.append(ctx.cylinder("Hand_Thumb", half(FD), mul(fl, 0.6), x=mul(PW, 0.42 * tx), z=mul(palm_len, 0.35), rot=thumb_rot))
    body = ctx.fuse("Hand_Body", feats)
    socks, _ = ctx.peg_pattern("Hand_Sockets", face, face_n, "socket")
    hand = ctx.cut(name, body, socks)
    hand.Label = name
    return [(name, hand)]

# ============================================================== head + jaw
def _head_frame(ctx):
    rz = half(sub(S("HeadHeight"), S("JawHeight")))
    z_flat = add(S("JawHeight"), mul(rz, 0.25))          # flat underside of the cranium
    z_c = add(S("JawHeight"), rz)                         # cranium centre
    return rz, z_flat, z_c

def build_head(ctx):
    """Origin at the neck face (bottom of the neck boss), +Z up, +Y = face direction."""
    rz, z_flat, z_c = _head_frame(ctx)
    HW, HD, ED = S("HeadWidth"), S("HeadDepth"), S("EyeDiameter")
    neck_face = mul(S("NeckDiameter"), 1.3); neck_face_n = ctx.s("NeckDiameter") * 1.3
    cranium = ctx.ellipsoid("Head_Cranium", rz, half(HW), half(HD), z=z_c)
    brow = ctx.ellipsoid("Head_Brow", mul(rz, 0.35), mul(HW, 0.5), mul(HD, 0.3), y=mul(HD, 0.22), z=add(z_c, mul(rz, 0.05)))
    boss = ctx.cylinder("Head_NeckBoss", half(neck_face), add(z_flat, mul(rz, 0.3)), y=neg(mul(HD, 0.08)))
    body = ctx.fuse("Head_Body", [cranium, brow, boss])
    # keep the neck boss: trim only above z=0 below z_flat outside the boss -> do it as ellipsoid-only trim
    trim = ctx.box("Head_FlatTrim", BIG, BIG, z_flat, x=-BIG / 2, y=-BIG / 2)
    keep = ctx.cylinder("Head_BossKeep", half(neck_face), z_flat, y=neg(mul(HD, 0.08)))
    trim = ctx.cut("Head_FlatTrimRing", trim, keep)
    body = ctx.cut("Head_Flat", body, trim)
    # eye sockets: bores along +Y through the front
    cuts = []
    for i, sx in enumerate((-0.5, 0.5)):
        x = mul(S("EyeSpacing"), sx)
        cuts.append(ctx.cylinder(f"Head_EyeBore{i+1}", half(ED), BIG, x=x, y=mul(HD, 0.12), z=add(z_c, mul(rz, 0.1)),
                                 rot=App.Rotation(App.Vector(1, 0, 0), -90)))
    body = ctx.cut("Head_Eyed", body, ctx.fuse("Head_EyeBores", cuts))
    eyes = []
    for i, sx in enumerate((-0.5, 0.5)):
        x = mul(S("EyeSpacing"), sx)
        eyes.append(ctx.sphere(f"Head_Eye{i+1}", mul(ED, 0.36), x=x, y=mul(HD, 0.2), z=add(z_c, mul(rz, 0.1))))
    body = ctx.fuse("Head_WithEyes", [body] + eyes)
    # sockets: neck pegs come up into the boss; jaw pegs come up into the flat underside
    socks, _ = ctx.peg_pattern("Head_NeckSockets", neck_face, neck_face_n, "socket")
    if socks is not None:
        socks.setExpression(".Placement.Base.y", neg(mul(HD, 0.08)))
    body = ctx.cut("Head_S1", body, socks)
    jaw_face, jaw_face_n = mul(HW, 0.3), ctx.s("HeadWidth") * 0.3
    jsocks, _ = ctx.peg_pattern("Head_JawSockets", jaw_face, jaw_face_n, "socket", z=z_flat)
    if jsocks is not None:
        jsocks.setExpression(".Placement.Base.y", mul(HD, 0.18))
    head = ctx.cut("Head", body, jsocks)
    head.Label = "Head"
    return [("Head", head)]

def build_jaw(ctx):
    """Origin at the jaw's mating face on the cranium underside; pegs point +Z (up), body hangs below."""
    HW, HD, JH = S("HeadWidth"), S("HeadDepth"), S("JawHeight")
    jaw_face, jaw_face_n = mul(HW, 0.3), ctx.s("HeadWidth") * 0.3
    feats = []
    feats.append(ctx.cylinder("Jaw_Pad", half(jaw_face), mul(JH, 0.25), z=neg(mul(JH, 0.25))))
    # hinge bar across the back of the jaw
    feats.append(ctx.cylinder("Jaw_Hinge", mul(JH, 0.22), mul(HW, 0.7), x=neg(mul(HW, 0.35)), y=0, z=neg(mul(JH, 0.4)),
                              rot=ROT_PX))
    # the U: half torus opening toward the back, hanging forward
    feats.append(ctx.torus("Jaw_U", mul(HW, 0.35), mul(JH, 0.28), angle3=180.0, z=neg(mul(JH, 0.7))))
    # chin plate under the U
    chin = ctx.cylinder("Jaw_Chin", mul(HW, 0.36), mul(JH, 0.12), z=neg(mul(JH, 0.98)))
    trim = ctx.box("Jaw_ChinTrim", BIG, BIG / 2, BIG, x=-BIG / 2, y=-BIG / 2, z=-BIG / 2)
    feats.append(ctx.cut("Jaw_ChinHalf", chin, trim))   # front half only
    body = ctx.fuse("Jaw_Body", feats)
    pegs, _ = ctx.peg_pattern("Jaw_Pegs", jaw_face, jaw_face_n, "peg")
    jaw = ctx.fuse("Jaw", [body, pegs])
    jaw.Label = "Jaw"
    return [("Jaw", jaw)]

# ============================================================== pelvis (root of the chain)
def build_pelvis(ctx):
    """Origin at the hip bar centre. +Z up, +Y forward.  Distal faces: top (spine), +/-X (hip balls)."""
    PH, PW, PD, SD = S("PelvisHeight"), S("PelvisWidth"), S("PelvisDepth"), S("SpineDiameter")
    bar_len = sub(PW, S("HipBall"))
    bar_len_n = ctx.s("PelvisWidth") - ctx.s("HipBall")
    hip_face, hip_face_n = _face(ctx, "HipBall")
    spine_face, spine_face_n = mul(SD, 1.2), ctx.s("SpineDiameter") * 1.2
    feats = []
    feats.append(ctx.cylinder("Pelvis_Bar", mul(PH, 0.3), bar_len, x=neg(half(bar_len)), rot=ROT_PX))
    feats.append(ctx.cylinder("Pelvis_Sacrum", half(spine_face), mul(PH, 0.8), z=neg(mul(PH, 0.3))))
    feats.append(ctx.box("Pelvis_Front", mul(PW, 0.45), mul(PD, 0.35), mul(PH, 0.45),
                         x=neg(mul(PW, 0.225)), y=mul(PD, 0.1), z=neg(mul(PH, 0.35))))
    # iliac wings
    for i, sx in enumerate((-1, 1)):
        feats.append(ctx.box(f"Pelvis_Wing{i+1}", mul(PD, 0.18), mul(PD, 0.7), mul(PH, 0.55),
                             x=mul(bar_len, 0.34 * sx - 0.09), y=neg(mul(PD, 0.35)), z=neg(mul(PH, 0.1))))
    body = ctx.fuse("Pelvis_Body", feats)
    pegs_top, _ = ctx.peg_pattern("Pelvis_SpinePegs", spine_face, spine_face_n, "peg", z=mul(PH, 0.5))
    pl, _ = ctx.peg_pattern("Pelvis_HipPegsL", hip_face, hip_face_n, "peg", rot=ROT_NX)
    pr, _ = ctx.peg_pattern("Pelvis_HipPegsR", hip_face, hip_face_n, "peg", rot=ROT_PX)
    if pl is not None:
        pl.setExpression(".Placement.Base.x", neg(half(bar_len)))
        pr.setExpression(".Placement.Base.x", half(bar_len))
    pelvis = ctx.fuse("Pelvis", [body, pegs_top, pl, pr])
    pelvis.Label = "Pelvis"
    return [("Pelvis", pelvis)]

# ============================================================== spine
def build_spine(ctx):
    from mimic_parts import segment
    SD = S("SpineDiameter"); sdn = ctx.s("SpineDiameter")
    return segment(ctx, "Spine", S("SpineGap"), ctx.s("SpineGap"), SD, sdn,
                   mul(SD, 1.2), sdn * 1.2, SD, sdn, collar=True)

# ============================================================== chest
def build_chest(ctx):
    """Origin at the bottom of the spine column (proximal face), +Z up, +Y forward.
    Spine column at the back, elliptical rib arcs to a sternum, clavicle bar at the top.
    Ribs/sternum/clavicle become separate snap pieces when the scaled rib is thick enough."""
    from mimic_parts import segment
    v = ctx.v
    CH, CW, CD, RD, SD = S("ChestHeight"), S("ChestWidth"), S("ChestDepth"), S("RibDiameter"), S("SpineDiameter")
    N = int(v["RibCount"])
    separate = ctx.s("RibDiameter") >= v["PegMinFace"]
    y_sp = neg(mul(sub(half(CD), half(SD)), 0.85))                 # spine axis y
    b = sub(half(CD), half(RD))                                     # rib half-depth (constant)
    a_full = sub(half(CW), half(RD))                                # rib half-width at the widest rib
    y_c = add(y_sp, b)                                              # ellipse centre y
    y_front = add(y_sp, mul(b, 2))                                  # sternum axis y
    st_w = mul(RD, 1.4)                                             # sternum width (box)
    neck_face, neck_face_n = mul(S("NeckDiameter"), 1.6 * v["JointCupRatio"]), ctx.s("NeckDiameter") * 1.6 * v["JointCupRatio"]
    sh_face, sh_face_n = _face(ctx, "ShoulderBall")
    clav_len = sub(S("ShoulderWidth"), S("ShoulderBall"))
    clav_len_n = ctx.s("ShoulderWidth") - ctx.s("ShoulderBall")

    pieces = []
    # ---- spine column: cylinder + box for flat flanks, top boss for the neck ball
    col = [ctx.cylinder("Chest_Column", half(SD), CH, y=y_sp),
           ctx.box("Chest_ColumnFlats", SD, mul(SD, 0.7), CH, x=neg(half(SD)), y=sub(y_sp, mul(SD, 0.35))),
           ctx.cylinder("Chest_NeckBoss", half(mul(neck_face, 1.15)), mul(SD, 0.4), y=y_sp, z=sub(CH, mul(SD, 0.4)))]
    # vertebra rings for texture
    for k in range(N + 1):
        col.append(ctx.cylinder(f"Chest_Vert{k+1}", mul(SD, 0.58), mul(CH, 0.04), y=y_sp,
                                z=mul(CH, 0.12 + 0.76 * (k - 0.5) / max(N - 1, 1))))
    column = ctx.fuse("Chest_ColumnBody", col)

    # ---- ribs
    ribs = []
    for k in range(N):
        s = 0.7 + 0.3 * math.sin(math.pi * (k + 0.5) / N)
        zf = 0.12 + 0.76 * k / max(N - 1, 1)
        for side, xs in (("L", -1), ("R", 1)):
            # same 90..270 arc for both sides; the right rib is the path spun 180 deg about its centre
            spin = ROT0 if xs < 0 else App.Rotation(App.Vector(0, 0, 1), 180)
            name = f"Rib{side}{k+1}"
            path = ctx.obj("Part::Ellipse", f"Chest_{name}_Path")
            path.setExpression("MajorRadius", mul(a_full, s))
            path.setExpression("MinorRadius", b)
            path.Angle1 = 90.0; path.Angle2 = 270.0
            path.Placement = App.Placement(App.Vector(0, 0, 0), spin)
            path.setExpression(".Placement.Base.y", y_c)
            path.setExpression(".Placement.Base.z", mul(CH, zf))
            prof = ctx.obj("Part::Circle", f"Chest_{name}_Profile")
            prof.setExpression("Radius", half(RD))
            prof.Placement = App.Placement(App.Vector(0, 0, 0), ROT_PX)
            prof.setExpression(".Placement.Base.y", add(y_c, mul(b, -xs)))
            prof.setExpression(".Placement.Base.z", mul(CH, zf))
            sw = ctx.obj("Part::Sweep", f"Chest_{name}_Sweep")
            sw.Sections = [prof]; sw.Spine = (path, ["Edge1"]); sw.Solid = True; sw.Frenet = True
            path.Visibility = False; prof.Visibility = False
            # trim both ends flat: back end at the column flank, front end at the sternum flank
            back = ctx.box(f"Chest_{name}_BackKeep", BIG, BIG, BIG, x=(-BIG if xs < 0 else 0), y=-BIG, z=-BIG / 2)
            back.setExpression(".Placement.Base.x", f"{-BIG if xs < 0 else 0} mm + {mul(half(SD), xs)}")
            back.setExpression(".Placement.Base.y", sub(y_c, BIG))
            front = ctx.box(f"Chest_{name}_FrontKeep", BIG, BIG, BIG, x=(-BIG if xs < 0 else 0), y=0, z=-BIG / 2)
            front.setExpression(".Placement.Base.x", f"{-BIG if xs < 0 else 0} mm + {mul(half(st_w), xs)}")
            front.setExpression(".Placement.Base.y", y_c)
            keep = ctx.fuse(f"Chest_{name}_Keep", [back, front])
            rib = ctx.common(f"Chest_{name}", sw, keep)
            ribs.append((name, rib, k, xs, zf, s))

    # ---- sternum (box) and clavicle
    st_z0 = mul(CH, 0.12 - 0.05); st_h = mul(CH, 0.76 + 0.1)
    sternum = ctx.box("Chest_Sternum", st_w, mul(RD, 1.2), st_h, x=neg(half(st_w)), y=sub(y_front, mul(RD, 0.6)), z=st_z0)
    clav_z = sub(CH, mul(SD, 0.45)); clav_y = add(y_sp, mul(b, 0.4)); post_r = mul(SD, 0.35); post_r_n = ctx.s("SpineDiameter") * 0.35
    clav = [ctx.cylinder("Chest_Clavicle", mul(SD, 0.32), clav_len, x=neg(half(clav_len)), y=clav_y, z=clav_z, rot=ROT_PX),
            ctx.cylinder("Chest_ClavBossL", half(sh_face), mul(S("ShoulderBall"), 0.5), x=neg(half(clav_len)), y=clav_y, z=clav_z, rot=ROT_PX),
            ctx.cylinder("Chest_ClavBossR", half(sh_face), mul(S("ShoulderBall"), 0.5), x=sub(half(clav_len), mul(S("ShoulderBall"), 0.5)), y=clav_y, z=clav_z, rot=ROT_PX)]
    clavicle = ctx.fuse("Chest_ClavicleBody", clav)
    post = ctx.box("Chest_ClavPost", mul(post_r, 2), mul(post_r, 2), mul(SD, 0.7), x=neg(post_r), y=sub(clav_y, post_r), z=sub(clav_z, mul(SD, 0.35)))
    column = ctx.fuse("Chest_ColumnPosted", [column, post])
    # shoulder pegs on the clavicle ends
    shl, _ = ctx.peg_pattern("Chest_ShoulderPegsL", sh_face, sh_face_n, "peg", rot=ROT_NX)
    shr, _ = ctx.peg_pattern("Chest_ShoulderPegsR", sh_face, sh_face_n, "peg", rot=ROT_PX)
    for p, sx in ((shl, -1), (shr, 1)):
        if p is not None:
            p.setExpression(".Placement.Base.x", mul(half(clav_len), sx))
            p.setExpression(".Placement.Base.y", clav_y)
            p.setExpression(".Placement.Base.z", clav_z)
    # neck ball pegs on top of the column, spine sockets at the bottom
    neck_pegs, _ = ctx.peg_pattern("Chest_NeckPegs", neck_face, neck_face_n, "peg", z=CH)
    if neck_pegs is not None:
        neck_pegs.setExpression(".Placement.Base.y", y_sp)
    spine_socks, _ = ctx.peg_pattern("Chest_SpineSockets", SD, ctx.s("SpineDiameter"), "socket")
    if spine_socks is not None:
        spine_socks.setExpression(".Placement.Base.y", y_sp)

    if not separate:
        allf = [column, sternum, clavicle, shl, shr, neck_pegs] + [r for _, r, *_ in ribs]
        body = ctx.fuse("Chest_Fused", allf)
        chest = ctx.cut("Chest", body, spine_socks)
        chest.Label = "Chest"
        return [("Chest", chest)]

    # ---- separate pieces with snap joints -------------------------------------------
    rib_face, rib_face_n = RD, ctx.s("RibDiameter")
    col_pegs, rib_socks_front = [], []
    for name, rib, k, xs, zf, s in ribs:
        z = mul(CH, zf)
        # back end: sockets in the rib, pegs on the column flank (pointing outward +/-X)
        rot_out = ROT_PX if xs > 0 else ROT_NX
        rs, _ = ctx.peg_pattern(f"Chest_{name}_BackSockets", rib_face, rib_face_n, "socket", rot=rot_out)
        rs.setExpression(".Placement.Base.x", mul(half(SD), xs)); rs.setExpression(".Placement.Base.y", y_sp); rs.setExpression(".Placement.Base.z", z)
        cp, _ = ctx.peg_pattern(f"Chest_{name}_ColumnPegs", rib_face, rib_face_n, "peg", rot=rot_out)
        cp.setExpression(".Placement.Base.x", mul(half(SD), xs)); cp.setExpression(".Placement.Base.y", y_sp); cp.setExpression(".Placement.Base.z", z)
        col_pegs.append(cp)
        # front end: pegs on the rib pointing inward, sockets in the sternum flank
        rot_in = ROT_NX if xs > 0 else ROT_PX
        yf = add(y_c, f"{b} * sqrt(1 - ({st_w} / (2 * {mul(a_full, s)})) ^ 2)")
        rp, _ = ctx.peg_pattern(f"Chest_{name}_FrontPegs", rib_face, rib_face_n, "peg", rot=rot_in)
        rp.setExpression(".Placement.Base.x", mul(half(st_w), xs)); rp.setExpression(".Placement.Base.y", yf); rp.setExpression(".Placement.Base.z", z)
        ss, _ = ctx.peg_pattern(f"Chest_{name}_SternumSockets", rib_face, rib_face_n, "socket", rot=rot_in)
        ss.setExpression(".Placement.Base.x", mul(half(st_w), xs)); ss.setExpression(".Placement.Base.y", yf); ss.setExpression(".Placement.Base.z", z)
        rib_socks_front.append(ss)
        piece = ctx.fuse(f"Chest_{name}_P", [ctx.cut(f"Chest_{name}_S", rib, rs), rp])
        piece.Label = f"Chest-{name}"
        pieces.append((piece.Label, piece))
    st = ctx.cut("Chest_SternumPiece", sternum, ctx.fuse("Chest_SternumSocketsAll", rib_socks_front))
    ns = split_count(ctx.s("ChestHeight") * 0.86, v)
    if ns == 1:
        st.Label = "Chest-Sternum"; pieces.append((st.Label, st))
    else:
        st_face, st_face_n = st_w, ctx.s("RibDiameter") * 1.4
        for i in range(ns):
            zs = f"({st_z0} + {st_h} * {i} / {ns})"
            slab = ctx.box(f"Chest_StSlab{i+1}", BIG, BIG, f"{st_h} / {ns}", x=-BIG / 2, y=-BIG / 2, z=zs)
            pc = ctx.common(f"Chest_St{i+1}", st, slab)
            if i > 0:
                s_, _ = ctx.peg_pattern(f"Chest_StSplitSockets{i}", st_face, st_face_n, "socket", z=zs)
                s_.setExpression(".Placement.Base.y", y_front)
                pc = ctx.cut(f"Chest_St{i+1}S", pc, s_)
            if i < ns - 1:
                p_, _ = ctx.peg_pattern(f"Chest_StSplitPegs{i+1}", st_face, st_face_n, "peg", z=f"({st_z0} + {st_h} * {i+1} / {ns})")
                p_.setExpression(".Placement.Base.y", y_front)
                pc = ctx.fuse(f"Chest_St{i+1}P", [pc, p_])
            pc.Label = f"Chest-Sternum-{i+1}of{ns}"; pieces.append((pc.Label, pc))
    # clavicle: two halves that peg into a post on the column top (split at x=0)
    clav_face, clav_face_n = mul(post_r, 1.8), post_r_n * 1.8
    for side, xs in (("L", -1), ("R", 1)):
        keep = ctx.box(f"Chest_Clav{side}Keep", BIG / 2, BIG, BIG, x=(-BIG / 2 if xs < 0 else 0), y=-BIG / 2, z=-BIG / 2)
        keep.setExpression(".Placement.Base.x", f"{-BIG / 2 if xs < 0 else 0} mm + {mul(post_r, xs)}")
        halfc = ctx.common(f"Chest_Clav{side}", clavicle, keep)
        rot_in = ROT_NX if xs < 0 else ROT_PX     # the post peg travels outward into this half
        cs, _ = ctx.peg_pattern(f"Chest_Clav{side}Sockets", clav_face, clav_face_n, "socket", rot=rot_in)
        cs.setExpression(".Placement.Base.x", mul(post_r, xs)); cs.setExpression(".Placement.Base.y", clav_y); cs.setExpression(".Placement.Base.z", clav_z)
        cpg, _ = ctx.peg_pattern(f"Chest_Clav{side}ColumnPegs", clav_face, clav_face_n, "peg", rot=rot_in)
        cpg.setExpression(".Placement.Base.x", mul(post_r, xs)); cpg.setExpression(".Placement.Base.y", clav_y); cpg.setExpression(".Placement.Base.z", clav_z)
        col_pegs.append(cpg)
        pc = ctx.fuse(f"Chest_Clav{side}Piece", [ctx.cut(f"Chest_Clav{side}S", halfc, cs), shl if xs < 0 else shr])
        pc.Label = f"Chest-Clavicle{side}"; pieces.append((pc.Label, pc))
    # the column carries every peg; split it along Z if needed
    column_full = ctx.fuse("Chest_ColumnAll", [column, neck_pegs] + col_pegs)
    column_full = ctx.cut("Chest_ColumnS", column_full, spine_socks)
    n = split_count(ctx.s("ChestHeight"), v)
    if n == 1:
        column_full.Label = "Chest-Column"; pieces.append((column_full.Label, column_full))
    else:
        for i in range(n):
            slab = ctx.box(f"Chest_ColSlab{i+1}", BIG, BIG, f"{CH} / {n}", x=-BIG / 2, y=-BIG / 2, z=f"{CH} * {i} / {n}")
            pc = ctx.common(f"Chest_Col{i+1}", column_full, slab)
            if i > 0:
                s_, _ = ctx.peg_pattern(f"Chest_ColSplitSockets{i}", SD, ctx.s("SpineDiameter"), "socket", z=f"{CH} * {i} / {n}")
                s_.setExpression(".Placement.Base.y", y_sp)
                pc = ctx.cut(f"Chest_Col{i+1}S", pc, s_)
            if i < n - 1:
                p_, _ = ctx.peg_pattern(f"Chest_ColSplitPegs{i+1}", SD, ctx.s("SpineDiameter"), "peg", z=f"{CH} * {i+1} / {n}")
                p_.setExpression(".Placement.Base.y", y_sp)
                pc = ctx.fuse(f"Chest_Col{i+1}P", [pc, p_])
            pc.Label = f"Chest-Column-{i+1}of{n}"; pieces.append((pc.Label, pc))
    return pieces
