"""Body parts that are not plain struts or balls: head, jaw, neck, spine, yokes, system box, hands, feet.

v0.2: open-cage head with captured eye spheres and a bar jaw; one continuous spine with a few
thick vertebrae; the same triangular yoke block at shoulders and hips; no ribs, a system box at
the heart; three-digit hands with a thumb; three-claw feet.
"""
import math
import FreeCAD as App
import Part
from mimic_lib import R, S, half, mul, add, sub, neg, peg_count, split_count

ROT0 = App.Rotation()
BIG = 5000.0
V = App.Vector
FOOT_HEEL = 0.3     # fraction of FootLength behind the ankle
FOOT_ANKLE_H = 0.66 # instep height at the ankle, fraction of the full sole-to-ankle-face height
TOE_REACH = 0.6     # toe length beyond the front face, fraction of FootLength
TOE_BLADE_W = 0.5   # toe width (x) at the root, fraction of ToeWidth
TOE_APEX = 0.4      # where the bottom edge peaks, fraction of the exposed toe length
TOE_RISE = 0.35     # how high the bottom edge arcs above the sole, fraction of FootHeight
TOE_FAN_DEG = 12.0  # outer toes splay this much
FOOT_FILLET = 0.06  # fillet radius on the foot's top edges, fraction of FootWidth
ROT_PX = App.Rotation(V(0, 1, 0), 90)     # local +Z -> +X
ROT_NX = App.Rotation(V(0, 1, 0), -90)    # local +Z -> -X
ROT_PY = App.Rotation(V(1, 0, 0), -90)    # local +Z -> +Y
ROT_XZ = App.Rotation(V(1, 0, 0), 90)     # ring in the XZ plane (normal Y)
ROT_YZ = App.Rotation(V(0, 1, 0), 90)     # ring in the YZ plane (normal X)

def _face(ctx, ball):
    return mul(S(ball), R("JointCupRatio")), ctx.s(ball) * ctx.v["JointCupRatio"]

def bar(ctx, name, radius, p0, p1, p0n, p1n):
    """Cylinder from p0 to p1.  p0/p1 are expression triples (positions stay parametric);
    p0n/p1n the scaled numeric points, used only for the rotation."""
    d = V(*p1n) - V(*p0n)
    rot = App.Rotation(V(0, 0, 1), d)
    length = f"sqrt(({p1[0]} - {p0[0]}) ^ 2 + ({p1[1]} - {p0[1]}) ^ 2 + ({p1[2]} - {p0[2]}) ^ 2)"
    return ctx.cylinder(name, radius, length, x=p0[0], y=p0[1], z=p0[2], rot=rot)

def beam(ctx, name, w, t, length, start, rot):
    """Box beam along its local +Y, cross-section w (x) by t (z), centred on the start point.
    `start` is an expression triple, `rot` numeric."""
    m = rot.toMatrix()
    def comp(i):
        return f"({start[i]} + {m.A[i*4+0]:.6f} * (-{w} / 2) + {m.A[i*4+2]:.6f} * (-{t} / 2))"
    return ctx.box(name, w, length, t, x=comp(0), y=comp(1), z=comp(2), rot=rot)

# ============================================================== head
HEAD_END_DEG = 160.0      # where the main head bar stops (C1 = 0, posterior over the back)
HEAD_EYE_DEG = 100.0      # eye level, same angular scale
HEAD_TAPER_DEG = 25.0     # the strap thins to the top-bar thickness over its last stretch
HEAD_CHEEK_ATTACH_DEG = 119.0   # cheek bar leaves the strap here (C1 = 0 scale); halfway from eye-bottom level to the top-bar split
HEAD_CHEEK_SIDE = 0.5           # how far out the cheek bar runs: fraction of the way from the eye centre to the head side
HEAD_CHEEK_DROP = 0.5           # front of the cheek bar sits this many eye radii below the eye bottom
HEAD_JAW_ATTACH_DEG = 40.0      # jaw bar leaves the strap edges here
HEAD_SOCKET_INNER = 0.97        # eye socket cup inner radius, in eye radii (just under 1 so it grips the ball)
HEAD_SOCKET_THICK = 1.6         # cup wall, in top-bar thicknesses
HEAD_SOCKET_RIM = 0.1           # socket bowl rim sits this many eye radii below the eye equator
HEAD_BOSS_DEG = 25.0            # screw boss sits this far below the equator
HEAD_BOSS_AZ = 45.0             # ...and this far round from the eye's outer side toward the back
HEAD_SOCKET_SPAN = 150.0        # socket wedge: degrees of azimuth from the medial side of the eye round the back (must reach the boss)
HEAD_CHEEK_CORNER = 0.5         # cheek bar turns the front corner this many eye radii behind the eye centre
HEAD_JAW_ANGLE = 45.0           # after the corner the cheek/jaw bars head inward-forward at this angle
HEAD_JAW_ROUND = 0.7            # front rounding bulge, as a fraction of the half eye spacing
DENTURE_INSET = 0.4             # lower denture platform sits this far inside the jaw bar (head radii)
DENTURE_FWD = 0.05              # its arms end this far forward of the jaw's corner
DENTURE_DROP = -0.08            # below the jaw bar (negative = above)
DENTURE_NOSE = 0.9              # front bulge beyond the arm ends, as a fraction of the half width
DENTURE_W = 1.6                 # platform width, in CageBar diameters
DENTURE_T = 0.5                 # platform thickness, in CageBar diameters
DENTURE_ROD = 0.2               # tie-rod radius, in CageBar diameters (under half the platform thickness)
DENTURE_LIP = 0.2               # lip width and height on the platform's outer and back edges, in CageBar diameters
HEAD_GUM_HEIGHT = 0.12          # denture platforms: band height (head radii)
HEAD_GUM_THICK = 0.06           # ...and thickness
HEAD_PUPIL = 0.14               # pupil dimple radius, in eye diameters
HEAD_PUPIL_DEPTH = 0.05         # ...and depth

def _head_geom(ctx):
    """Head sphere of radius R centred at z_c; C1 (neck junction) is the bottom pole.
    Angles run from C1 (0) posteriorly up the back (90 = back at centre height)."""
    Rc = S("HeadCageRadius"); Rn = ctx.s("HeadCageRadius")
    boss_h = mul(S("NeckDiameter"), 0.4); boss_hn = ctx.s("NeckDiameter") * 0.4
    # the strap (HeadBar/2 thick) starts with its outer face flush with the top of the neck boss (C1)
    z_c = add(Rc, sub(boss_h, mul(S("HeadBar"), 0.25))); z_cn = Rn + boss_hn - ctx.s("HeadBar") * 0.25
    eye_lat = HEAD_EYE_DEG - 90                                  # eye level above centre, deg
    ring_k = math.cos(math.radians(eye_lat))                      # eye-ring radius / R
    z_e = add(z_c, mul(Rc, math.sin(math.radians(eye_lat))))
    eye_az = math.degrees(math.asin(ctx.s("EyeSpacing") / 2 / (Rn * ring_k)))   # eye azimuth from +Y
    return Rc, Rn, z_c, z_cn, z_e, ring_k, eye_lat, eye_az, boss_h

def _unit_pt(ctx, Rc, z_c, p):
    """Unit-sphere point (relative to the centre) -> expression triple."""
    return (mul(Rc, p.x), mul(Rc, p.y), add(z_c, mul(Rc, p.z)))

def _section(ctx, name, Rc, z_c, P, w, n, W, T):
    """Rectangular loft section (W along unit vector w, T along unit vector n) centred at the
    unit-sphere point P.  Positions scale with the head radius; orientation is numeric."""
    d = w.cross(n)
    rot = App.Rotation(App.Matrix(w.x, n.x, d.x, 0, w.y, n.y, d.y, 0, w.z, n.z, d.z, 0, 0, 0, 0, 1))
    pl = ctx.obj("Part::Plane", name)
    pl.setExpression("Length", W); pl.setExpression("Width", T)
    pl.Placement = App.Placement(V(0, 0, 0), rot)
    c = _unit_pt(ctx, Rc, z_c, P)
    for ax, i in zip("xyz", range(3)):
        pl.setExpression(f".Placement.Base.{ax}", f"({c[i]} - {w[i]:.6f} * {W} / 2 - {n[i]:.6f} * {T} / 2)")
    pl.Visibility = False
    return pl

def _arc_bar(ctx, name, Rc, z_c, E, t, Q, minor):
    """Round bar along the circular arc that leaves E tangent to t and ends at Q (unit-sphere
    coordinates relative to the head centre).  Built as a partial torus."""
    d = Q - E
    n = d - t * d.dot(t); n.normalize()                 # in-plane normal at E, toward Q
    r = d.Length ** 2 / (2 * d.dot(n))
    C = E + n * r
    m = t.cross(n); m.normalize()                       # plane normal
    e_dir = (E - C); e_dir.normalize()
    q_dir = (Q - C); q_dir.normalize()
    sweep = math.degrees(math.acos(max(-1.0, min(1.0, e_dir.dot(q_dir)))))
    if e_dir.cross(q_dir).dot(m) < 0:
        m = -m                                          # sweep counter-clockwise about m
    y_dir = m.cross(e_dir)
    rot = App.Rotation(App.Matrix(e_dir.x, y_dir.x, m.x, 0, e_dir.y, y_dir.y, m.y, 0, e_dir.z, y_dir.z, m.z, 0, 0, 0, 0, 1))
    cx, cy, cz = _unit_pt(ctx, Rc, z_c, C)
    return ctx.torus(name, mul(Rc, r), minor, angle3=sweep, x=cx, y=cy, z=cz, rot=rot)

def build_head(ctx):
    """Origin at the neck face (C1), +Z up, +Y = face direction.
    The spine flattens into a strap that curves posterior from C1, up the back, and stops at
    HEAD_END_DEG.  From that end two smaller round bars continue tangentially, arch over and come
    down to meet the eye bars flush, a quarter of the way round from the back.  At eye level two
    small bars leave the back of the strap, run round the sides and curve anterior into the eyeballs."""
    Rc, Rn, z_c, z_cn, z_e, ring_k, eye_lat, eye_az, boss_h = _head_geom(ctx)
    HBw = S("HeadBar"); HBt = half(S("HeadBar")); CB = half(S("CageBar")); ED = S("EyeDiameter")
    neck_face = mul(S("NeckDiameter"), 1.3); neck_face_n = ctx.s("NeckDiameter") * 1.3
    f = []
    f.append(ctx.cylinder("Head_NeckBoss", half(neck_face), boss_h))
    # main strap: a HeadBar x HeadBar/2 rectangle at the bottom pole, revolved posteriorly about X
    # for all but the last HEAD_TAPER_DEG, then lofted down to the top-bar width
    TW = f"(({S('CageBar')} / 2 + {S('HeadBar')}) / 2)"                # top-bar ribbon width
    TT = half(S("CageBar"))                                            # top-bar ribbon thickness
    rect = ctx.obj("Part::Plane", "Head_StrapSection")
    rect.setExpression("Length", HBw); rect.setExpression("Width", HBt)
    rect.Placement = App.Placement(V(0, 0, 0), App.Rotation(V(1, 0, 0), 90))       # lies in XZ
    rect.setExpression(".Placement.Base.x", neg(half(HBw)))
    rect.setExpression(".Placement.Base.z", sub(sub(z_c, Rc), half(HBt)))
    rect.Visibility = False
    strap = ctx.obj("Part::Revolution", "Head_Strap")
    strap.Source = rect; strap.Axis = V(-1, 0, 0); strap.Angle = HEAD_END_DEG - HEAD_TAPER_DEG; strap.Solid = True
    strap.setExpression(".Base.z", z_c)
    f.append(strap)
    # taper: full width, thickness HeadBar/2 -> top-bar thickness, lofted along the arc from
    # HEAD_TAPER_DEG before the top bar's centreline to the top bar's leading edge (half its width
    # further round), where the strap ends flush with the ribbon
    TWn = (ctx.s("CageBar") / 2 + ctx.s("HeadBar")) / 2
    ext_deg = 0.0                                   # the ribbons continue forward from the strap end
    secs = []
    for i in range(5):
        fr = i / 4
        th = math.radians(HEAD_END_DEG - HEAD_TAPER_DEG + (HEAD_TAPER_DEG + ext_deg) * fr)
        P = V(0, -math.sin(th), -math.cos(th))                # unit point on the strap centreline
        rhat = P                                              # outward radial = thickness direction
        t_e = f"({HBt} * {1 - fr:.4f} + {TT} * {fr:.4f})"
        secs.append(_section(ctx, f"Head_TaperSec{i+1}", Rc, z_c, P, V(1, 0, 0), rhat, HBw, t_e))
    taper = ctx.obj("Part::Loft", "Head_StrapTaper")
    taper.Sections = secs; taper.Solid = True; taper.Ruled = False; taper.Closed = False
    f.append(taper)
    # end of the strap and its tangent (unit sphere, angles from the bottom pole going posterior)
    a = math.radians(HEAD_END_DEG)
    E = V(0, -math.sin(a), -math.cos(a))
    t = V(0, -math.cos(a), math.sin(a))
    ze_u = math.sin(math.radians(eye_lat))
    z_en = z_cn + Rn * ze_u
    # (eye bars are built after the top bars, which fix where the arc ends)
    # top bars: flat ribbons lofted through oriented sections.  They start in the plane of the
    # strap end (flush with it), run out horizontally, arc straight down onto the eye bar, and
    # twist along the way so the width ends up along the eye bar's tangent (thickness radial).
    # (At this width a flat end sits within 0.3 mm of the eye bar's curve, so no curved section.)
    # Q = where the eye bar's arc ends and its straight spoke to the eye begins (HEAD_CROSS_DEG from the back)
    cross = math.radians(45.0)                                         # (legacy; unused by the new bars)
    xq, yq = ring_k * math.sin(cross), -ring_k * math.cos(cross)     # unit-sphere Q (right side)
    # Top bars: the strap's end splits into two ribbons side by side.  Each continues forward over
    # the crown to the outer edge of its eye, wraps down round the outside and under the eyeball,
    # and runs inward to meet its twin at the bridge of the (absent) nose.  Built as piecewise
    # cubic Hermite curves through waypoints, lofted through oriented sections; the thickness
    # direction follows the head sphere over the crown and the eyeball round the eye.
    eyeR = ctx.s("EyeDiameter") / 2 / Rn
    TTn = ctx.s("CageBar") / 2 / Rn
    ex = ctx.s("EyeSpacing") / 2 / Rn
    ey = ring_k * math.cos(math.radians(eye_az)) + ctx.s("EyeDiameter") * 0.1 / Rn
    for k, sx in enumerate((-1, 1)):
        Ec = V(ex * sx, ey, ze_u)                                      # eyeball centre
        off = TWn / 2 / Rn                                             # ribbons sit edge to edge across the strap end
        crown_az = math.atan2(ex + eyeR, ey)                           # azimuth of the eye's outer edge
        ba = math.radians(HEAD_BOSS_DEG)
        bz_ = math.radians(HEAD_BOSS_AZ)
        boss_dir = V(math.cos(ba) * math.cos(bz_) * sx, -math.cos(ba) * math.sin(bz_), -math.sin(ba))   # radial at the boss: posterior-lateral, below the equator
        boss_tan = V(-math.sin(ba) * math.cos(bz_) * sx, math.sin(ba) * math.sin(bz_), -math.cos(ba))    # sphere tangent there, heading down
        P1 = V(math.sin(crown_az) * math.cos(math.radians(45)) * sx, math.cos(crown_az) * math.cos(math.radians(45)), math.sin(math.radians(45)))
        way = [  # (point, unit tangent, thickness direction)
            (V(off * sx, E.y, E.z), V(0, t.y, t.z), V(0, E.y, E.z)),
            (P1, V(math.sin(crown_az) * sx * 0.3, math.cos(crown_az) * 0.3, -0.95), P1),
            # ...and flows into the eye socket cup at the eye's outer edge, mid-shell
            # ...and ends inside the screw boss on the socket's outer side, HEAD_BOSS_DEG below the equator
            (Ec + boss_dir * (eyeR * HEAD_SOCKET_INNER + TTn * (HEAD_SOCKET_THICK + 1.0)), boss_tan, boss_dir),
        ]
        for w_ in way:
            w_[1].normalize(); w_[2].normalize()
        prev_sec = None
        for seg in range(len(way) - 1):
            Pa, ta, na = way[seg]; Pb, tb, nb = way[seg + 1]
            L = (Pb - Pa).Length
            m0, m1 = ta * L, tb * L
            secs = []
            s_list = [0.0, 0.25, 0.5, 0.75, 1.0]
            for i, s in enumerate(s_list):
                h00 = 2*s**3 - 3*s**2 + 1; h10 = s**3 - 2*s**2 + s; h01 = -2*s**3 + 3*s**2; h11 = s**3 - s**2
                d00 = 6*s**2 - 6*s; d10 = 3*s**2 - 4*s + 1; d01 = -6*s**2 + 6*s; d11 = 3*s**2 - 2*s
                P = Pa * h00 + m0 * h10 + Pb * h01 + m1 * h11
                d = Pa * d00 + m0 * d10 + Pb * d01 + m1 * d11; d.normalize()
                fr = max(min(s, 1.0), 0.0)
                n = na * (1 - fr) + nb * fr
                n = n - d * n.dot(d); n.normalize()                    # thickness perpendicular to the path
                w = n.cross(d); w.normalize()
                secs.append(_section(ctx, f"Head_TopSec{k+1}_{seg+1}_{i+1}", Rc, z_c, P, w, n, TW, TT))
            loft = ctx.obj("Part::Loft", f"Head_TopBar{k+1}_{seg+1}")
            loft.Sections = secs; loft.Solid = True; loft.Ruled = False; loft.Closed = False
            f.append(loft)
    f_frame = f; f = []                     # group 1 done: strap + ribbons
    # eye sockets: a spherical cup round each eyeball (overlapping it by HEAD_SOCKET_INNER), with the
    # front-upper quadrant cut away so the eye looks out; the top-bar ribbon flows into its rim
    SKIP = __import__("os").environ.get("MIMIC_HEAD_SKIP", "")
    for k, sx in (() if "socket" in SKIP else enumerate((-1, 1))):
        exe = mul(S("EyeSpacing"), 0.5 * sx)
        eye_y = add(mul(Rc, ring_k * math.cos(math.radians(eye_az))), mul(ED, 0.1))
        r_in = mul(ED, 0.5 * HEAD_SOCKET_INNER)
        r_out = add(r_in, mul(TT, HEAD_SOCKET_THICK))
        outer = ctx.sphere(f"Head_SocketOuter{k+1}", r_out, x=exe, y=eye_y, z=z_e)
        inner = ctx.sphere(f"Head_SocketInner{k+1}", r_in, x=exe, y=eye_y, z=z_e)
        shell = ctx.cut(f"Head_SocketShell{k+1}", outer, inner)
        # bowl: keep only what lies below HEAD_SOCKET_RIM (in eye radii) under the eye's equator
        window = ctx.box(f"Head_SocketWindow{k+1}", BIG, BIG, BIG, x=-BIG / 2, y=-BIG / 2, z=sub(z_e, mul(ED, 0.5 * HEAD_SOCKET_RIM)))
        bowl = ctx.cut(f"Head_SocketBowl{k+1}", shell, window)
        # keep only a HEAD_SOCKET_SPAN wedge of the bowl centred on the back of the eye
        # the sector starts at the medial side of the eye (toward the other eye) and sweeps round the back
        start_az = 180.0 if sx > 0 else 360.0 - HEAD_SOCKET_SPAN
        sector = ctx.cylinder(f"Head_SocketSector{k+1}", BIG / 4, BIG, x=exe, y=eye_y, z=sub(z_e, BIG / 2),
                              rot=App.Rotation(V(0, 0, 1), start_az))
        sector.Angle = HEAD_SOCKET_SPAN
        f.append(ctx.common(f"Head_Socket{k+1}", bowl, sector))
        # screw boss: a round collar on the socket's outer side, its axis radial to the eye, that the
        # top bar terminates in; two rings round it read as the thread
        ba = math.radians(HEAD_BOSS_DEG)
        bz_ = math.radians(HEAD_BOSS_AZ)
        bdir = V(math.cos(ba) * math.cos(bz_) * sx, -math.cos(ba) * math.sin(bz_), -math.sin(ba))
        r_boss_start = f"({r_in} + {TT} * {HEAD_SOCKET_THICK - 0.4})"
        b_len = mul(TT, 2.4)
        bx = f"({exe} + {r_boss_start} * {bdir.x:.6f})"; by = f"({eye_y} + {r_boss_start} * {bdir.y:.6f})"; bz = f"({z_e} + {r_boss_start} * {bdir.z:.6f})"
        boss = ctx.cylinder(f"Head_Boss{k+1}", mul(TW, 0.45), b_len, x=bx, y=by, z=bz, rot=App.Rotation(V(0, 0, 1), bdir))
        f.append(boss)
        for j, fr in enumerate((0.35, 0.7)):
            f.append(ctx.torus(f"Head_BossRing{k+1}_{j+1}", mul(TW, 0.45), mul(TT, 0.35),
                               x=f"({bx} + {b_len} * {fr} * {bdir.x:.6f})", y=f"({by} + {b_len} * {fr} * {bdir.y:.6f})", z=f"({bz} + {b_len} * {fr} * {bdir.z:.6f})",
                               rot=App.Rotation(V(0, 0, 1), bdir)))
    f_eyes = f; f = []                      # group 2: sockets + bosses (eyeballs join this group below)
    # ---- cheek bars and jaw bars: round tubes swept along smooth splines --------------------
    CBn = ctx.s("CageBar") / 2 / Rn
    SPINE_STEP = 0.1                                            # target point spacing along tube spines (head radii)

    def hermite(Pa, ta, Pb, tb, n=None, ka=1.0, kb=1.0):
        """Points along a cubic Hermite from Pa (unit tangent ta) to Pb (unit tangent tb); ka/kb scale
        the tangents.  n defaults to ~one point per SPINE_STEP of chord so spacing stays even."""
        L = (Pb - Pa).Length
        if n is None:
            n = max(3, int(round(L * 1.3 / SPINE_STEP)) + 1)
        m0, m1 = ta * L * ka, tb * L * kb
        out = []
        for i in range(n):
            s = i / (n - 1)
            h00 = 2*s**3 - 3*s**2 + 1; h10 = s**3 - 2*s**2 + s; h01 = -2*s**3 + 3*s**2; h11 = s**3 - s**2
            out.append(Pa * h00 + m0 * h10 + Pb * h01 + m1 * h11)
        return out

    def tube(name, pts_unit, radius_expr, frenet=True):
        """Round tube along a B-spline through unit-sphere points (scaled numerically), as a Part::Sweep.
        The spine is static geometry (scaled at build time); the profile radius stays an expression."""
        # resample the polyline at even spacing first: uneven spacing makes the interpolating spline wiggle
        raw = [V(p.x * Rn, p.y * Rn, z_cn + p.z * Rn) for p in pts_unit]
        step = 1e9      # resampling disabled: the raw points are already evenly spaced; a resampled spline exploded the sweep
        pts = [raw[0]]; carry = 0.0
        for a, b in (zip(raw[:-1], raw[1:]) if step < 1e8 else ()):
            seg = b - a; L = seg.Length
            if L < 1e-9:
                continue
            dpos = step - carry
            while dpos <= L:
                pts.append(a + seg * (dpos / L)); dpos += step
            carry = L - (dpos - step)
        if step >= 1e8:
            pts = list(raw)
        elif (pts[-1] - raw[-1]).Length > step * 0.3:
            pts.append(raw[-1])
        else:
            pts[-1] = raw[-1]
        dedup = [pts[0]]
        for p in pts[1:]:
            if (p - dedup[-1]).Length > 1e-4 * Rn:
                dedup.append(p)
        pts = dedup
        if len(pts) < 3:
            raise RuntimeError(f"{name}: only {len(pts)} distinct spine points from {len(pts_unit)} (raw {[ (round(p.x,3), round(p.y,3), round(p.z,3)) for p in pts_unit][:6]})")
        bs = Part.BSplineCurve(); bs.interpolate(pts)
        spine = ctx.obj("Part::Feature", f"{name}_Spine")
        spine.Shape = Part.Wire(bs.toShape()); spine.Visibility = False
        d = bs.tangent(bs.FirstParameter)[0]
        prof = ctx.obj("Part::Circle", f"{name}_Profile")
        prof.setExpression("Radius", radius_expr)
        prof.Placement = App.Placement(pts[0], App.Rotation(V(0, 0, 1), d)); prof.Visibility = False
        sw = ctx.obj("Part::Sweep", name)
        sw.Sections = [prof]; sw.Spine = (spine, ["Edge1"]); sw.Solid = True; sw.Frenet = frenet
        return sw

    def flat_tube(name, pts_unit, w_n, t_n, lip=None):
        """Rectangular-section sweep (w wide, t tall, kept level) along a B-spline through unit-sphere points.
        lip=(lw, lh) adds a lip of that width/height along the top outer edge (left of travel): an L section."""
        pts = [V(p.x * Rn, p.y * Rn, z_cn + p.z * Rn) for p in pts_unit]
        bs = Part.BSplineCurve(); bs.interpolate(pts)
        spine = ctx.obj("Part::Feature", f"{name}_Spine")
        spine.Shape = Part.Wire(bs.toShape()); spine.Visibility = False
        d = bs.tangent(bs.FirstParameter)[0]
        e1 = V(0, 0, 1).cross(d); e1.normalize()
        e2 = d.cross(e1); e2.normalize()
        P0 = pts[0]
        # e1 = outside (left of travel), e2 = up; walk the section anticlockwise from the outer-top corner
        sec = [(w_n / 2, t_n / 2)] if lip is None else [(w_n / 2, t_n / 2 + lip[1]), (w_n / 2 - lip[0], t_n / 2 + lip[1]),
                                                        (w_n / 2 - lip[0], t_n / 2)]
        sec += [(-w_n / 2, t_n / 2), (-w_n / 2, -t_n / 2), (w_n / 2, -t_n / 2), sec[0]]
        rect = Part.makePolygon([P0 + e1 * a + e2 * b for a, b in sec])
        prof = ctx.obj("Part::Feature", f"{name}_Profile")
        prof.Shape = rect; prof.Visibility = False
        sw = ctx.obj("Part::Sweep", name)
        sw.Sections = [prof]; sw.Spine = (spine, ["Edge1"]); sw.Solid = True; sw.Frenet = False
        return sw

    def rod(name, A, B, r_expr, ext_a, ext_b=0.0):
        """Cylinder from A to B (numeric, mm), extended ext_a / ext_b past each end to bury into the bodies."""
        d = B - A; L = d.Length; d.normalize()
        A2 = A - d * ext_a
        return ctx.cylinder(name, r_expr, L + ext_a + ext_b, x=A2.x, y=A2.y, z=A2.z, rot=App.Rotation(V(0, 0, 1), d))

    # cheek bar: leaves the strap at HEAD_CHEEK_ATTACH_DEG, arcs round to x = HEAD_CHEEK_SIDE
    # (fraction of the way from the eye centre to the head's side), runs straight forward to the
    # back of the eyeball, then sweeps slowly inward to meet its twin on the centreline.  Its height
    # falls steadily from the attachment to the front point, which sits HEAD_CHEEK_DROP below the
    # eye's bottom.
    th = math.radians(HEAD_CHEEK_ATTACH_DEG)
    S_pt = V(0, -math.sin(th), -math.cos(th))
    x_side = ex + (math.sqrt(1 - S_pt.z ** 2) - ex) * HEAD_CHEEK_SIDE
    y_post = ey - eyeR * HEAD_CHEEK_CORNER              # the front corner
    # front of the cheek/jaw: a short sweep at the corner turning to HEAD_JAW_ANGLE, a straight
    # run at that angle until between the eyes, then a rounding to horizontal at the centre
    def jaw_front_side(z, sx, xs=None, yp=None, xt=None):
        ja = math.radians(HEAD_JAW_ANGLE)
        d45 = V(-sx * math.sin(ja), math.cos(ja), 0)
        sw = 0.25                                                   # length of the initial sweep (head radii); too tight a bend self-intersects the tube
        xs = x_side if xs is None else xs
        yp = y_post if yp is None else yp
        C = V(xs * sx, yp, z)
        C2 = C + V(-sx * sw * math.sin(ja) * 0.7, sw * 0.9, 0)        # end of the sweep, heading at the angle
        out = hermite(C, V(0, 1, 0), C2, d45)
        x_turn = ex if xt is None else xt                           # rounding begins at the eye's inner edge
        t_line = (abs(C2.x) - x_turn) / math.sin(ja)
        C3 = C2 + d45 * t_line
        nl = max(1, int(round(t_line / SPINE_STEP)))
        out += [C2 + d45 * (t_line * i / nl) for i in range(1, nl)]
        yf = C3.y + x_turn * HEAD_JAW_ROUND
        out += hermite(C3, d45, V(0, yf, z), V(-sx, 0, 0), ka=0.9, kb=0.9)
        return out, yf
    def jaw_front(z):
        return jaw_front_side(z, sx)
    z_front = ze_u - eyeR - eyeR * HEAD_CHEEK_DROP
    def z_of(y):                                   # height eases (smoothstep) from the attachment down to the corner, then level round the front
        u = max(0.0, min((y - S_pt.y) / (y_post - S_pt.y), 1.0))
        return S_pt.z + (z_front - S_pt.z) * (u * u * (3 - 2 * u))
    for k, sx in (() if "cheek" in SKIP else enumerate((-1, 1))):
        pts = []
        cy = S_pt.y + x_side                       # quarter arc from the back point to the side, radius x_side
        for i in range(9):
            a = math.radians(270 + 90 * i / 8 * sx)
            pts.append(V(math.cos(a) * x_side, cy + math.sin(a) * x_side, 0))
        nr = max(2, int(round((y_post - cy) / SPINE_STEP)))
        for i in range(1, nr + 1):
            pts.append(V(x_side * sx, cy + (y_post - cy) * i / nr, 0))
        front, y_front = jaw_front(0.0)
        pts += front[1:]
        pts = [V(p.x, p.y, z_of(p.y)) for p in pts]
        f.append(tube(f"Head_Cheek{k+1}", pts, CB))

    f_cheek = f; f = []                     # group 3: cheek bars
    # jaw bar: leaves the strap's side edge low down (HEAD_JAW_ATTACH_DEG), runs straight forward
    # to the middle of the head, widens out to the cheek bar's width and sweeps round the front
    # like a jaw, meeting its twin at the chin.
    thj = math.radians(HEAD_JAW_ATTACH_DEG)
    zj = -math.cos(thj)
    x_edge = ctx.s("HeadBar") / 2 / Rn
    jaw_paths = {}
    for k, sx in (() if "jaw" in SKIP else enumerate((-1, 1))):
        nj = max(2, int(round(math.sin(thj) / SPINE_STEP)))
        pts = [V(x_edge * sx, -math.sin(thj) * (1 - i / nj), zj) for i in range(nj + 1)]
        # flare out to the cheek bar's width, then the same plan as the cheek bar's front, straight below it
        pts += hermite(V(x_edge * sx, 0, zj), V(0, 1, 0), V(x_side * sx, y_post - 0.35, zj), V(0, 1, 0))[1:]
        pts += [V(x_side * sx, y_post - 0.35 + 0.35 * i / 3, zj) for i in (1, 2, 3)]
        front, _ = jaw_front(zj)
        pts += front[1:]
        jaw_paths[sx] = pts
        # corrected-Frenet sweep: the flare has an inflection and the runs are straight, both of which
        # break the plain Frenet frame (the cheek, a 3-D curve without either, is fine with Frenet)
        f.append(tube(f"Head_Jaw{k+1}", pts, CB, frenet=False))
    # lower denture platform: a flat U inside the jaw bar, a little forward and below it, tied to the
    # jaw tube by thin rods on each side
    if "jaw" not in SKIP and "denture" not in SKIP:
        zp = zj - DENTURE_DROP
        x_arm = x_side - DENTURE_INSET
        y_arm0 = y_post - 0.3
        upath = []
        yp = y_post + DENTURE_FWD
        for sx in (-1, 1):
            side = [V(x_arm * sx, y_arm0 + (yp - y_arm0) * i / 3, zp) for i in range(3)]
            # rounded front: one smooth curve from the arm end to the centreline
            side += hermite(V(x_arm * sx, yp, zp), V(0, 1, 0), V(0, yp + x_arm * DENTURE_NOSE, zp), V(-sx, 0, 0))
            upath += side if sx == -1 else list(reversed(side))[1:]
        w_n, t_n = ctx.s("CageBar") * DENTURE_W, ctx.s("CageBar") * DENTURE_T
        rw_n = rh_n = ctx.s("CageBar") * DENTURE_LIP
        # platform with a lip along its outer edge (one L-section sweep: a separate lip flush with the
        # edge gave coplanar faces and the fuse dropped the body)
        f.append(flat_tube("Head_Denture", upath, w_n, t_n, lip=(rw_n, rh_n)))
        # lips across the open ends of the arms: a hair wider and further back than the platform, so no
        # face is coplanar with it
        eps = ctx.s("CageBar") * 0.02
        z_top = z_cn + zp * Rn + t_n / 2
        for k, sx in enumerate((-1, 1)):
            f.append(ctx.box(f"Head_DentureBack{k+1}", w_n + 2 * eps, rw_n + eps, rh_n + rh_n * 0.3,
                             x=x_arm * sx * Rn - w_n / 2 - eps, y=y_arm0 * Rn - eps, z=z_top - rh_n * 0.3))
        # tie rods from the platform's outer edge to the jaw tube
        def at_y(path, y, sx):
            return min((p for p in path if p.x * sx > 0.05), key=lambda p: abs(p.y - y))
        for k, sx in enumerate((-1, 1)):
            jaw_pts = jaw_paths[sx]
            for j, yy in enumerate((y_post - 0.12, y_post + 0.12)):
                A = at_y(upath, yy, sx); B = at_y(jaw_pts, yy, sx)
                A = V(A.x * Rn + sx * w_n / 2, A.y * Rn, z_cn + A.z * Rn); B = V(B.x * Rn, B.y * Rn, z_cn + B.z * Rn)
                # barely embedded at the platform edge (the rod slopes, so a deep embed surfaces through the
                # top); ends on the jaw tube's centreline
                f.append(rod(f"Head_DentureRod{k+1}{j+1}", A, B, mul(S("CageBar"), DENTURE_ROD), ctx.s("CageBar") * 0.12))
    # eyeballs on the ring ends, pushed forward a little so the bar enters their backs

    for k, sx in enumerate((-1, 1)):
        f.append(ctx.sphere(f"Head_Eye{k+1}", half(ED),
                            x=mul(S("EyeSpacing"), 0.5 * sx),
                            y=add(mul(Rc, ring_k * math.cos(math.radians(eye_az))), mul(ED, 0.1)), z=z_e))
    f_jaw = [x for x in f if not x.Name.startswith(("Head_Eye", "Head_Denture"))]
    f_dent = [x for x in f if x.Name.startswith("Head_Denture")]
    f_eyes += [x for x in f if x.Name.startswith("Head_Eye")]
    # fuse in groups: OCC hangs on one long chain of everything, but accepts the sub-assemblies
    # (the two cheeks pre-fused together refuse to merge with the frame; each tube joins it directly;
    # the denture platform in the frame group makes the frame+eyes fuse fail, so it joins last)
    groups = [ctx.fuse("Head_G_Frame", f_frame + f_cheek + f_jaw), ctx.fuse("Head_G_Eyes", f_eyes)]
    body = ctx.fuse("Head_Body0" if f_dent else "Head_Body", [g for g in groups if g is not None])
    if f_dent:
        # (the denture pieces pre-fused as a group refuse to join the body; one at a time they do —
        #  rods first so everything after them is already connected)
        rods = [x for x in f_dent if "Rod" in x.Name]
        rest = [x for x in f_dent if "Rod" not in x.Name]
        body = ctx.fuse("Head_Body", [body] + rods + rest)
    socks, _ = ctx.peg_pattern("Head_NeckSockets", neck_face, neck_face_n, "socket")
    # pupils: a shallow flat-bottomed dimple in the front of each eyeball
    pupils = []
    for k, sx in enumerate((-1, 1)):
        eye_y = add(mul(Rc, ring_k * math.cos(math.radians(eye_az))), mul(ED, 0.1))
        pupils.append(ctx.cylinder(f"Head_Pupil{k+1}", mul(ED, HEAD_PUPIL), mul(ED, 0.3),
                                   x=mul(S("EyeSpacing"), 0.5 * sx), y=sub(add(eye_y, half(ED)), mul(ED, HEAD_PUPIL_DEPTH)), z=z_e, rot=ROT_PY))
    head = ctx.cut("Head_S", body, socks)
    for k, p in enumerate(pupils):
        head = ctx.cut(f"Head_P{k+1}" if k < len(pupils) - 1 else "Head", head, p)
    head.Label = "Head"
    return [("Head", head)]

def build_jaw(ctx):
    """Jaw parked while the head bars are being settled."""
    return []

# ============================================================== neck, spine
def build_neck(ctx):
    from mimic_parts import segment
    SD = S("SpineDiameter"); sdn = ctx.s("SpineDiameter")
    nf = mul(S("NeckDiameter"), 1.3); nfn = ctx.s("NeckDiameter") * 1.3
    return segment(ctx, "Neck", S("NeckLength"), ctx.s("NeckLength"), S("NeckDiameter"), ctx.s("NeckDiameter"),
                   SD, sdn, nf, nfn, rods=False, collar=True)

def build_spine(ctx):
    """One column from the pelvis hub top to the shoulder hub bottom, with VertebraCount thick
    collars and a pad on the front where the system box pegs on."""
    from mimic_parts import segment
    SD = S("SpineDiameter"); sdn = ctx.s("SpineDiameter")
    L = S("SpineLength"); Ln = ctx.s("SpineLength")
    N = int(ctx.v["VertebraCount"])
    extras = []
    for k in range(N):
        extras.append(ctx.cylinder(f"Spine_Vert{k+1}", half(S("VertebraDiameter")), mul(SD, 0.5),
                                   z=f"({L} * {(k + 0.5) / N:.4f} - {SD} * 0.25)"))
    # system-box pad: flat face facing +Y at y = SD * 0.9
    pad_face = mul(SD, 0.8); pad_face_n = sdn * 0.8
    # box top sits at T1: pad centre = T1 height - half the box height
    z_pad = f"({L} + {S('HubHeight')} - {S('ShoulderDrop')} - {S('SystemBoxDrop')} - {S('SystemBoxHeight')} / 2)"
    # pad face flush with the spine surface (y = SD/2): the box back sits against the column
    extras.append(ctx.box("Spine_Pad", pad_face, mul(SD, 0.3), pad_face,
                          x=neg(half(pad_face)), y=mul(SD, 0.2), z=sub(z_pad, half(pad_face))))
    pegs, _ = ctx.peg_pattern("Spine_BoxPegs", pad_face, pad_face_n, "peg", rot=ROT_PY)
    if pegs is not None:
        pegs.setExpression(".Placement.Base.y", half(SD)); pegs.setExpression(".Placement.Base.z", z_pad)
        extras.append(pegs)
    return segment(ctx, "Spine", L, Ln, SD, sdn, SD, sdn, SD, sdn, rods=False, collar=False, extras=extras)

# ============================================================== yokes
def _yoke(ctx, name, kind, width, ball, face_dia):
    """Two collars on the spine (C7/T1 at the shoulders, their pelvic twins), each with a flat pad
    on +/-X.  From the upper pad the trap and from the lower pad the clavicle run straight toward
    the ball centre; both stop inside a connector disc that faces along their bisector, so each
    meets it at the same angle.  The disc's outer face is the ball's mating face.
    Returns (column features, {side: arm features}, {side: geom dict}, x_pad expr, x_pad numeric)."""
    from mimic_geom import yoke_side, pad_x
    SD, VD, YB = S("SpineDiameter"), S("VertebraDiameter"), S("YokeBar")
    co = R("JointCupOffset")
    c_e = f"({S(ball)} / 2 * {co})"
    CL_e = mul(S(ball), 0.25)
    PT = mul(YB, 0.3)
    x_pad = add(half(VD), PT); x_padn = pad_x(ctx.v)
    gL, gR = yoke_side(ctx.v, kind, -1), yoke_side(ctx.v, kind, 1)
    geoms_pre = {"L": gL, "R": gR}
    # collar heights as expressions, top to bottom (must match mimic_geom.YOKES)
    if kind == "shoulder":
        collars = [("C7", sub(S("HubHeight"), mul(SD, 0.35))), ("T1", sub(S("HubHeight"), S("ShoulderDrop")))]
    else:
        zu_, zl_ = neg(mul(SD, 0.35)), neg(S("PelvisDrop"))
        collars = [("L5", zu_), ("S1", f"(({zu_} + {zl_}) / 2)"), ("S5", zl_)]
    zl = collars[-1][1]
    kinds = {tag: kd for tag, _z, kd in __import__("mimic_geom").YOKES[kind][2]}
    col = []
    for tag, z in collars:
        if kinds[tag] != "pad":
            continue                                   # nothing attaches at a junction collar: no ring
        col.append(ctx.cylinder(f"{name}_{tag}Collar", half(VD), mul(SD, 0.5), z=sub(z, mul(SD, 0.25))))
        for side, sx in (("L", -1), ("R", 1)):
            col.append(ctx.box(f"{name}_{tag}Pad{side}", add(PT, 2), mul(YB, 1.4), mul(YB, 1.4),
                               x=(sub(half(VD), 2) if sx > 0 else neg(x_pad)),
                               y=neg(mul(YB, 0.7)), z=sub(z, mul(YB, 0.7))))
    # clavicle junction: a knuckle over the control box's top-front edge, shared by both sides
    junc = None
    for tag, z in collars:
        if kinds[tag] == "junction":
            if kind == "shoulder":
                jy = add(half(SD), S("SystemBoxDepth")); jz = add(z, half(YB))
            else:
                jy = S("PelvisForward"); jz = z
            junc = (jy, jz)
            CONN = S("ClavicleBar") if kind == "shoulder" else S("PelvisBar")
            # centre joint on the box's top-front edge; from it each side's thick connector runs
            # straight along the clavicle's own line for ClavicleBar/2, then the clavicle continues
            col.append(ctx.sphere(f"{name}_ClavJoint", mul(YB, 0.7), y=jy, z=jz))
            for side, sx in (("L", -1), ("R", 1)):
                u = [b for b in geoms_pre[side]["bars"] if b[4] == "junction"][0][2]
                col.append(ctx.cylinder(f"{name}_ClavConn{side}", mul(YB, 0.6), half(CONN),
                                        y=jy, z=jz, rot=App.Rotation(V(0, 0, 1), u)))
                col.append(ctx.sphere(f"{name}_ClavConnEnd{side}", mul(YB, 0.6),
                                      x=f"({half(CONN)} * {u.x:.6f})", y=f"({jy} + {half(CONN)} * {u.y:.6f})",
                                      z=f"({jz} + {half(CONN)} * {u.z:.6f})"))
    fwd = S("ShoulderForward") if kind == "shoulder" else S("PelvisForward")
    arms, geoms = {}, {"L": gL, "R": gR}
    for side, sx in (("L", -1), ("R", 1)):
        g = geoms[side]; f = arms[side] = []
        B = (f"({S(width)} / 2 * {sx})", fwd, (add(zl, mul(S("YokeBar"), 2)) if kind == "shoulder" else zl))
        n = g["n"]
        def along(base, k_expr, vec):
            """base - k_expr * vec, per component (vec numeric unit vector)."""
            return tuple(f"({base[i]} - {k_expr} * {vec[i]:.6f})" for i in range(3))
        # bars: from each attachment, straight at the ball centre, stopping 40% into the disc
        for (tag, Pn, u, _zn, kd), (_t, z) in zip(g["bars"], collars):
            P = (mul(x_pad, 0.98 * sx), "0 mm", z) if kd == "pad" else ("0 mm", junc[0], junc[1])
            udn = u.dot(n)
            E = along(B, f"(({c_e} + {CL_e} * 0.4) / {udn:.6f})", u)
            En = g["B"] - u * ((g["c"] + g["CL"] * 0.4) / udn)
            f.append(bar(ctx, f"{name}_{tag}{side}", half(YB), P, E, Pn, En))
        # connector disc on the bisector: from B - (c + CL) n  to  F = B - c n
        base = along(B, f"({c_e} + {CL_e})", n)
        f.append(ctx.cylinder(f"{name}_Disc{side}", half(face_dia), CL_e,
                              x=base[0], y=base[1], z=base[2], rot=App.Rotation(V(0, 0, 1), n)))
        g["F_expr"] = along(B, c_e, n)
    return col, arms, geoms, x_pad, x_padn, collars

def _yoke_pieces(ctx, name, label, col, arms, geoms, x_pad, collars, face_dia, face_dia_n, end_pegs, end_socks):
    """Fuse a yoke into one piece, or split it into Column + ArmL + ArmR (pegged at the pads)
    when it is wider than the build cube."""
    YB = S("YokeBar"); ybn = ctx.s("YokeBar")
    ball_pegs = {}
    for side, sx, rot in (("L", -1, ROT_NX), ("R", 1, ROT_PX)):
        g = geoms[side]
        p, _ = ctx.peg_pattern(f"{name}_BallPegs{side}", face_dia, face_dia_n, "peg", rot=g["rot"])
        if p is not None:
            for ax, e in zip("xyz", g["F_expr"]):
                p.setExpression(f".Placement.Base.{ax}", e)
        ball_pegs[side] = p
    width_n = 2 * abs(geoms["R"]["B"].x)      # ball centre to centre: the tilted disc + pegs reach nearly that far
    if width_n <= ctx.v["BuildVolume"]:
        body = ctx.fuse(f"{name}_Body", col + arms["L"] + arms["R"])
        for i, s_ in enumerate(end_socks):
            body = ctx.cut(f"{name}_S{i+1}", body, s_)
        out = ctx.fuse(label, [body] + end_pegs + [ball_pegs["L"], ball_pegs["R"]])
        out.Label = label
        return [(label, out)]
    pieces, col_pegs = [], []
    for side, sx, rot in (("L", -1, ROT_NX), ("R", 1, ROT_PX)):
        keep = ctx.box(f"{name}_Arm{side}Keep", BIG / 2, BIG, BIG, y=-BIG / 2, z=-BIG / 2)
        keep.setExpression(".Placement.Base.x", f"{-BIG / 2 if sx < 0 else 0} mm + {mul(x_pad, sx)}")
        arm = ctx.common(f"{name}_Arm{side}Cut", ctx.fuse(f"{name}_Arm{side}Body", arms[side]), keep)
        socks = []
        # pegs where each bar crosses the cut plane x = +/-x_pad (numeric crossing along the bar line)
        xpn = geoms[side]["bars"][0][1].x / 0.98
        for (tag, Pn, u, _zn, _kd), (_t, z) in zip(geoms[side]["bars"], collars):
            tcross = (xpn - Pn.x) / u.x if abs(u.x) > 1e-9 else 0.0
            Xc = Pn + u * tcross
            s_, _ = ctx.peg_pattern(f"{name}_Arm{side}{tag}Sockets", YB, ybn, "socket", rot=rot)
            s_.Placement = App.Placement(Xc, rot)
            socks.append(s_)
            p_, _ = ctx.peg_pattern(f"{name}_Col{side}{tag}Pegs", YB, ybn, "peg", rot=rot)
            p_.Placement = App.Placement(Xc, rot)
            col_pegs.append(p_)
        arm = ctx.cut(f"{name}_Arm{side}S", arm, ctx.fuse(f"{name}_Arm{side}SocketsAll", socks))
        arm = ctx.fuse(f"{label}-Arm{side}", [arm, ball_pegs[side]])
        arm.Label = f"{label}-Arm{side}"; pieces.append((arm.Label, arm))
    body = ctx.fuse(f"{name}_ColBody", col)
    for i, s_ in enumerate(end_socks):
        body = ctx.cut(f"{name}_ColS{i+1}", body, s_)
    colp = ctx.fuse(f"{label}-Column", [body] + end_pegs + col_pegs)
    colp.Label = f"{label}-Column"; pieces.append((colp.Label, colp))
    return pieces

def build_shoulderyoke(ctx):
    """Origin at the bottom of a HubHeight spine section (spine mating face), +Z up.
    C7 collar near the top (traps), T1 collar at ShoulderDrop below the top (clavicles)."""
    SD = S("SpineDiameter"); sdn = ctx.s("SpineDiameter")
    sh_face, sh_face_n = _face(ctx, "ShoulderBall")
    HH = S("HubHeight")
    col, arms, geoms, x_pad, x_padn, collars = _yoke(ctx, "Yoke", "shoulder", "ShoulderWidth", "ShoulderBall", sh_face)
    col.insert(0, ctx.cylinder("Yoke_Column", half(SD), HH))
    neck_pegs, _ = ctx.peg_pattern("Yoke_NeckPegs", SD, sdn, "peg", z=HH)
    spine_socks, _ = ctx.peg_pattern("Yoke_SpineSockets", SD, sdn, "socket")
    return _yoke_pieces(ctx, "Yoke", "ShoulderYoke", col, arms, geoms, x_pad, collars,
                        sh_face, sh_face_n, [neck_pegs], [spine_socks])

def build_pelvis(ctx):
    """Root of the chain.  Origin at the top of the pelvis spine section (spine mating face), +Z up.
    Upper collar just below the top (iliac bars slant down), lower collar at hip height (sacral
    bars horizontal); the column runs down to the lower collar."""
    SD = S("SpineDiameter"); sdn = ctx.s("SpineDiameter")
    hip_face, hip_face_n = _face(ctx, "HipBall")
    col, arms, geoms, x_pad, x_padn, collars = _yoke(ctx, "Pelvis", "pelvis", "PelvisWidth", "HipBall", hip_face)
    # the column ends flush with the lowest ring that still carries bars (S1)
    z_s1 = f"(({neg(mul(SD, 0.35))} + {neg(S('PelvisDrop'))}) / 2)"
    col_len = add(neg(z_s1), mul(SD, 0.25))
    col.insert(0, ctx.cylinder("Pelvis_Column", half(SD), col_len, z=neg(col_len)))
    spine_pegs, _ = ctx.peg_pattern("Pelvis_SpinePegs", SD, sdn, "peg")
    return _yoke_pieces(ctx, "Pelvis", "Pelvis", col, arms, geoms, x_pad, collars,
                        hip_face, hip_face_n, [spine_pegs], [])

# ============================================================== system box
def build_systembox(ctx):
    """Origin at the back face (against the spine pad); local +Z = outward (world +Y), local -Y = up."""
    W, Hh, D = S("SystemBoxWidth"), S("SystemBoxHeight"), S("SystemBoxDepth")
    SD = S("SpineDiameter"); sdn = ctx.s("SpineDiameter")
    pad_face, pad_face_n = mul(SD, 0.8), sdn * 0.8
    box = ctx.box("SysBox_Body", W, Hh, D, x=neg(half(W)), y=neg(half(Hh)))
    inset = mul(W, 0.08)
    iw, ih = sub(W, mul(inset, 2)), sub(Hh, mul(inset, 2))
    recess = ctx.box("SysBox_Recess", iw, ih, mul(D, 0.12), x=neg(half(iw)), y=neg(half(ih)), z=sub(D, mul(D, 0.12)))
    body = ctx.cut("SysBox_Cut", box, recess)
    ribs = []
    for k, a in enumerate((42, -42)):
        rot = App.Rotation(V(0, 0, 1), a)
        Ld = f"(sqrt({W} ^ 2 + {Hh} ^ 2) * 0.8)"
        rib = ctx.box(f"SysBox_X{k+1}", mul(W, 0.06), Ld, mul(D, 0.12), rot=rot)
        m = rot.toMatrix()
        rib.setExpression(".Placement.Base.x", f"({m.A[0]:.6f} * (-{W} * 0.03) + {m.A[1]:.6f} * (-{Ld} / 2))")
        rib.setExpression(".Placement.Base.y", f"({m.A[4]:.6f} * (-{W} * 0.03) + {m.A[5]:.6f} * (-{Ld} / 2))")
        rib.setExpression(".Placement.Base.z", sub(D, mul(D, 0.12)))
        clip = ctx.box(f"SysBox_Clip{k+1}", iw, ih, D, x=neg(half(iw)), y=neg(half(ih)))
        ribs.append(ctx.common(f"SysBox_XClip{k+1}", rib, clip))
    body = ctx.fuse("SysBox_WithX", [body] + ribs)
    # cable loops on top (local -Y is up)
    loops = []
    for k, fx in enumerate((-0.3, 0.0, 0.3)):
        loops.append(ctx.torus(f"SysBox_Cable{k+1}", mul(Hh, 0.18), mul(W, 0.02), angle3=180.0,
                               x=mul(W, fx), y=neg(half(Hh)), z=mul(D, 0.5),
                               rot=ROT_YZ.multiply(App.Rotation(V(0, 0, 1), 180))))
    body = ctx.fuse("SysBox_Cabled", [body] + loops)
    socks, _ = ctx.peg_pattern("SysBox_Sockets", pad_face, pad_face_n, "socket")
    out = ctx.cut("SystemBox", body, socks)
    out.Label = "SystemBox"
    return [("SystemBox", out)]

# ============================================================== hands
def build_hand_l(ctx): return _hand(ctx, "HandL", -1)
def build_hand_r(ctx): return _hand(ctx, "HandR", 1)

def _hand(ctx, name, tx):
    """Origin at the wrist face, digits along local +Z, palm normal local Y; thumb toward local tx*X.
    Three spindly segmented digits and one thumb."""
    face, face_n = _face(ctx, "WristBall")
    L, PW, FW = S("HandLength"), S("PalmWidth"), S("FingerWidth")
    palm_len = mul(L, 0.22)
    f = [ctx.cone("Hand_Cup", half(face), mul(PW, 0.3), mul(face, 0.35)),
         ctx.box("Hand_Palm", PW, mul(FW, 1.6), palm_len, x=neg(half(PW)), y=neg(mul(FW, 0.8)), z=mul(face, 0.3))]
    fl = sub(L, palm_len)
    z0 = add(mul(face, 0.3), palm_len)

    def digit(prefix, x, z_start, rot, fracs, taper):
        m = rot.toMatrix()
        base = (x, "0 mm", z_start)
        acc = "0 mm"
        for i, fr in enumerate(fracs):
            w = mul(FW, taper ** i); t = mul(FW, 0.8 * taper ** i)
            seg_len = mul(fl, fr)
            pos = [f"({base[j]} + {m.A[j*4+2]:.6f} * {acc} + {m.A[j*4+0]:.6f} * (-{w} / 2) + {m.A[j*4+1]:.6f} * (-{t} / 2))" for j in range(3)]
            f.append(ctx.box(f"{prefix}_Seg{i+1}", w, t, seg_len, x=pos[0], y=pos[1], z=pos[2], rot=rot))
            pr = mul(FW, 0.55 * taper ** i)
            pin = [f"({base[j]} + {m.A[j*4+2]:.6f} * {acc} + {m.A[j*4+0]:.6f} * (-{pr}))" for j in range(3)]
            f.append(ctx.cylinder(f"{prefix}_Pin{i+1}", pr, mul(pr, 2), x=pin[0], y=pin[1], z=pin[2], rot=rot.multiply(ROT_PX)))
            acc = add(acc, seg_len)
        tip = [f"({base[j]} + {m.A[j*4+2]:.6f} * {acc})" for j in range(3)]
        f.append(ctx.sphere(f"{prefix}_Tip", mul(FW, 0.4 * taper ** len(fracs)), x=tip[0], y=tip[1], z=tip[2]))

    for k, fx in enumerate((-1 / 3, 0.0, 1 / 3)):
        digit(f"Hand_D{k+1}", mul(PW, fx), z0, ROT0, (0.4, 0.33, 0.27), 0.9)
    digit("Hand_Thumb", mul(PW, 0.5 * tx), mul(palm_len, 0.6), App.Rotation(V(0, 1, 0), tx * 45), (0.3, 0.25), 0.9)
    body = ctx.fuse("Hand_Body", f)
    socks, _ = ctx.peg_pattern("Hand_Sockets", face, face_n, "socket")
    hand = ctx.cut(name, body, socks)
    hand.Label = name
    return [(name, hand)]

# ============================================================== feet
def _wedge(ctx, name, x, y, z, x2, z2, rot=None):
    """Part::Wedge from expressions: base at y[0] spans x, z; top at y[1] spans x2, z2 (taper along +Y)."""
    w = ctx.obj("Part::Wedge", name)
    for prop, val in (("Xmin", x[0]), ("Xmax", x[1]), ("Ymin", y[0]), ("Ymax", y[1]), ("Zmin", z[0]), ("Zmax", z[1]),
                      ("X2min", x2[0]), ("X2max", x2[1]), ("Z2min", z2[0]), ("Z2max", z2[1])):
        w.setExpression(prop, val)
    if rot is not None:
        w.Placement = App.Placement(V(0, 0, 0), rot)
    return w

def _blade_toe(ctx, name, x0, yaw, y_face, y_root, y_tip, H, instep, w0, apex, rise, sink):
    """One toe as a smooth lofted blade (numeric).  Knife section: flat top, short vertical sides,
    sharp bottom edge.  Bottom edge lies on the sole plane inside the foot, leaves it at the front face,
    arcs up to `rise` at `apex` (fraction of the exposed length) and comes down to a point at y_tip.
    Top edge follows the instep surface (sunk by `sink`) and converges to the same point."""
    n_in, n_out = 3, 14
    ys = [y_root + (y_face - y_root) * i / n_in for i in range(n_in)] +          [y_face + (y_tip - y_face) * i / n_out for i in range(n_out + 1)]
    wires = []
    for y in ys:
        v = max(0.0, (y - y_face) / (y_tip - y_face))               # 0 at the face .. 1 at the tip
        if v <= 0:
            bump = 0.0
        elif v < apex:
            bump = (1 - math.cos(math.pi * v / apex)) / 2
        else:
            bump = math.cos(math.pi / 2 * (v - apex) / (1 - apex))
        zb = H - rise * bump
        h_face = H - instep(y_face) - sink
        if v <= 0:
            zb = H - sink * (y_face - y) / (y_face - y_root)          # inside: just under the sole plane
            zt = instep(y) + sink                                    # inside: just under the instep
        else:
            zt = zb - h_face * (1 - v ** 1.3)                        # height fades to a point at the tip
        h = max(zb - zt, 0.0)
        w = w0 * (1 - v) ** 0.7
        w = max(w, w0 * 0.03); h = max(h, w0 * 0.03)
        yl = y - y_face                                              # local: yaw pivots at the front face
        pts = [V(-w / 2, yl, zt), V(w / 2, yl, zt), V(w / 2, yl, zt + 0.35 * h), V(0, yl, zt + h),
               V(-w / 2, yl, zt + 0.35 * h), V(-w / 2, yl, zt)]
        wires.append(Part.makePolygon(pts))
    shape = Part.makeLoft(wires, True, False)
    m = App.Placement(V(x0, y_face, 0), App.Rotation(V(0, 0, 1), yaw)).toMatrix()
    shape.transformShape(m)
    o = ctx.obj("Part::Feature", name)
    o.Shape = shape
    return o

def build_foot(ctx):
    """Origin at the ankle face, local +Z = down, +Y = forward.  A flat-soled foot: the ankle sits 30%
    of FootLength from the heel; the instep slopes down from the ankle to the toe and heel; the
    footprint is rounded at the heel and truncated flat at its widest point, where three blade toes
    emerge and arc down to points on the sole plane.  Top edges filleted."""
    face, face_n = _face(ctx, "AnkleBall")
    H, FL, FW, TW = S("FootHeight"), S("FootLength"), S("FootWidth"), S("ToeWidth")
    # instep top at the ankle: FOOT_ANKLE_H of the way from the sole up to just under the ankle face
    top = sub(H, mul(sub(H, mul(face, 0.25)), FOOT_ANKLE_H))
    heel, toe = mul(FL, FOOT_HEEL), sub(FL, mul(FL, FOOT_HEEL))
    rh, rt = mul(FW, 0.35), half(FW)             # heel / toe rounding radii
    # instep: two wedges meeting at the ankle, sloping down to sole height at each end
    sole_top_t, sole_top_h = mul(H, 0.65), mul(H, 0.55)
    f = [_wedge(ctx, "Foot_Instep", (neg(FW), FW), ("0 mm", toe), (top, H), (neg(FW), FW), (sole_top_t, H)),
         _wedge(ctx, "Foot_Heel", (neg(FW), FW), ("0 mm", heel), (top, H), (neg(FW), FW), (sole_top_h, H),
                rot=App.Rotation(V(0, 0, 1), 180))]
    body = ctx.fuse("Foot_Body", f)
    # footprint: rounded heel and toe joined by a tapered slab, extruded through the full height
    yh, yt = neg(sub(heel, rh)), sub(toe, rt)
    fp = [ctx.cylinder("Foot_PrintHeel", rh, H, y=yh),
          ctx.cylinder("Foot_PrintToe", rt, H, y=yt),
          _wedge(ctx, "Foot_PrintMid", (neg(rh), rh), (yh, yt), ("0 mm", H), (neg(rt), rt), ("0 mm", H))]
    print_ = ctx.fuse("Foot_Print", fp)
    body = ctx.common("Foot_Shaped", body, print_)
    # truncate at the widest point (the toe circle's centre line) to get a flat front face
    front = ctx.box("Foot_Front", BIG, BIG, BIG, x=-BIG / 2, y=yt, z=-BIG / 2)
    body = ctx.cut("Foot_Trunc", body, front)
    # fillet every edge except those lying in the sole plane
    ctx.doc.recompute()
    H_n = ctx.s("FootHeight")
    edges = [(i + 1, FOOT_FILLET * ctx.s("FootWidth"), FOOT_FILLET * ctx.s("FootWidth"))
             for i, e in enumerate(body.Shape.Edges)
             if not all(abs(vx.Point.z - H_n) < 0.01 for vx in e.Vertexes)]
    fil = ctx.obj("Part::Fillet", "Foot_Fillet")
    fil.Base = body; fil.Edges = edges
    body.Visibility = False
    ctx.doc.recompute()
    if fil.Shape.isNull() or not fil.Shape.isValid() or fil.Shape.Volume < body.Shape.Volume * 0.9:
        print("[mimic]   Foot: fillet failed, leaving edges sharp")
        ctx.doc.removeObject(fil.Name)
        body.Visibility = True
    else:
        body = fil
    f = [body, ctx.cone("Foot_Cup", half(face), mul(TW, 0.9), mul(face, 0.35)),
         # ankle post from the cup down into the instep
         ctx.cylinder("Foot_Post", mul(TW, 0.9), sub(add(top, mul(H, 0.05)), mul(face, 0.3)), z=mul(face, 0.3))]
    # blade toes (numeric): sole-plane bottom edge, rising after the front face, point on the floor
    FL_n, FW_n, TW_n, toe_n, yt_n = ctx.s("FootLength"), ctx.s("FootWidth"), ctx.s("ToeWidth"),         ctx.s("FootLength") * (1 - FOOT_HEEL), ctx.s("FootLength") * (1 - FOOT_HEEL) - ctx.s("FootWidth") / 2
    top_n, sole_t_n = H_n - (H_n - face_n * 0.25) * FOOT_ANKLE_H, H_n * 0.65
    instep = lambda y: top_n + (sole_t_n - top_n) * y / toe_n
    w0 = TOE_BLADE_W * TW_n
    x_out = FW_n / 2 - w0 / 2                    # outer toes' outer faces flush with the foot's sides
    for k, (x0, yaw) in enumerate(((-x_out, TOE_FAN_DEG), (0.0, 0.0), (x_out, -TOE_FAN_DEG))):
        f.append(_blade_toe(ctx, f"Foot_Toe{k+1}", x0, yaw, yt_n, yt_n - 0.15 * FL_n, yt_n + TOE_REACH * FL_n,
                            H_n, instep, w0, TOE_APEX, TOE_RISE * H_n, 0.01 * FW_n))
    body = ctx.fuse("Foot_All", f)
    socks, _ = ctx.peg_pattern("Foot_Sockets", face, face_n, "socket")
    foot = ctx.cut("Foot", body, socks)
    foot.Label = "Foot"
    return [("Foot", foot)]
