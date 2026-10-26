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
# limb segment style "b" (two-part piston), all x the segment diameter D unless noted
PISTON_BARREL_R = 0.28   # the two thick "bones" (square piston barrels) at the proximal end: half side
PISTON_SPREAD = 0.32     # barrel / rod centres sit at +/- this on local X (side by side, radius/ulna)
PISTON_ROD_R = 0.14      # the thinner rods the barrels narrow to
PISTON_STROKE = 3 / 8    # the lateral barrel runs this fraction of the segment length before narrowing (1/3 read too short)
PISTON_INNER_STROKE = 1.15   # the medial barrel runs this much further (x the lateral stroke)
PISTON_NUT_AF = 0.34     # hex nut round each rod where it enters the crosshead: across flats ...
PISTON_NUT_H = 0.12      # ... and height
PISTON_GLAND = 0.15      # length of the taper from barrel to rod
PISTON_BLOCK_R = 0.62    # proximal block (ties the barrels to the cup): radius ...
PISTON_BLOCK_H = 0.25    # ... and height
PISTON_HEAD_R = 0.5      # distal crosshead (ties the rods to the distal cup): radius ...
PISTON_HEAD_H = 0.2      # ... and height
# limb segment style "c" (variegated pipe with rounded bumps), x the segment diameter D
BUMP_CORE_R = 0.36       # the pipe itself
BUMP_MAJOR_R = 0.32      # bump ring centreline radius (ring tube is centred here)
BUMP_MINOR_R = (0.18,)   # ring tube radii, cycled along the pipe (one size now: he liked the big ones)
BUMP_PITCH = 0.4         # spacing between rings

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
            rods=True, collar=True, extras=None, style="a", medial_sx=1, split_fit=False):
    """A strut from z=0 (proximal face, dia prox_face) to z=length (distal face, dia dist_face).
    `length` etc. are expression strings, `*_n` the scaled numeric values.  Splits itself to fit the build cube.
    style "a": one central strut with two thin rods and a collar.  style "c": a pipe with rounded
    ring bumps of alternating size (BUMP_* knobs).  style "b": a two-part piston --
    two thick barrels side by side from a proximal block, narrowing at PISTON_STROKE of the length
    to two rods that run into a distal crosshead (see the PISTON_* knobs); medial_sx says which
    barrel (local X sign) is the medial, longer one.

    `split_fit` sizes an internal split's joint to the material around it instead of keeping it
    modest, and lets the cut slide to a bump valley.  The limb bones use it.  The spine and the
    neck do not -- not because it would not suit them, but because the spine is printed already
    and a joint that changes size is a piece that no longer fits the ones beside it."""
    cup = "0.35"                                    # cup height as a fraction of face diameter
    prox_cup_h = mul(prox_face, cup)
    dist_cup_h = mul(dist_face, cup)
    bump = None                                     # style c's ring layout, for siting the splits
    feats = []
    feats.append(ctx.cone(f"{name}_ProxCup", half(prox_face), half(dia), prox_cup_h))
    feats.append(ctx.cone(f"{name}_DistCup", half(dia), half(dist_face), dist_cup_h,
                          z=sub(length, dist_cup_h)))
    if style == "b":
        rods = collar = False
        rb, rr = mul(dia, PISTON_BARREL_R), mul(dia, PISTON_ROD_R)
        side = mul(dia, 2 * PISTON_BARREL_R)
        gland_h = mul(dia, PISTON_GLAND)
        head_h = mul(dia, PISTON_HEAD_H)
        z_head = sub(sub(length, dist_cup_h), head_h)
        nut_h = mul(dia, PISTON_NUT_H)
        feats.append(ctx.cylinder(f"{name}_Block", mul(dia, PISTON_BLOCK_R), mul(dia, PISTON_BLOCK_H), z=prox_cup_h))
        feats.append(ctx.cylinder(f"{name}_Head", mul(dia, PISTON_HEAD_R), head_h, z=z_head))
        for i, sx in enumerate((-1, 1)):
            x = mul(dia, PISTON_SPREAD * sx)
            stroke = PISTON_STROKE * (PISTON_INNER_STROKE if sx == medial_sx else 1.0)
            z_gland = mul(length, stroke)                                     # this barrel ends here, tapers to its rod
            # square barrel, round gland and rod
            feats.append(ctx.box(f"{name}_Barrel{i+1}", side, side, sub(z_gland, prox_cup_h),
                                 x=sub(x, half(side)), y=neg(half(side)), z=prox_cup_h))
            feats.append(ctx.cone(f"{name}_Gland{i+1}", rb, rr, gland_h, x=x, z=z_gland))
            feats.append(ctx.cylinder(f"{name}_PistonRod{i+1}", rr, sub(add(z_head, head_h), z_gland), x=x, z=z_gland))
            # hex nut where the rod enters the crosshead (bolted-on look)
            nut = ctx.obj("Part::Prism", f"{name}_Nut{i+1}", Polygon=6)
            nut.setExpression("Circumradius", f"({mul(dia, PISTON_NUT_AF)} / 2 / cos(30 deg))")
            nut.setExpression("Height", nut_h)
            ctx.place(nut, x=x, z=sub(z_head, nut_h))
            feats.append(nut)
    elif style == "c":
        rods = collar = False
        feats.append(ctx.cylinder(f"{name}_Core", mul(dia, BUMP_CORE_R), length))
        span = sub(length, add(prox_cup_h, dist_cup_h))                     # rings between the cups
        span_n = length_n - (prox_face_n + dist_face_n) * float(cup)
        n_b = max(1, int(span_n / (dia_n * BUMP_PITCH)))
        # bumps sit at (i + 0.5) / n_b of the span, so the valleys between them are at k / n_b
        bump = dict(span=span, n=n_b, z0_n=prox_face_n * float(cup), pitch_n=span_n / n_b)
        for i in range(n_b):
            r_minor = BUMP_MINOR_R[i % len(BUMP_MINOR_R)]
            feats.append(ctx.torus(f"{name}_Bump{i+1}", mul(dia, BUMP_MAJOR_R), mul(dia, r_minor),
                                   z=add(prox_cup_h, mul(span, (i + 0.5) / n_b))))
    else:
        feats.append(ctx.cylinder(f"{name}_Strut", half(dia), length))
    if rods:
        rod_r = mul(dia, 0.15)
        rod_len = sub(length, add(prox_cup_h, dist_cup_h))
        for i, ang in enumerate((90, 270)):
            x = f"{mul(dia, 0.55)} * cos({ang} deg)"
            y = f"{mul(dia, 0.55)} * sin({ang} deg)"
            feats.append(ctx.cylinder(f"{name}_Rod{i+1}", rod_r, rod_len, x=x, y=y, z=prox_cup_h))
    if collar:
        feats.append(ctx.cylinder(f"{name}_Collar", mul(dia, 0.65), mul(length, 0.12), z=mul(length, 0.42)))
    # End spuds: the sockets are cut after the body is fused, and on a hollow strut (styles b and
    # c) a socket is wider than the core and simply cuts the end cup off.  The joint is sized by
    # the mating FACE and nothing else -- both halves have to come out the same size or they will
    # not mate, and the ball has no idea what strut it meets -- so the face is carried into the
    # part as a solid, deep enough to host the socket.
    #
    # Only as WIDE as the socket actually needs, though.  At the face diameter it stood a couple
    # of millimetres proud of the very cup it was meant to hide inside, on every limb -- a small
    # cuff of the same kind as the one at the splits.  At life size the strut's own diameter is
    # plenty, so the stub comes out flush with the end of the cup and disappears; only where the
    # socket is genuinely wider than the strut (the quarter-scale shin, where a 15 mm strut has to
    # host an 18 mm face's joint) does it fall back to the face.  A cone carrying the cup's taper
    # on would hide it at every scale, but at quarter scale it grazes the rods and the bumps at a
    # shallow angle and the mesh comes back with a ring of slivers.
    import mimic_joints
    pe = mimic_joints.envelope(prox_face_n)
    de = mimic_joints.envelope(dist_face_n)
    pr = half(prox_face) if pe[0] + mimic_joints.WALL > dia_n / 2 else half(dia)
    dr = half(dist_face) if de[0] + mimic_joints.WALL > dia_n / 2 else half(dia)
    feats.append(ctx.cylinder(f"{name}_SpudProx", pr, pe[1] + 1.0))
    feats.append(ctx.cylinder(f"{name}_SpudDist", dr, de[1] + 1.0,
                              z=sub(length, f"{de[1] + 1.0} mm")))

    # ---- splits -----------------------------------------------------------------------------
    # A bone longer than the build cube has to come apart, and the joint holding it together has
    # to live INSIDE whatever the style already puts on the centreline.  A cylinder at the
    # strut's full diameter used to be fused across every split to host it; on the two hollow
    # styles that is a smooth cuff interrupting the barrels or the bumps, which is the one thing
    # a split must not do -- the piece has to read as though it were never cut.  So:
    #   a  the strut is solid the whole way, so the bayonet goes straight into it; the split
    #      falls inside the decorative collar, which buries the seam as well.
    #   c  the pipe's core is solid, so the same bayonet, sized to fit the core; the split slides
    #      to the valley between two bumps, where the pipe is plain and the seam is a bare line.
    #   b  there is nothing on the axis at all -- at half length it is two piston rods and air --
    #      so each rod gets its own collet.  Two of them a rod-spacing apart key the halves
    #      against each other, which no single central joint could have done; and a collet goes
    #      in with a straight push, which is the only thing two parallel joints can agree on.
    #      (Two bayonets cannot: each would have to turn about its own axis.)
    if style == "b":
        core_n = None
        split_face_n = dia_n * 2 * PISTON_ROD_R                 # one piston rod
        split_env = mimic_joints.envelope(split_face_n, permanent=True, split=True)
    else:
        core_n = dia_n * 2 * BUMP_CORE_R if style == "c" else dia_n
        split_face_n = min(dia_n, core_n)
        split_env = mimic_joints.envelope(split_face_n, split=split_fit)
    # the printed piece is the segment plus whatever the male joint sticks out past its end
    prot = max(split_env[1], mimic_joints.envelope(dist_face_n)[1])
    n = split_count(length_n, ctx.v, prot)
    # how far a cut may be slid off the even spacing before a piece stops fitting the build cube
    slack = (ctx.v["BuildVolume"] - prot - 2.0) - length_n / max(n, 1)
    cuts = []                                                   # (expression, numeric) per split
    for i in range(1, n):
        z_expr, z_num = f"{length} * {i} / {n}", length_n * i / n
        if split_fit and style == "c" and bump is not None and bump["n"] > 1:
            even = z_num
            k = min(range(1, bump["n"]),
                    key=lambda j: abs(bump["z0_n"] + bump["pitch_n"] * j - even))
            z_valley = bump["z0_n"] + bump["pitch_n"] * k
            if abs(z_valley - even) <= slack:                   # otherwise leave it evenly spaced
                z_expr = add(prox_cup_h, mul(bump["span"], f"{k} / {bump['n']}"))
                z_num = z_valley
        cuts.append((z_expr, z_num))
    if cuts:
        where = (f"a collet in each {split_face_n:.0f} mm rod, "
                 f"{mimic_joints.describe(split_face_n, True, True)}" if style == "b" else
                 f"{mimic_joints.describe(split_face_n, split=split_fit)} in a "
                 f"{split_face_n:.0f} mm core")
        print(f"[mimic]   {name}: {n} pieces, split at "
              + ", ".join(f"{z:.0f}" for _e, z in cuts)
              + f" of {length_n:.0f} mm ({slack:.0f} mm to spare); " + where)

    def split_joints(tag, kind, idx):
        """The joint(s) at internal split `idx` (1-based): one in the core, or one per rod."""
        z_expr = cuts[idx - 1][0]
        out = []
        if style == "b":
            for j, sx in enumerate((-1, 1)):
                f, _ = ctx.joint_pattern(f"{name}_{tag}{j+1}", dia, split_face_n, kind, z=z_expr,
                                         x=mul(dia, PISTON_SPREAD * sx), permanent=True, split=True)
                out.append(f)
        else:
            f, _ = ctx.joint_pattern(f"{name}_{tag}", dia, dia_n, kind, z=z_expr,
                                     limit=core_n, split=split_fit)
            out.append(f)
        return [f for f in out if f is not None]

    def below(idx, tag):
        """Everything proximal of internal split `idx`, as a cutting tool."""
        return ctx.box(f"{name}_Below{idx}{tag}", BIG, BIG, BIG, x=-BIG / 2, y=-BIG / 2,
                       z=sub(cuts[idx - 1][0], f"{BIG} mm"))

    body = ctx.fuse(f"{name}_Body", feats + list(extras or []))
    pieces = []
    for i in range(n):
        piece = body
        if i < n - 1:
            piece = ctx.common(f"{name}_Cut{i+1}", piece, below(i + 1, "a"))
        if i > 0:
            piece = ctx.cut(f"{name}_Over{i+1}", piece, below(i, "b"))
        # proximal side: sockets (from the ball, or from the previous piece)
        if i == 0:
            socks, _ = ctx.joint_pattern(f"{name}_ProxSockets", prox_face, prox_face_n, "socket")
            piece = ctx.cut(f"{name}_S{i+1}", piece, socks)
        else:
            for j, s in enumerate(split_joints(f"SplitSockets{i}", "socket", i)):
                piece = ctx.cut(f"{name}_S{i+1}_{j+1}", piece, s)
        # distal side: pegs (into the ball, or into the next piece)
        if i == n - 1:
            pegs, _ = ctx.joint_pattern(f"{name}_DistPegs", dist_face, dist_face_n, "peg", z=length)
            add_on = [pegs] if pegs is not None else []
        else:
            add_on = split_joints(f"SplitPegs{i+1}", "peg", i + 1)
        piece = ctx.fuse(f"{name}{'' if n == 1 else i+1}", [piece] + add_on)
        piece.Label = f"{name}" if n == 1 else f"{name}-{i+1}of{n}"
        pieces.append((piece.Label, piece))
    return pieces

# ============================================================== generic ball joint
def ball(ctx, name, dia, dia_n, bend=ROT0, detail=True, crest=None, yoke_prox=False):
    """Sphere with two flat mating faces.  Proximal face at z=0 (sockets), distal face rotated by `bend`
    (pegs).  Face diameter = dia * JointCupRatio; centre sits JointCupOffset * r above the proximal face.

    yoke_prox cuts the PROXIMAL face further out instead -- where the sphere is as wide as the
    yoke's connector ring -- so the ball runs out to meet the ring instead of standing proud of it.
    The ball moves outboard by the difference; mimic_geom.cup_prox_frac is the one definition of it
    and mimic_assembly places the limb from the same number."""
    from mimic_geom import YOKE_DISC_FRAC, cup_prox_frac
    r = half(dia)
    co_d = R('JointCupOffset')
    co_p = (f"sqrt(1 - ({R('JointCupRatio')} * {YOKE_DISC_FRAC}) ^ 2)" if yoke_prox else co_d)
    c = f"({r} * {co_p})"                      # proximal face to centre
    cd = f"({r} * {co_d})"                     # centre to distal face
    face = mul(dia, R("JointCupRatio"))
    face_n = dia_n * ctx.v["JointCupRatio"]
    c_n = dia_n / 2 * (cup_prox_frac(ctx.v) if yoke_prox else ctx.v["JointCupOffset"])
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
    dist = {"x": f"({cd} * {d.x:.6f})", "y": f"({cd} * {d.y:.6f})", "z": f"({c} + {cd} * {d.z:.6f})"}
    above = ctx.box(f"{name}_DistTrim", BIG, BIG, BIG, rot=bend)
    # box origin is its corner: shift so its -Z face passes through the distal plane, centred in X/Y
    above.Placement = App.Placement(App.Vector(0, 0, 0), bend)
    corner = bend.multVec(App.Vector(-BIG / 2, -BIG / 2, 0))
    for a_, comp in zip("xyz", (corner.x, corner.y, corner.z)):
        above.setExpression(f".Placement.Base.{a_}", f"{dist[a_]} + {comp:.6f} mm")
    body = ctx.cut(f"{name}_D", body, above)
    socks, _ = ctx.joint_pattern(f"{name}_Sockets", face, face_n, "socket")
    body = ctx.cut(f"{name}_S", body, socks)
    pegs, _ = ctx.joint_pattern(f"{name}_Pegs", face, face_n, "peg", rot=bend)
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
    if crest_feats:
        # The crest is fused on AFTER the socket was cut and it overhangs the socket mouth, so it
        # refills the cavity: 2.4 cm3 of it sat inside the shoulder socket and the yoke's bayonet
        # had nowhere to go.  Re-cut the socket over the finished body.
        # fuse the sector and its teeth into one gear first: thrown at the body all at once, the
        # tooth/sector contacts are tangential enough that OCC returns an invalid shape (the right
        # shoulder started doing exactly that when the clavicle move changed the crest's angles)
        gear = ctx.fuse(f"{name}_Gear", crest_feats) if len(crest_feats) > 1 else crest_feats[0]
        whole = ctx.fuse(f"{name}_All", [body, pegs, gear])
        socks2, _ = ctx.joint_pattern(f"{name}_Sockets2", face, face_n, "socket")
        out = ctx.cut(name, whole, socks2) if socks2 is not None else whole
    else:
        out = ctx.fuse(name, [body, pegs])
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
    kw.setdefault("split_fit", True)      # every limb bone; the spine and neck keep what they have
    return segment(ctx, name, length, length_n, S(D), ctx.s(D), prox_face, prox_n, dist_face, dist_n, **kw)

def build_thigh(ctx):    return _seg(ctx, "Thigh", "ThighLength", "ThighDiameter", "HipBall", "KneeBall")
def build_shin(ctx):     return _seg(ctx, "Shin", "ShinLength", "ShinDiameter", "KneeBall", "AnkleBall")
def build_upperarm(ctx): return _seg(ctx, "UpperArm", "UpperArmLength", "UpperArmDiameter", "ShoulderBall", "ElbowBall")
def build_forearm(ctx):  return _seg(ctx, "Forearm", "ForearmLength", "ForearmDiameter", "ElbowBall", "WristBall")
# style B segments (sided files).  The limb frame keeps local Y forward, so local +X points to the
# midline on the right limbs and away from it on the left: medial_sx = +1 right, -1 left.
def build_forearm_r(ctx):  return _seg(ctx, "ForearmR", "ForearmLength", "ForearmDiameter", "ElbowBall", "WristBall", style="b", medial_sx=1)
def build_thigh_l(ctx):    return _seg(ctx, "ThighL", "ThighLength", "ThighDiameter", "HipBall", "KneeBall", style="b", medial_sx=-1)
def build_thigh_r(ctx):    return _seg(ctx, "ThighR", "ThighLength", "ThighDiameter", "HipBall", "KneeBall", style="c")
def build_upperarm_r(ctx): return _seg(ctx, "UpperArmR", "UpperArmLength", "UpperArmDiameter", "ShoulderBall", "ElbowBall", style="c")
def build_shin_l(ctx):     return _seg(ctx, "ShinL", "ShinLength", "ShinDiameter", "KneeBall", "AnkleBall", style="c")
def build_upperarm_l(ctx): return _seg(ctx, "UpperArmL", "UpperArmLength", "UpperArmDiameter", "ShoulderBall", "ElbowBall", style="b", medial_sx=-1)

def build_hipball_l(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "HipBallL", S("HipBall"), ctx.s("HipBall"), bend=ball_bend(ctx.v, "pelvis", -1), yoke_prox=True)
def build_hipball_r(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "HipBallR", S("HipBall"), ctx.s("HipBall"), bend=ball_bend(ctx.v, "pelvis", 1), yoke_prox=True)
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
    from mimic_geom import cup_prox_frac
    co = ctx.v["JointCupOffset"]                                # flat sits at c = r * co from the centre

    def flat_edge(n, co=co):
        """Angle (deg from up, about ax) where the flat with outward normal n meets the crest plane,
        taking the intersection nearest the top of the ball."""
        A, B = up.dot(n), w.dot(n)
        m = math.hypot(A, B)
        base = math.degrees(math.atan2(B, A))
        half = math.degrees(math.acos(min(1.0, co / m)))
        cands = [base + half, base - half]
        return min(cands, key=lambda t: abs((t + 180) % 360 - 180))

    # the socket flat is cut where the sphere matches the yoke's ring, further out than the rest
    th_p = flat_edge(App.Vector(0, 0, -1), cup_prox_frac(ctx.v))
    th_d = flat_edge(ball_bend(ctx.v, "shoulder", sx).multVec(App.Vector(0, 0, 1)))   # humerus flat
    th_p = (th_p + 180) % 360 - 180; th_d = (th_d + 180) % 360 - 180
    # Leeway at BOTH flats.  It used to be applied only at the socket end, which left the sector's
    # other radial face sitting exactly in the humerus flat's plane -- coplanar faces, and OCC
    # returned an invalid shape for the whole ball the moment the clavicle move nudged the angles.
    if th_p < th_d:
        th0, th1 = th_p + CREST_LEEWAY_DEG, th_d - CREST_LEEWAY_DEG
    else:
        th0, th1 = th_d + CREST_LEEWAY_DEG, th_p - CREST_LEEWAY_DEG
    return {"axis": ax, "up": up, "theta0": th0, "theta1": th1}
def build_shoulderball_l(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "ShoulderBallL", S("ShoulderBall"), ctx.s("ShoulderBall"), bend=ball_bend(ctx.v, "shoulder", -1), crest=_shoulder_crest(ctx, -1), yoke_prox=True)
def build_shoulderball_r(ctx):
    from mimic_geom import ball_bend
    return ball(ctx, "ShoulderBallR", S("ShoulderBall"), ctx.s("ShoulderBall"), bend=ball_bend(ctx.v, "shoulder", 1), crest=_shoulder_crest(ctx, 1), yoke_prox=True)
def build_elbowball(ctx):
    return ball(ctx, "ElbowBall", S("ElbowBall"), ctx.s("ElbowBall"), bend=App.Rotation(App.Vector(1, 0, 0), -ctx.v["ElbowBend"]))
def build_wristball(ctx):
    return ball(ctx, "WristBall", S("WristBall"), ctx.s("WristBall"))

from mimic_jointtest import build_jointtest
from mimic_parts_body import (build_foot, build_hand_l, build_hand_r, build_head, build_mouth, build_neck,
                              build_spine, build_shoulderyoke, build_hipharness, build_systembox, build_boxtool, build_eyedisk)

BUILDERS = [
    ("SnapTest", build_snaptest), ("JointTest", build_jointtest),
    ("Head", build_head), ("Mouth", build_mouth), ("Neck", build_neck),
    ("ShoulderYoke", build_shoulderyoke), ("Spine", build_spine), ("SystemBox", build_systembox), ("BoxTool", build_boxtool), ("EyeDisk", build_eyedisk), ("HipHarness", build_hipharness),
    ("HipBallL", build_hipball_l), ("HipBallR", build_hipball_r), ("Thigh", build_thigh), ("ThighL", build_thigh_l), ("ThighR", build_thigh_r), ("KneeBall", build_kneeball),
    ("Shin", build_shin), ("ShinL", build_shin_l), ("AnkleBall", build_ankleball), ("Foot", build_foot),
    ("ShoulderBallL", build_shoulderball_l), ("ShoulderBallR", build_shoulderball_r), ("UpperArm", build_upperarm), ("UpperArmL", build_upperarm_l), ("UpperArmR", build_upperarm_r), ("ElbowBall", build_elbowball),
    ("Forearm", build_forearm), ("ForearmR", build_forearm_r), ("WristBall", build_wristball), ("HandL", build_hand_l), ("HandR", build_hand_r),
]
