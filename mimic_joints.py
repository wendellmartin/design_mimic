"""Joint geometry for mating faces: bayonet, collet peg, spigot.

Chosen 2026-10-01 after printing the JointTest coupons.  What the coupons showed:

* the **bayonet** works well -- it is all solid material in shear, has nothing thin to snap,
  assembles by hand and (with the helical ramp) pulls itself tight and stays put;
* the **collet peg** at 0.55 mm interference "set in and I can't get it out" -- an excellent
  PERMANENT joint -- but two of them snapped just getting the print off the bed, so it is a poor
  choice anywhere that gets handled or taken apart.

So: **bayonet for joints that come apart, collet for joints that are permanent.**  The splits
inside a long bone are permanent by definition (they exist only because the bone is longer than
the build cube and are meant to read as one piece), so those get collets.  Everything in the
chain -- balls, neck, feet, hands -- gets a bayonet where the face is big enough.

Like the peg before it, all of this is ABSOLUTE millimetres, except that the bayonet grows a
little with the mating face so big faces get a stronger joint.  Geometry is numeric (built at the
run's scale) rather than expression-driven, like the other swept/lofted detail in this project.

Frames match the old peg/socket exactly, so this is a drop-in for `peg_pattern`: the male
protrudes local +Z from the mating plane, the female is a cavity running local +Z into the
material, and the two mate when the faces meet.

The bayonet's LOCKED position is the modelled pose.  The entry slots sit BAYO_TURN back from it,
so you offer the part up rotated a quarter turn anticlockwise and turn it forward into place.
"""
import math
import FreeCAD as App
import Part

V = App.Vector

WALL = 1.2              # material left outside the socket's outer wall

# ---- bayonet (proven on the coupon at R = 4.0) ---------------------------------
BAYO_R_MIN = 3.5                    # 3.5 so a 14 mm face (the ankle) still gets a bayonet and
                                    # the foot stays removable; below ~3.0 the lugs and their
                                    # 0.15 mm channel clearances stop being printable
# The joint grows with the face so a life-size limb does not hang off the same 14 mm boss the
# quarter-scale one uses -- but the CLEARANCES below stay absolute, because they are printer
# tolerances, not dimensions.  The caps are written so that every face on the quarter-scale
# figure (14-22 mm) comes out exactly as it did before: there 0.18 * face < 7 and 0.5 * face <= 11.
BAYO_R_CAP, BAYO_R_FRAC = 7.0, 0.18
BAYO_LEN_CAP, BAYO_LEN_FRAC = 11.0, 0.5
BAYO_LEN_MIN = 8.0
BAYO_CLEAR = 0.25       # radial clearance, boss to bore
BAYO_CHAN_CLEAR = 0.15  # lug clearance in the circumferential channel
BAYO_TURN = 90.0        # degrees to lock
BAYO_SWEEP_EXTRA = 18.0 # calibrated so the lug's leading edge hits the end face AT BAYO_TURN
BAYO_RAMP = 0.5         # the run climbs this much over the locking turn, drawing the joint in
BAYO_PRELOAD = 0.10     # of that, how much is left after the faces meet: the wedge
BAYO_STEP = 3.0         # the ramp is built from sectors this many degrees wide

# ---- collet peg (proven on the coupon; permanent joints only) ------------------
COLLET_OD_R = 4.0
COLLET_WALL = 2.0       # thicker than the coupon's 1.7: two snapped during handling
COLLET_LEN = 11.0
COLLET_BORE_CLEAR = 0.15
COLLET_SLIT = 0.8
COLLET_SLIT_FLOOR = 1.5
COLLET_FACE_Z = 8.0     # flat retaining face height
COLLET_TIP_R = 3.4
COLLET_GROOVE = 0.3
COLLET_INTERFERENCE = 0.55   # his pick: "set in and I can't get it out"
COLLET_EMBED = 2.5
COLLET_ROOT = 1.2       # conical root fillet, to take the stress riser off the base

# ---- spigot: a plain register for faces too small for either, glued ------------
SPIGOT_LEN = 6.0
SPIGOT_CLEAR = 0.12

BAYO_MIN_FACE = 2 * ((BAYO_R_MIN * 1.4 + 0.6) + BAYO_CLEAR + WALL)
COLLET_MIN_FACE = 2 * (COLLET_OD_R + COLLET_BORE_CLEAR + COLLET_INTERFERENCE + COLLET_GROOVE + WALL)
SPIGOT_MIN_FACE = 7.0


def kind_for(face_num, permanent=False):
    """Which mechanism a mating face of this diameter gets.  None = too small for anything, leave
    the faces flat and glue them."""
    if permanent:
        return "collet" if face_num >= COLLET_MIN_FACE else ("spigot" if face_num >= SPIGOT_MIN_FACE else None)
    if face_num >= BAYO_MIN_FACE:
        return "bayo"
    if face_num >= COLLET_MIN_FACE:
        return "collet"
    return "spigot" if face_num >= SPIGOT_MIN_FACE else None


# ============================================================ bayonet
def _bayo_dims(face_num):
    r_out = face_num / 2 - WALL
    r_max = max(BAYO_R_CAP, BAYO_R_FRAC * face_num)
    len_max = max(BAYO_LEN_CAP, BAYO_LEN_FRAC * face_num)
    R = min(max((r_out - 0.6) / 1.4, BAYO_R_MIN), r_max)
    length = min(max(2.0 * R, BAYO_LEN_MIN), len_max)
    lug_r = 0.35 * R
    # the lug has to sit clear of the crown chamfer; a fixed setback let it grow past the
    # boss top on big faces and the chamfer cut sliced it off as a separate solid
    return dict(R=R, length=length, lug_r=lug_r, lug_out=0.4 * R, lug_z=length - lug_r - 1.2)


def _bayo_male(face_num):
    d = _bayo_dims(face_num)
    R, length = d["R"], d["length"]
    body = Part.makeCylinder(R, length + 2.0, V(0, 0, -2.0))
    for ang in (0, 180):
        lug = Part.makeCylinder(d["lug_r"], R + d["lug_out"], V(0, 0, d["lug_z"]), V(1, 0, 0))
        lug.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        body = body.fuse(lug)
    # chamfer the crown so it starts into the bore
    top = Part.makeCone(R, R - 0.8, 0.8, V(0, 0, length - 0.8))
    body = body.cut(Part.makeCylinder(R + 3, 1.0, V(0, 0, length - 0.8)).cut(top))
    return body.removeSplitter()


def _bayo_run(r_in, r_out, lug_w, z0, sweep):
    """The circumferential run as a shallow helix, so turning the part draws it in and the last
    few degrees wedge.  Built from overlapping sectors climbing in z: makePipeShell along a
    low-pitch helix silently returns a CONSTANT-height channel instead of a ramp."""
    per_deg = BAYO_RAMP / BAYO_TURN
    n = max(1, int(round(sweep / BAYO_STEP)))
    run = None
    for i in range(n):
        a0, a1 = sweep * i / n, sweep * (i + 1) / n
        z = z0 + per_deg * (a0 + a1) / 2 - lug_w / 2
        seg = Part.makeCylinder(r_out, lug_w, V(0, 0, z), V(0, 0, 1), (a1 - a0) + 0.6)
        seg = seg.cut(Part.makeCylinder(r_in, lug_w + 1.0, V(0, 0, z - 0.5)))
        seg.rotate(V(0, 0, 0), V(0, 0, 1), a0)
        run = seg if run is None else run.fuse(seg)
    return run


def _bayo_female(face_num):
    """Bore, an entry slot per lug, and the ramped run.  Built with the entry at azimuth 0 and the
    lock at BAYO_TURN, then rotated back so the LOCK lands at azimuth 0 -- the modelled pose."""
    d = _bayo_dims(face_num)
    R, length = d["R"], d["length"]
    r_in = R + BAYO_CLEAR
    r_out = R + d["lug_out"] + 0.6
    lug_w = 2 * d["lug_r"] + 2 * BAYO_CHAN_CLEAR
    sweep = BAYO_TURN + BAYO_SWEEP_EXTRA
    # the channel floor under the lug is what sets how deep the part sits, so this has to allow
    # for the lug's clearance inside the channel or that slack eats the ramp's whole draw
    z_mid0 = d["lug_z"] - d["lug_r"] + lug_w / 2 - BAYO_RAMP + BAYO_PRELOAD
    t = Part.makeCylinder(r_in, length + 1.0, V(0, 0, -0.5))
    for ang in (0, 180):
        entry = Part.makeBox(r_out, lug_w, z_mid0 + lug_w + 1.0, V(0, -lug_w / 2, -0.5))
        entry.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        t = t.fuse(entry)
        run = _bayo_run(r_in, r_out, lug_w, z_mid0, sweep)
        run.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        t = t.fuse(run)
    t.rotate(V(0, 0, 0), V(0, 0, 1), -BAYO_TURN)
    return t.removeSplitter()


# ============================================================ collet peg
def _collet_male(face_num):
    r_barb = COLLET_OD_R + COLLET_BORE_CLEAR + COLLET_INTERFERENCE
    sh = Part.makeCylinder(COLLET_OD_R, COLLET_FACE_Z + COLLET_EMBED, V(0, 0, -COLLET_EMBED))
    sh = sh.fuse(Part.makeCone(r_barb, COLLET_TIP_R, COLLET_LEN - COLLET_FACE_Z, V(0, 0, COLLET_FACE_Z)))
    sh = sh.fuse(Part.makeCone(COLLET_OD_R + COLLET_ROOT, COLLET_OD_R, COLLET_ROOT, V(0, 0, 0)))
    sh = sh.cut(Part.makeCylinder(COLLET_OD_R - COLLET_WALL, COLLET_LEN + 1.0, V(0, 0, 0.0)))
    for ang in (0, 90):
        s = Part.makeBox(COLLET_SLIT, 4 * COLLET_OD_R, COLLET_LEN - COLLET_SLIT_FLOOR + 0.5,
                         V(-COLLET_SLIT / 2, -2 * COLLET_OD_R, COLLET_SLIT_FLOOR))
        s.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        sh = sh.cut(s)
    return sh.removeSplitter()


def _collet_female(face_num):
    r_barb = COLLET_OD_R + COLLET_BORE_CLEAR + COLLET_INTERFERENCE
    r_bore = COLLET_OD_R + COLLET_BORE_CLEAR
    t = Part.makeCylinder(r_bore, COLLET_FACE_Z + 0.5, V(0, 0, -0.5))
    t = t.fuse(Part.makeCylinder(r_barb + COLLET_GROOVE, COLLET_LEN + 0.4 - COLLET_FACE_Z,
                                 V(0, 0, COLLET_FACE_Z)))
    # clearance for the root fillet so the faces still meet
    t = t.fuse(Part.makeCone(COLLET_OD_R + COLLET_ROOT + 0.15, COLLET_OD_R + 0.15, COLLET_ROOT, V(0, 0, -0.01)))
    return t.removeSplitter()


# ============================================================ spigot
def _spigot_r(face_num):
    return max(1.6, min(face_num / 2 - WALL - 0.5, 3.0))


def _spigot_male(face_num):
    r = _spigot_r(face_num)
    sh = Part.makeCylinder(r, SPIGOT_LEN + 1.5, V(0, 0, -1.5))
    top = Part.makeCone(r, r - 0.6, 0.6, V(0, 0, SPIGOT_LEN - 0.6))
    return sh.cut(Part.makeCylinder(r + 2, 0.8, V(0, 0, SPIGOT_LEN - 0.6)).cut(top)).removeSplitter()


def _spigot_female(face_num):
    r = _spigot_r(face_num) + SPIGOT_CLEAR
    return Part.makeCylinder(r, SPIGOT_LEN + 1.0, V(0, 0, -0.5))


# ============================================================ entry point
_MALE = {"bayo": _bayo_male, "collet": _collet_male, "spigot": _spigot_male}
_FEMALE = {"bayo": _bayo_female, "collet": _collet_female, "spigot": _spigot_female}


def shape(kind, male, face_num):
    """The joint feature for a mating face of this diameter: a solid to fuse on (male) or a cavity
    to cut out (female), protruding / running along local +Z from the mating plane at z = 0."""
    return (_MALE if male else _FEMALE)[kind](face_num)


def envelope(face_num, permanent=False):
    """(outer radius, depth) the joint occupies, so a caller can make sure there is material for
    it -- a socket cut into a hollow strut will otherwise sever its end cup."""
    k = kind_for(face_num, permanent)
    if k == "bayo":
        d = _bayo_dims(face_num)
        return d["R"] + d["lug_out"] + 0.6, d["length"] + 1.0
    if k == "collet":
        return COLLET_OD_R + COLLET_BORE_CLEAR + COLLET_INTERFERENCE + COLLET_GROOVE, COLLET_LEN + 0.4
    if k == "spigot":
        return _spigot_r(face_num) + SPIGOT_CLEAR, SPIGOT_LEN + 1.0
    return 0.0, 0.0


def describe(face_num, permanent=False):
    k = kind_for(face_num, permanent)
    if k == "bayo":
        d = _bayo_dims(face_num)
        return f"bayo R={d['R']:.1f} len={d['length']:.1f}"
    if k == "collet":
        return f"collet OD={2*COLLET_OD_R:.0f} int={COLLET_INTERFERENCE}"
    return k or "flat (glue)"
