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
TOE_FAN_DEG = 0.0   # outer toes splay this much (0 = parallel)
FOOT_ANKLE_W = 0.76 # foot width from the heel to the front face, fraction of FootWidth (parallel sides)
FOOT_BLOCK = 0.16   # the solid foot block ends this far ahead of the ankle (fraction of FootLength; must cover the ankle post)
FOOT_WEB = 0.5      # metatarsal web: how far the top dips between the toes at the toe root, fraction of the toe height there
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
HEAD_JAW_ATTACH_DEG = 28.0      # jaw bar height as an angle up the strap from C1 (z = -cos): 40 was the original, 0 is level with the neck
HEAD_JAW_ROOT = 0.2             # the jaw bars start this far behind centre (head radii): inside the neck boss when attach is 0
HEAD_SOCKET_INNER = 0.97        # eye socket cup inner radius, in eye radii (just under 1 so it grips the ball)
HEAD_SOCKET_THICK = 1.6         # cup wall, in top-bar thicknesses
HEAD_SOCKET_RIM = 0.1           # socket bowl rim sits this many eye radii below the eye equator
HEAD_BOSS_DEG = 25.0            # screw boss sits this far below the equator
HEAD_BOSS_AZ = 45.0             # ...and this far round from the eye's outer side toward the back
HEAD_SOCKET_SPAN = 150.0        # socket wedge: degrees of azimuth from the medial side of the eye round the back (must reach the boss)
HEAD_CHEEK_CORNER = 0.5         # cheek bar turns the front corner this many eye radii behind the eye centre
HEAD_JAW_ANGLE = 45.0           # after the corner the cheek/jaw bars head inward-forward at this angle
HEAD_JAW_ROUND = 0.7            # front rounding bulge, as a fraction of the half eye spacing
DENTURE_INSET = 0.34            # denture platforms sit this far inside the jaw bar (head radii); ~0.13 would touch it
DENTURE_FWD = 0.05              # its arms end this far forward of the jaw's corner
DENTURE_DROP = -0.08            # lower platform: below the jaw bar (negative = above)
DENTURE_UPPER_DROP = -0.08      # upper platform: below the cheek bar (negative = above)
DENTURE_NOSE = 0.9              # front bulge beyond the arm ends, as a fraction of the half width
DENTURE_W = 1.6                 # platform width, in CageBar diameters
DENTURE_T = 0.5                 # platform thickness, in CageBar diameters
DENTURE_ROD = 0.2               # tie-rod radius, in CageBar diameters (under half the platform thickness)
DENTURE_LIP = 0.2               # lip width and height on the platform's outer and back edges, in CageBar diameters
HEAD_GUM_HEIGHT = 0.12          # denture platforms: band height (head radii)
# mouth insert (gums + teeth + tongue), in gum widths unless noted
MOUTH_CLEAR = 0.1               # clearance between the insert and the tray's lip (CageBar diameters)
MOUTH_GUM_H = 0.9               # gum ridge height
MOUTH_TOOTH_BASE = 0.6          # crown heights in TEETH are measured from this height, not the gum top
MOUTH_TOOTH_ROUND = 0.16        # corner radius of the tooth sections, x the smaller side
MOUTH_FOSSA = 0.176             # molar central fossa radius, x the smaller top side
MOUTH_MARGIN_R = 0.0            # fillet radius on the gum where it meets a tooth's cheek/tongue faces (gum widths); 0 = none
MOUTH_JITTER = 1.0              # scale of the per-tooth randomness (size, yaw, lean, shift); 0 = uniform
MOUTH_TOOTH_PITCH = 1.1         # tooth spacing along the ridge
MOUTH_TONGUE_TOOTH = 2          # the tongue's highest point matches this tooth's nominal crown top (index into TEETH: 2 = cuspid)
MOUTH_TONGUE_LIFT_DEG = 10      # tongue pitched up so the tip lifts
MOUTH_GROOVE_R = 0.3            # tongue groove: cylinder radius (gum widths) ...
MOUTH_GROOVE_DEPTH = 0.1        # ... sunk this deep, so it meets the surface at a shallow angle
MOUTH_TONGUE_TIP_MM = 0.1       # clearance between the tongue and the teeth's inner faces, front and sides (mm, absolute)
MOUTH_TONGUE_BACK = 0.35        # ellipsoid centre this far from the back cut, as a fraction of the tongue length
MOUTH_FLOOR_T = 0.25            # mouth-floor plate thickness (joins tongue to gums)
MOUTH_ARCH_OVERSHOOT = 0.15     # the arch runs this far (gum widths) past the back plane, so the last molar is cut flush
# lower arch from the midline back: (kind, human width mm, depth / gum width, crown height / gum width)
# (depths are kept well inside the gum width so the ridge's hump stays standing beside every tooth,
#  molars included; the socket takes the hump's crest, and what shows is the flank outside it)
TEETH = [("incisor", 5.4, 0.55, 1.2), ("incisor", 5.9, 0.6, 1.15), ("cuspid", 7.25, 0.68, 1.21),
         ("bicuspid", 7.0, 0.7, 0.95), ("bicuspid", 7.1, 0.7, 0.9),
         ("molar", 11.4, 0.75, 0.8), ("molar", 10.7, 0.75, 0.75)]

def _rrect(a, b, r, z):
    """Closed rounded-rectangle wire a x b at height z, corner radius r (arc joins of an offset)."""
    r = min(r, a * 0.45, b * 0.45)
    core = Part.makePolygon([V(-a / 2 + r, -b / 2 + r, z), V(a / 2 - r, -b / 2 + r, z), V(a / 2 - r, b / 2 - r, z),
                             V(-a / 2 + r, b / 2 - r, z), V(-a / 2 + r, -b / 2 + r, z)])
    return core.makeOffset2D(r, 0, False, False)

def _tooth(w, d, h, wt, dt, bulge=1.0, rnd=None, top_r=0.3, grooves=(), fossa=False):
    """One tooth in its own frame: X along the arch, Y outward, Z up.  A smooth loft through
    rounded-rectangle sections (corner radius rnd x the smaller side): w x d at the base, bulging
    to bulge x that at mid crown, wt x dt at the top, whose rim is filleted top_r x min(wt, dt).
    Cusps are made by cutting: grooves = any of "x" (along the arch) and "y" (across it) are
    cylinders sunk into the occlusal surface; fossa adds a spherical dimple at its centre."""
    rnd = MOUTH_TOOTH_ROUND if rnd is None else rnd
    r = rnd * min(w, d)
    secs = [_rrect(w, d, r, 0), _rrect(w * bulge, d * bulge, r, h * 0.55), _rrect(wt, dt, min(r, rnd * min(wt, dt) * 2), h)]
    try:
        sh = Part.makeLoft(secs, True, False)
        if sh.isNull() or not sh.isValid() or sh.Volume < 1e-9:
            raise ValueError("loft")
    except Exception:
        sh = Part.makeLoft([secs[0], secs[2]], True, True)
    top = [e for e in sh.Edges if abs(e.BoundBox.ZMin - h) < 1e-6 and abs(e.BoundBox.ZMax - h) < 1e-6]
    for k in (1.0, 0.7, 0.45):                                     # largest fillet OCC will accept
        try:
            f2 = sh.makeFillet(min(wt, dt) * top_r * k, top)
            if f2.isValid() and f2.Volume > sh.Volume * 0.6:
                sh = f2; break
        except Exception:
            pass
    rg = 0.13 * min(wt, dt); zg = h - rg * 0.55                    # groove radius / axis height (groove ~0.45 r deep)
    L = 3 * max(w, d)
    if "x" in grooves:
        sh = sh.cut(Part.makeCylinder(rg, L, V(-L / 2, 0, zg), V(1, 0, 0)))
    if "y" in grooves:
        sh = sh.cut(Part.makeCylinder(rg, L, V(0, -L / 2, zg), V(0, 1, 0)))
    if fossa:
        rf = MOUTH_FOSSA * min(wt, dt)
        sh = sh.cut(Part.makeSphere(rf, V(0, 0, h - rf * 0.35)))
    return sh.removeSplitter() if (grooves or fossa) else sh

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

SPINE_STEP = 0.1                # target point spacing along head tube spines (head radii)

def _hermite(Pa, ta, Pb, tb, n=None, ka=1.0, kb=1.0):
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

def _head_plan(ctx):
    """Numeric (unit-sphere) landmarks shared by the head cage and the mouth insert: eye frame,
    the cheek/jaw plan (x_side, y_post) and the heights of the cheek front (z_front) and jaw (zj)."""
    Rc, Rn, z_c, z_cn, z_e, ring_k, eye_lat, eye_az, boss_h = _head_geom(ctx)
    ze_u = math.sin(math.radians(eye_lat))
    eyeR = ctx.s("EyeDiameter") / 2 / Rn
    ex = ctx.s("EyeSpacing") / 2 / Rn
    ey = ring_k * math.cos(math.radians(eye_az)) + ctx.s("EyeDiameter") * 0.1 / Rn
    th = math.radians(HEAD_CHEEK_ATTACH_DEG)
    S_pt = V(0, -math.sin(th), -math.cos(th))
    x_side = ex + (math.sqrt(1 - S_pt.z ** 2) - ex) * HEAD_CHEEK_SIDE
    y_post = ey - eyeR * HEAD_CHEEK_CORNER              # the front corner of the cheek / jaw plan
    z_front = ze_u - eyeR - eyeR * HEAD_CHEEK_DROP      # cheek bar height round the front
    zj = -math.cos(math.radians(HEAD_JAW_ATTACH_DEG))   # jaw bar height
    return dict(Rn=Rn, z_cn=z_cn, ze_u=ze_u, eyeR=eyeR, ex=ex, ey=ey, S_pt=S_pt,
                x_side=x_side, y_post=y_post, z_front=z_front, zj=zj)

def _denture_upath(x_arm, y_arm0, yp, zp, nose):
    """The denture U in unit-sphere coordinates: two arms at x = +/-x_arm from y_arm0 to yp, joined
    by one smooth rounded front reaching nose beyond the arm ends.  Runs from the -X arm end to the +X."""
    upath = []
    for sx in (-1, 1):
        side = [V(x_arm * sx, y_arm0 + (yp - y_arm0) * i / 3, zp) for i in range(3)]
        side += _hermite(V(x_arm * sx, yp, zp), V(0, 1, 0), V(0, yp + nose, zp), V(-sx, 0, 0))
        upath += side if sx == -1 else list(reversed(side))[1:]
    return upath

def _denture_dims(ctx, hp):
    """Denture platform plan (unit-sphere x/y, mm widths) shared by the head and the mouth insert."""
    cb = ctx.s("CageBar")
    return dict(x_arm=hp["x_side"] - DENTURE_INSET, y_arm0=hp["y_post"] - 0.3, yp=hp["y_post"] + DENTURE_FWD,
                nose=(hp["x_side"] - DENTURE_INSET) * DENTURE_NOSE,
                w_n=cb * DENTURE_W, t_n=cb * DENTURE_T, rw_n=cb * DENTURE_LIP, rh_n=cb * DENTURE_LIP)

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
    hp = _head_plan(ctx)
    eyeR, ex, ey = hp["eyeR"], hp["ex"], hp["ey"]
    TTn = ctx.s("CageBar") / 2 / Rn
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
    hermite = _hermite

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

    def flat_tube(name, pts_unit, w_n, t_n, lip=None, flip=False):
        """Rectangular-section sweep (w wide, t tall, kept level) along a B-spline through unit-sphere points.
        lip=(lw, lh) adds a lip of that width/height along the top outer edge (left of travel): an L section.
        flip=True turns the section upside down (lip on the bottom edge) for the upper denture."""
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
        if flip:
            e2 = -e2
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
    S_pt, x_side, y_post = hp["S_pt"], hp["x_side"], hp["y_post"]      # (see _head_plan)
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
    z_front = hp["z_front"]
    def z_of(y):                                   # height eases (smoothstep) from the attachment down to the corner, then level round the front
        u = max(0.0, min((y - S_pt.y) / (y_post - S_pt.y), 1.0))
        return S_pt.z + (z_front - S_pt.z) * (u * u * (3 - 2 * u))
    cheek_paths = {}
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
        cheek_paths[sx] = pts
        f.append(tube(f"Head_Cheek{k+1}", pts, CB))

    f_cheek = f; f = []                     # group 3: cheek bars
    # jaw bar: starts inside the neck boss (or at the strap's side edge when HEAD_JAW_ATTACH_DEG > 0),
    # level at zj, runs straight forward
    # to the middle of the head, widens out to the cheek bar's width and sweeps round the front
    # like a jaw, meeting its twin at the chin.
    thj = math.radians(HEAD_JAW_ATTACH_DEG)
    zj = hp["zj"]
    x_edge = ctx.s("HeadBar") / 2 / Rn
    jaw_paths = {}
    for k, sx in (() if "jaw" in SKIP else enumerate((-1, 1))):
        y_root = max(math.sin(thj), HEAD_JAW_ROOT)
        nj = max(2, int(round(y_root / SPINE_STEP)))
        pts = [V(x_edge * sx, -y_root * (1 - i / nj), zj) for i in range(nj + 1)]
        # flare out to the cheek bar's width, then the same plan as the cheek bar's front, straight below it
        pts += hermite(V(x_edge * sx, 0, zj), V(0, 1, 0), V(x_side * sx, y_post - 0.35, zj), V(0, 1, 0))[1:]
        pts += [V(x_side * sx, y_post - 0.35 + 0.35 * i / 3, zj) for i in (1, 2, 3)]
        front, _ = jaw_front(zj)
        pts += front[1:]
        jaw_paths[sx] = pts
        # corrected-Frenet sweep: the flare has an inflection and the runs are straight, both of which
        # break the plain Frenet frame (the cheek, a 3-D curve without either, is fine with Frenet)
        f.append(tube(f"Head_Jaw{k+1}", pts, CB, frenet=False))
    # denture platforms: a flat U inside a bar (jaw below, cheek above), a little forward of it and
    # DENTURE_DROP away from it, tied to the bar's tube by thin rods on each side.  The upper one is
    # the lower one flipped: lip on its underside, end-lips hanging down, rods going up.
    def denture(tag, zp, bar_paths, flip):
        dd = _denture_dims(ctx, hp)
        x_arm, y_arm0, yp = dd["x_arm"], dd["y_arm0"], dd["yp"]
        upath = _denture_upath(x_arm, y_arm0, yp, zp, dd["nose"])
        w_n, t_n, rw_n, rh_n = dd["w_n"], dd["t_n"], dd["rw_n"], dd["rh_n"]
        # platform with a lip along its outer edge (one L-section sweep: a separate lip flush with the
        # edge gave coplanar faces and the fuse dropped the body)
        f.append(flat_tube(f"Head_Denture{tag}", upath, w_n, t_n, lip=(rw_n, rh_n), flip=flip))
        # lips across the open ends of the arms: a hair wider and further back than the platform, so no
        # face is coplanar with it; they stand on the platform (lower) or hang from it (upper)
        eps = ctx.s("CageBar") * 0.02
        z_face = z_cn + zp * Rn + (-t_n / 2 if flip else t_n / 2)
        z_box = z_face - rh_n if flip else z_face - rh_n * 0.3
        for k, sx in enumerate((-1, 1)):
            f.append(ctx.box(f"Head_Denture{tag}Back{k+1}", w_n + 2 * eps, rw_n + eps, rh_n + rh_n * 0.3,
                             x=x_arm * sx * Rn - w_n / 2 - eps, y=y_arm0 * Rn - eps, z=z_box))
        # tie rods from the platform's outer edge to the bar's tube
        def at_y(path, y, sx):
            return min((p for p in path if p.x * sx > 0.05), key=lambda p: abs(p.y - y))
        for k, sx in enumerate((-1, 1)):
            bar_pts = bar_paths[sx]
            for j, yy in enumerate((y_post - 0.12, y_post + 0.12)):
                A = at_y(upath, yy, sx); B = at_y(bar_pts, yy, sx)
                A = V(A.x * Rn + sx * w_n / 2, A.y * Rn, z_cn + A.z * Rn); B = V(B.x * Rn, B.y * Rn, z_cn + B.z * Rn)
                # barely embedded at the platform edge (the rod slopes, so a deep embed surfaces through the
                # top); ends on the bar tube's centreline
                f.append(rod(f"Head_Denture{tag}Rod{k+1}{j+1}", A, B, mul(S("CageBar"), DENTURE_ROD), ctx.s("CageBar") * 0.12))
    if "jaw" not in SKIP and "denture" not in SKIP:
        denture("", zj - DENTURE_DROP, jaw_paths, flip=False)              # lower: above the jaw bar
    if "cheek" not in SKIP and "denture" not in SKIP and "upper" not in SKIP:
        denture("U", z_front - DENTURE_UPPER_DROP, cheek_paths, flip=True)  # upper: DENTURE_UPPER_DROP from the cheek bar
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

def build_mouth(ctx):
    """The mouth insert: gums, teeth and a tongue as one organic piece that drops into the lower
    denture tray (inside its lip) and prints on its flat base.  Head frame, numeric geometry.
    Gums = a domed horseshoe along the tray's U; teeth = uneven, slightly leaning cones on the
    ridge with fangs at the corners; tongue = a flattened ellipsoid filling the U with its tip
    lifted and a groove down the middle.  The arms end in a diagonal tear just ahead of the
    tray's end-lips; the back is otherwise plain."""
    import random
    hp = _head_plan(ctx); dd = _denture_dims(ctx, hp)
    Rn, z_cn = hp["Rn"], hp["z_cn"]
    zp = hp["zj"] - DENTURE_DROP                                  # lower platform centre (unit)
    z_top = z_cn + zp * Rn + dd["t_n"] / 2                        # platform top = the insert's base plane (mm)
    clear = ctx.s("CageBar") * MOUTH_CLEAR
    gw = dd["w_n"] - dd["rw_n"] - clear                           # gum width: the platform less its lip and a clearance
    gh = gw * MOUTH_GUM_H
    off = (dd["rw_n"] + clear) / 2 / Rn                           # gum centreline sits this far inside the platform's
    x_arm, yp, nose = dd["x_arm"] - off, dd["yp"] - off, dd["nose"] - off
    y0 = dd["y_arm0"] + (dd["rw_n"] + clear) / Rn                  # arms start clear of the end-lips
    pts = [V(p.x * Rn, p.y * Rn, z_top) for p in _denture_upath(x_arm, y0, yp, zp, nose)]
    f = []
    # gum ridge: an ellipse (gum width x 2*gum height) swept along the U with its centre on the base
    # plane; the lower half is cut away below, leaving a domed ridge with a flat bottom
    bs = Part.BSplineCurve(); bs.interpolate(pts)
    spine = ctx.obj("Part::Feature", "Mouth_GumSpine"); spine.Shape = Part.Wire(bs.toShape()); spine.Visibility = False
    d = bs.tangent(bs.FirstParameter)[0]
    e1 = V(0, 0, 1).cross(d); e1.normalize(); e2 = d.cross(e1); e2.normalize()
    # (Part.Ellipse wants major >= minor; when the ridge is taller than half its width the major
    #  axis goes vertical, so the frame's X is swapped to e2 -- still right-handed: e2 x -e1 = d)
    a1, a2 = (e1, e2) if gw / 2 >= gh else (e2, -e1)
    ell = Part.Ellipse(V(0, 0, 0), max(gw / 2, gh), min(gw / 2, gh)).toShape()
    ell.Placement = App.Placement(pts[0], App.Rotation(App.Matrix(a1.x, a2.x, d.x, 0, a1.y, a2.y, d.y, 0, a1.z, a2.z, d.z, 0, 0, 0, 0, 1)))
    prof = ctx.obj("Part::Feature", "Mouth_GumProfile"); prof.Shape = Part.Wire([ell]); prof.Visibility = False
    gum = ctx.obj("Part::Sweep", "Mouth_Gum")
    gum.Sections = [prof]; gum.Spine = (spine, ["Edge1"]); gum.Solid = True; gum.Frenet = False
    f.append(gum)
    # teeth: the human lower arch from the midline back -- central and lateral incisors (blades),
    # cuspid (a blunt narrower blade), two bicuspids (one groove), two molars (two grooves and a
    # fossa); no third molars.  Widths are the human proportions scaled so the arch fills the arm
    # and runs MOUTH_ARCH_OVERSHOOT past the back plane (the last molar is cut flush there); each
    # tooth roots at the base plane and leans a little.
    seg = [(pts[i + 1] - pts[i]).Length for i in range(len(pts) - 1)]
    total = sum(seg)
    Cc = V(0, sum(p.y for p in pts) / len(pts), z_top)              # inside the U, for the outward direction
    def at_arc(a):
        acc, j = 0.0, 0
        while j < len(seg) - 1 and acc + seg[j] < a:
            acc += seg[j]; j += 1
        P = pts[j] + (pts[j + 1] - pts[j]) * ((a - acc) / seg[j])
        t = pts[j + 1] - pts[j]; t.normalize()
        return P, t
    rng = random.Random(11)
    teeth = []                                                       # numeric tooth solids (own part)
    w_alloc, frames = [], []
    z_base = z_top - gw * 0.1                                        # roots run to the base plane (trimmed below)
    z_ref = z_top + gw * MOUTH_TOOTH_BASE                            # crown heights count from here
    half = total / 2 + gw * MOUTH_ARCH_OVERSHOOT
    wsum = sum(w for _, w, _, _ in TEETH)
    for sx in (-1, 1):
        a = total / 2
        for i, (kind, w_h, d_f, h_f) in enumerate(TEETH):
            w = half * w_h / wsum                                    # allotted arc for this tooth
            w_alloc.append(w)
            P, t = at_arc(a + sx * w / 2)
            a += sx * w
            out = P - Cc; out = out - t * out.dot(t); out.normalize()
            up = t.cross(out)
            if up.z < 0:
                t = -t; up = -up
            J = MOUTH_JITTER
            tw = w * 0.92 * (1 + 0.06 * J * (rng.random() - 0.5))       # crown width (gap between teeth) and depth,
            dpt = gw * d_f * (1 + 0.08 * J * (rng.random() - 0.5))      # each a few percent off nominal
            h = z_ref - z_base + gw * h_f * (0.9 + 0.2 * rng.random())   # height from the root plane to the crown top
            if kind == "incisor":
                sh = _tooth(tw, dpt, h, tw * 1.05, dpt * 0.28, bulge=1.04, rnd=0.22, top_r=0.45)   # blunted blade
            elif kind == "cuspid":
                sh = _tooth(tw, dpt, h, tw * 0.55, dpt * 0.34, bulge=1.06, rnd=0.22, top_r=0.45)   # blunt: a normal human jaw, not fangs
            elif kind == "bicuspid":
                sh = _tooth(tw, dpt, h, tw * 0.9, dpt * 0.9, bulge=1.1, rnd=0.25, top_r=0.4, grooves=("x",))
            else:
                sh = _tooth(tw, dpt, h, tw * 0.95, dpt * 0.95, bulge=1.1, rnd=0.3, top_r=0.45, grooves=("x", "y"), fossa=True)
            frame = App.Rotation(App.Matrix(t.x, out.x, up.x, 0, t.y, out.y, up.y, 0, t.z, out.z, up.z, 0, 0, 0, 0, 1))
            lean = App.Rotation(t, -(4 + 8 * rng.random()))         # tops tilt outward
            yaw = App.Rotation(up, 5 * J * (rng.random() - 0.5) * 2)   # a few degrees of twist about the vertical
            shift = out * (gw * 0.05 * J * (rng.random() - 0.5) * 2)  # a little in or out of the ridge line
            sh.Placement = App.Placement(V(P.x, P.y, z_base) + shift, lean * yaw * frame)
            teeth.append(sh); frames.append((V(P.x, P.y, z_base), t, out))
    # mouth floor and tongue.  The floor is a thin plate filling the U between the gums (it is what
    # ties the tongue to the gums); the tongue is a flattened ellipsoid in front, full-width slab
    # behind, reaching MOUTH_TONGUE_TIP_MM short of the teeth's inner faces at the front and sides,
    # pitched up so the tip lifts, cut off square at the back, with a groove down the middle
    x_in = x_arm * Rn - gw / 2                                       # inner face of the gum arms
    y_front = (yp + nose) * Rn - gw / 2                              # inner face of the gum at the nose
    y_back = y0 * Rn
    tf = gw * MOUTH_FLOOR_T
    floor_pts = [V(p.x * Rn, p.y * Rn, z_top) for p in _denture_upath(x_arm - gw * 0.35 / Rn, y0, yp - gw * 0.35 / Rn, zp, nose - gw * 0.35 / Rn)]
    floor_w = Part.Wire(Part.makePolygon(floor_pts + [floor_pts[0]]))
    floor = ctx.obj("Part::Feature", "Mouth_Floor", Shape=Part.Face(floor_w).extrude(V(0, 0, tf)))
    floor.Placement = App.Placement(V(0, 0, -gw * 0.1), App.Rotation())   # starts below the base plane, trimmed
    f.append(floor)
    lift_r = math.radians(MOUTH_TONGUE_LIFT_DEG)
    z_goal = gw * (MOUTH_TOOTH_BASE + TEETH[MOUTH_TONGUE_TOOTH][3])           # crown top of the reference tooth, above the base
    # front: the tip stops MOUTH_TONGUE_TIP_MM short of the central incisors' inner (lingual) faces,
    # which sit half the gum width less half the incisor depth inside the gum's inner face
    y_tip = y_front + gw * (0.5 - TEETH[0][2] / 2) - MOUTH_TONGUE_TIP_MM
    L = y_tip - y_back
    yc = y_back + L * MOUTH_TONGUE_BACK
    rx = x_in + gw * (0.5 - TEETH[-1][2] / 2) - MOUTH_TONGUE_TIP_MM       # out to the molars' lingual faces
    ry = (y_tip - yc) / math.cos(lift_r)
    # thickness: the tilted ellipsoid peaks at 0.15 tt + sqrt(tt^2 cos^2 + ry^2 sin^2) above the base -> iterate
    tt = z_goal
    for _ in range(20):
        peak = 0.15 * tt + math.sqrt(tt ** 2 * math.cos(lift_r) ** 2 + ry ** 2 * math.sin(lift_r) ** 2)
        tt *= z_goal / peak
    lift = App.Rotation(V(1, 0, 0), MOUTH_TONGUE_LIFT_DEG)
    zc = z_top + tt * 0.15
    tongue = ctx.ellipsoid("Mouth_Tongue", tt, rx, ry, x=0, y=yc, z=zc, rot=lift)
    f.append(tongue)
    # behind its centre the tongue keeps the full section (no taper) back through the cut-off: an
    # elliptical slab with the ellipsoid's mid-section, extruded backward, sharing the same pitch
    a_, b_ = max(rx, tt), min(rx, tt)
    sec = Part.Face(Part.Wire(Part.Ellipse(V(0, 0, 0), a_, b_).toShape()))
    slab = sec.extrude(V(0, 0, yc - y_back + gw))
    swap = App.Rotation(V(0, 0, 1), 90) if tt > rx else App.Rotation()  # major axis must be X: swap if the tongue is taller than wide
    slab.Placement = App.Placement(V(0, yc, zc), lift * App.Rotation(V(1, 0, 0), 90) * swap)
    f.append(ctx.obj("Part::Feature", "Mouth_TongueBack", Shape=slab))
    # ---- two printable pieces in the same frame: the soft body (gums + floor + tongue) and the
    # teeth.  The teeth are subtracted from the soft body so each sits in an exact socket, and the
    # socket rims are filleted so the gum wraps the tooth (gingival margin) ------------------
    soft = ctx.fuse("Mouth_Soft0", f)
    # groove down the middle of the tongue: a cylinder along its long axis (same pitch), sunk a
    # little so it meets the surface at a shallow angle
    rgr = gw * MOUTH_GROOVE_R
    top_c = V(0, yc, zc + tt + rgr - gw * MOUTH_GROOVE_DEPTH)          # groove axis: above the tongue's top by radius - depth
    gr = ctx.cylinder("Mouth_Groove", rgr, (yc - y_back + gw) + ry * 1.05)
    gr.Placement = App.Placement(top_c - lift.multVec(V(0, yc - y_back + gw, 0)), lift * App.Rotation(V(1, 0, 0), -90))
    soft = ctx.cut("Mouth_Soft1", soft, gr)
    # flat base: everything below the platform top goes; the back is one square cut at the gum-start
    # line (just inside the tray's end-lips), a hair ahead of the floor plate's back edge so no two
    # faces are coplanar.  Both cuts apply to the teeth too (roots, the overshooting last molar).
    big = gw * 30
    y_cut = y_back + gw * 0.02
    base_cut = ctx.box("Mouth_BaseCut", big, big, gw * 10, x=-big / 2, y=-big / 2, z=z_top - gw * 10)
    back_cut = ctx.box("Mouth_BackCut", big, big, big, x=-big / 2, y=y_cut - big, z=z_top - big / 2)
    soft = ctx.cut("Mouth_Soft2", soft, base_cut)
    soft = ctx.cut("Mouth_Soft3", soft, back_cut)
    ctx.doc.recompute()
    base_box = Part.makeBox(big, big, gw * 10, V(-big / 2, -big / 2, z_top - gw * 10))
    back_box = Part.makeBox(big, big, big, V(-big / 2, y_cut - big, z_top - big / 2))
    cut_teeth = [t.cut(base_box).cut(back_box) for t in teeth]
    keep = [i for i, t in enumerate(cut_teeth) if not t.isNull() and t.Volume > 1e-9]
    teeth = [cut_teeth[i] for i in keep]; frames = [frames[i] for i in keep]
    teeth_comp = Part.makeCompound(teeth)
    # sockets: subtract the teeth one at a time (a compound tool is less reliable)
    soft_sh = soft.Shape
    gums_sh = soft_sh
    for t in teeth:
        g2 = gums_sh.cut(t)
        if not g2.isNull() and g2.isValid() and g2.Volume < gums_sh.Volume:
            gums_sh = g2
    gums_sh = gums_sh.removeSplitter()
    if len(gums_sh.Solids) > 1:                                      # a socket cut can leave a zero-volume sliver
        gums_sh = max(gums_sh.Solids, key=lambda x: x.Volume)
    # gingival margin: fillet the edges where the gum surface meets a tooth's cheek or tongue face
    # (on that tooth's surface, on the original gum surface, not on the base or back planes, and on
    # the long sides of the tooth -- the edges between neighbouring teeth have no room for a round)
    def mid(e):
        return e.valueAt(e.FirstParameter + (e.LastParameter - e.FirstParameter) / 2)
    tol = gw * 1e-3
    done, failed = 0, 0
    for t, (P, td, out) in (zip(teeth, frames) if MOUTH_MARGIN_R > 0 else ()):
        rim = []
        for e in gums_sh.Edges:
            m = mid(e)
            if abs(m.z - z_top) < tol or abs(m.y - y_cut) < tol:
                continue
            if t.distToShape(Part.Vertex(m))[0] > tol or soft_sh.isInside(m, tol, False):
                continue
            r = m - P
            if abs(r.dot(out)) > abs(r.dot(td)):                     # cheek / tongue side, not between teeth
                rim.append(e)
        if not rim:
            continue
        err = ""
        for k in (1.0, 0.6, 0.35):
            try:
                f2 = gums_sh.makeFillet(gw * MOUTH_MARGIN_R * k, rim)
                if f2.isValid() and 0.9 * gums_sh.Volume < f2.Volume <= gums_sh.Volume * 1.001 and len(f2.Solids) == 1:
                    gums_sh = f2; done += 1; break
            except Exception as ex:
                err = str(ex)
        else:
            failed += 1
            if failed == 1:
                print(f"[mimic]   Mouth: first margin fillet failure: {len(rim)} rim edges: {err or 'invalid result'}")
    if failed:
        print(f"[mimic]   Mouth: gum margin filleted round {done} teeth, failed on {failed}")
    gums = ctx.obj("Part::Feature", "MouthGums", Shape=gums_sh)
    teeth_o = ctx.obj("Part::Feature", "MouthTeeth", Shape=teeth_comp)
    return [("MouthGums", gums), ("MouthTeeth", teeth_o)]

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

def _blade_toe(ctx, name, x0, yaw, y_face, y_root, y_tip, H, instep, w0, apex, rise, sink, y_block=None):
    """One toe as a smooth lofted blade (numeric).  Knife section: flat top, short vertical sides,
    sharp bottom edge.  Bottom edge lies on the sole plane inside the foot, leaves it at the front face,
    arcs up to `rise` at `apex` (fraction of the exposed length) and comes down to a point at y_tip.
    Top edge follows the instep surface (sunk by `sink`) and converges to the same point.
    y_block: the solid foot ends here; behind it the blade is buried (bottom sunk under the sole so
    the fuse takes), ahead of it the blade is exposed with its knife edge on the sole."""
    n_in, n_out = 3, 14                      # few inner sections: a smooth loft through many collinear ones wobbles
    y_block = y_face if y_block is None else y_block
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
            # buried stub: shrunk inward by `sink` on every side (the metatarsal's prong has this exact
            # section, and coincident faces break the fuse), reaching the full section at the face
            b = max(0.0, (y_block - y) / (y_block - y_root))
            zb = H - sink * b
            zt = instep(y) + sink + sink * b
        else:
            zt = zb - h_face * (1 - v ** 1.3)                        # height fades to a point at the tip
        h = max(zb - zt, 0.0)
        w = w0 * (1 - v) ** 0.7 - (2 * sink * b if v <= 0 else 0.0)
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
    footprint is a rounded heel and parallel sides (FOOT_ANKLE_W wide).  The solid block ends
    FOOT_BLOCK ahead of the ankle (top edges filleted, front face sharp); the metatarsal is a ruled
    loft from the block's section to the toes' combined root section (outer sides up from the
    ground, tops with a web dipping between the toes, sole across) and the three blade toes start on
    that face and curve down to points on the sole plane."""
    face, face_n = _face(ctx, "AnkleBall")
    H, FL, FW, TW = S("FootHeight"), S("FootLength"), S("FootWidth"), S("ToeWidth")
    # instep top at the ankle: FOOT_ANKLE_H of the way from the sole up to just under the ankle face
    top = sub(H, mul(sub(H, mul(face, 0.25)), FOOT_ANKLE_H))
    heel, toe = mul(FL, FOOT_HEEL), sub(FL, mul(FL, FOOT_HEEL))
    ra = mul(FW, FOOT_ANKLE_W / 2)               # half width of the foot (heel rounding radius too)
    rt = half(FW)                                # sets where the front face is (unchanged from the tapered foot)
    # instep: two wedges meeting at the ankle, sloping down to sole height at each end
    sole_top_t, sole_top_h = mul(H, 0.65), mul(H, 0.55)
    f = [_wedge(ctx, "Foot_Instep", (neg(FW), FW), ("0 mm", toe), (top, H), (neg(FW), FW), (sole_top_t, H)),
         _wedge(ctx, "Foot_Heel", (neg(FW), FW), ("0 mm", heel), (top, H), (neg(FW), FW), (sole_top_h, H),
                rot=App.Rotation(V(0, 0, 1), 180))]
    body = ctx.fuse("Foot_Body", f)
    # footprint: a rounded heel and a constant-width slab to the block's front face, through the full height
    yh, yt = neg(sub(heel, ra)), sub(toe, rt)
    yb = mul(FL, FOOT_BLOCK)
    fp = [ctx.cylinder("Foot_PrintHeel", ra, H, y=yh),
          ctx.box("Foot_PrintMid", mul(ra, 2), sub(yb, yh), H, x=neg(ra), y=yh)]
    print_ = ctx.fuse("Foot_Print", fp)
    body = ctx.common("Foot_Shaped", body, print_)
    # fillet every edge except those lying in the sole plane or in the block's front face
    ctx.doc.recompute()
    H_n = ctx.s("FootHeight")
    yb_n = ctx.s("FootLength") * FOOT_BLOCK
    edges = [(i + 1, FOOT_FILLET * ctx.s("FootWidth"), FOOT_FILLET * ctx.s("FootWidth"))
             for i, e in enumerate(body.Shape.Edges)
             if not all(abs(vx.Point.z - H_n) < 0.01 for vx in e.Vertexes)
             and not all(abs(vx.Point.y - yb_n) < 0.01 for vx in e.Vertexes)]
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
    x_out = FW_n * FOOT_ANKLE_W / 2 - w0 / 2     # outer toes' outer faces flush with the foot's sides
    for k, (x0, yaw) in enumerate(((-x_out, TOE_FAN_DEG), (0.0, 0.0), (x_out, -TOE_FAN_DEG))):
        # the toe starts ON the metatarsal's front face (a hair inside, so the fuse takes), no buried run
        f.append(_blade_toe(ctx, f"Foot_Toe{k+1}", x0, yaw, yt_n, yt_n - 0.02 * FL_n, yt_n + TOE_REACH * FL_n,
                            H_n, instep, w0, TOE_APEX, TOE_RISE * H_n, 0.01 * FW_n))
    # metatarsal: one ruled loft from the block's section (just inside its front face) to the toes'
    # combined root section: the outer toe's outer side up from the ground, across the tops with a
    # cosine web dipping between the toes, down the inner toe's side, and back along the sole.
    # The block section is the same point list pushed out to the block's rectangle (sides at +/-ra,
    # top flat on the instep, rounded top corners at the block's fillet radius), so the loft is
    # smooth with no extra edges and the toes carry straight on from its front face.
    ra_n = FW_n * FOOT_ANKLE_W / 2
    rf = FOOT_FILLET * FW_n
    sink_n = 0.01 * FW_n
    xs = [-x_out, 0.0, x_out]
    def section(y, at_toes):
        zt = instep(y) + (sink_n if at_toes else 0.0)                   # toe top at the root (see _blade_toe, v = 0); block top exactly on the instep
        h = H_n - zt                                                    # toe height there
        dip = FOOT_WEB * h if at_toes else 0.0
        side = (x_out + w0 / 2) if at_toes else ra_n                    # outer faces: toe side or block side
        r = 0.02 * w0 if at_toes else rf                                # top-corner rounding
        pts = [V(-x_out if at_toes else -ra_n, y, H_n)]                 # start: outer toe's knife point / block's sole corner
        pts.append(V(-side, y, zt + 0.35 * h))                          # up the lower slant to the vertical side
        NA = 8
        for j in range(NA):                                             # rounded top-left corner
            a_ = math.pi / 2 * j / NA
            pts.append(V(-side + r - r * math.cos(a_), y, zt + r - r * math.sin(a_)))
        for k, xk in enumerate(xs):                                     # across the tops, dipping between toes
            if k > 0:
                pts.append(V(xk - w0 / 2, y, zt))
            if k < 2:
                pts.append(V(xk + w0 / 2, y, zt))
                xa, xb = xk + w0 / 2, xs[k + 1] - w0 / 2
                for j in range(1, 6):
                    u = j / 6
                    pts.append(V(xa + (xb - xa) * u, y, zt + dip * (1 - math.cos(2 * math.pi * u)) / 2))
        for j in range(NA):                                             # rounded top-right corner
            a_ = math.pi / 2 * (j + 1) / NA
            pts.append(V(side - r + r * math.sin(a_), y, zt + r - r * math.cos(a_)))
        pts.append(V(side, y, zt + 0.35 * h))
        pts.append(V(x_out if at_toes else ra_n, y, H_n))               # down the inner toe's slant to the ground
        pts.append(pts[0])                                              # back along the sole
        return Part.makePolygon(pts)
    meta = Part.makeLoft([section(yb_n - 0.03 * FL_n, False), section(yt_n, True)], True, True)
    f.append(ctx.obj("Part::Feature", "Foot_Metatarsal", Shape=meta))
    body = ctx.fuse("Foot_All", f)
    socks, _ = ctx.peg_pattern("Foot_Sockets", face, face_n, "socket")
    foot = ctx.cut("Foot", body, socks)
    foot.Label = "Foot"
    return [("Foot", foot)]
