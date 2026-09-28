"""Joint test coupons: one small pair per locking mechanism, printed and clicked by hand.

Everything here is ABSOLUTE millimetres (like the peg itself) -- these are test pieces, not
scaled parts.  Each male coupon is a plate whose top face is z = 0 with its feature standing up
in +Z; each female coupon is a plate with the mating cavity opening upward at z = 0.  So both
print plate-down with no supports, and the cavity is the male feature (grown by a clearance)
rotated 180 deg about X -- the pose it will actually be in when mated, so handed features
(threads, bayonet lugs) match.

Raised dots on the plate identify a variant (one dot = first in the series).

Round 2 (2026-09-28), from printing round 1:
  SnapB  round 1's 4 mm solid peg locked best at 0.30 mm but the fingers snapped off.  Now an
         8 mm COLLET: a tube split into four fingers, so the fingers are twice as wide (they do
         not break) and bend on a 1.7 mm wall instead of a solid 2 mm radius (they flex much
         further).  Interferences moved up accordingly.
  Screw  round 1 cross-threaded and had to be forced.  Now an unthreaded PILOT at the tip that
         squares the axis before the thread can touch, a countersink at the female mouth and a
         chamfer collar at the male root (which is also what stopped it snapping off).
  Bayo   round 1 jammed at ~80 deg: the circumferential sector swept BAYO_TURN + 12, but the lug
         is ~18 deg wide at the bore, so the lug's leading edge hit the end of the sector before
         its centre reached 90.  The sweep is now computed from the lug's own angular width, so
         the sector ends exactly at BAYO_TURN and that end face is the hard stop.  The detent is
         a shallow dome on the channel floor instead of a 0.45 mm post that nothing could flex past.
  Dove   round 1 was closed at both ends, so there was no way to slide it together.  The groove is
         now open at the plate's front edge and stops at the back.
  Magnet dropped -- he wants a stronger hold.
"""
import math
import FreeCAD as App
import Part

V = App.Vector

PLATE = 20.0            # coupon plate, mm square
PLATE_H = 5.0           # male plate thickness
DOT_R, DOT_H = 0.7, 0.6

# ---- split collet peg (the tuning matrix) --------------------------------------
SNAPB_OD_R = 4.0        # 8 mm collet (round 1 was 4 mm and the fingers broke)
SNAPB_ID_R = 2.3        # through bore -> 1.7 mm wall, ~4 perimeters at 0.4 mm nozzle
SNAPB_LEN = 11.0        # protruding length
SNAPB_BORE_CLEAR = 0.15 # socket bore over the collet OD: this guides the peg
SNAPB_SLIT = 0.8        # cross-slit width (two perimeters)
SNAPB_SLIT_FLOOR = 1.0  # slits stop this far above the mating plane
SNAPB_FACE = 8.0        # flat retaining face height above the mating plane
SNAPB_TIP_R = 3.4       # radius where the lead-in cone meets the tip
SNAPB_GROOVE = 0.3      # socket groove over the barb: room to snap out
SNAPB_EMBED = 2.5       # how far the collet roots into its own plate
# radial interference at the barb = how far each finger flexes on the way in.  A 10 mm long,
# 1.7 mm thick finger takes ~0.78 mm before PLA yields, so the whole series stays elastic.
SNAPB_INTERFERENCE = (0.25, 0.35, 0.45, 0.55, 0.65)

# ---- coarse trapezoidal screw, with a pilot ------------------------------------
SCREW_CORE_R, SCREW_MAJ_R = 3.5, 4.5
SCREW_PITCH = 2.0
SCREW_THREAD_LEN = 5.0
SCREW_PILOT_R = 3.3     # unthreaded tip: squares the axis before the thread bites.  Must be
SCREW_PILOT_LEN = 7.0   # LONGER than the threaded bore, or the threads meet before it registers
SCREW_CLEAR = 0.25
SCREW_MOUTH = 1.2       # chamfer collar at the male root / countersink at the female mouth
SCREW_PLATE_H = 7.0     # thicker male plate: round 1 tore out of a 5 mm one

# ---- bayonet -------------------------------------------------------------------
BAYO_R, BAYO_LEN = 4.0, 8.0
BAYO_LUG_R, BAYO_LUG_OUT = 1.4, 1.6      # lug radius and how far it stands out
BAYO_LUG_Z = 6.2                          # lug centre height
BAYO_TURN = 90.0                          # degrees of twist to lock (the sector ends here)
BAYO_CLEAR = 0.25
BAYO_SWEEP_EXTRA = 18.0    # sector sweeps BAYO_TURN + this; calibrated so the lug's leading
                           # edge meets the end face (the hard stop) exactly at BAYO_TURN
BAYO_DETENT_AT = 55.0      # azimuth of the detent dome.  Both the lug (~15 deg half-width at
                           # this radius) and the dome (~13 deg) are wide, so the dome has to sit
                           # well back for the lug to ride fully over it and drop in behind
BAYO_CHAN_CLEAR = 0.15                    # lug clearance in the circumferential channel
BAYO_RAMP = 0.5                           # the run is a shallow HELIX: over BAYO_TURN it draws the
                                          # male this much deeper, camming the joint tight
BAYO_PRELOAD = 0.10                       # of that draw, how much is left AFTER the plates touch --
                                          # this is the interference the wedge takes up, and it is
                                          # spread over ~18 deg of a 1 deg ramp, so it cannot jam
BAYO_DETENT = 0.0                         # dome detent, superseded by the ramp (0 = none)

# ---- dovetail ------------------------------------------------------------------
DOVE_WB, DOVE_WT, DOVE_H, DOVE_LEN = 6.0, 9.0, 4.0, 16.0
DOVE_CLEAR = 0.2


def _clean(sh):
    """removeSplitter() where OCC allows it -- on the threaded pieces it raises 'Bnd_Box is void',
    and the unmerged faces are only cosmetic."""
    try:
        r = sh.removeSplitter()
        if not r.isNull() and r.isValid() and r.Volume > sh.Volume * 0.99:
            return r
    except Exception:
        pass
    return sh


def _plate(h=PLATE_H, w=PLATE):
    """Coupon plate: top face on z = 0, material below."""
    return Part.makeBox(w, w, h, V(-w / 2, -w / 2, -h))


def _dots(n):
    """n raised dots along the plate's front edge: which variant this is."""
    out = None
    for i in range(n):
        d = Part.makeCylinder(DOT_R, DOT_H, V(-PLATE / 2 + 2.5 + i * 2.2, -PLATE / 2 + 2.0, 0))
        out = d if out is None else out.fuse(d)
    return out


def _mate(cavity):
    """The male feature rotated into the pose it takes when mated (so handed features match)."""
    c = cavity.copy()
    c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    return c


def _female(plate_h, cavity, dots=0):
    body = _plate(plate_h).cut(_mate(cavity))
    if dots:
        body = body.fuse(_dots(dots))
    return _clean(body)


# ============================================================ split collet peg
def _snapb_peg(interference):
    """A tube split into four cantilever fingers by a cross-slit, with a barb at the tip whose
    underside is a flat retaining face and whose top is a shallow lead-in cone.  The interference
    is taken up by bending the thin wall, not by hooping solid material."""
    r_barb = SNAPB_OD_R + SNAPB_BORE_CLEAR + interference
    sh = Part.makeCylinder(SNAPB_OD_R, SNAPB_FACE + SNAPB_EMBED, V(0, 0, -SNAPB_EMBED))
    sh = sh.fuse(Part.makeCone(r_barb, SNAPB_TIP_R, SNAPB_LEN - SNAPB_FACE, V(0, 0, SNAPB_FACE)))
    # hollow from the mating plane up: the root stays solid where it meets the plate
    sh = sh.cut(Part.makeCylinder(SNAPB_ID_R, SNAPB_LEN + 1.0, V(0, 0, 0.0)))
    for ang in (0, 90):
        s = Part.makeBox(SNAPB_SLIT, 4 * SNAPB_OD_R, SNAPB_LEN - SNAPB_SLIT_FLOOR + 0.5,
                         V(-SNAPB_SLIT / 2, -2 * SNAPB_OD_R, SNAPB_SLIT_FLOOR))
        s.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        sh = sh.cut(s)
    return _clean(sh)


def _snapb_cavity(interference):
    """Socket: a bore that guides the collet, then a groove the barb springs out into.  The step
    between them is the ledge the peg's flat face catches under."""
    r_barb = SNAPB_OD_R + SNAPB_BORE_CLEAR + interference
    r_bore = SNAPB_OD_R + SNAPB_BORE_CLEAR
    t = Part.makeCylinder(r_bore, SNAPB_FACE + 0.5, V(0, 0, -0.5))
    t = t.fuse(Part.makeCylinder(r_barb + SNAPB_GROOVE, SNAPB_LEN + 0.4 - SNAPB_FACE, V(0, 0, SNAPB_FACE)))
    return _clean(t)


# ============================================================ coarse screw thread
def _screw_parts(core_r, maj_r, pitch, length):
    """(core cylinder, helical ridge) kept separate: fusing them makes a solid OCC will not
    subtract (the fuse reports valid with zero volume), so the female is cut in two steps."""
    helix = Part.makeHelix(pitch, length, maj_r)
    f = pitch * 0.22                                          # flat half-height at the crest
    root = core_r - 0.6                                       # profile root sunk INSIDE the core: an
    pts = [V(root, 0, -pitch * 0.42), V(maj_r, 0, -f),        # edge exactly on the core surface gives
           V(maj_r, 0, f), V(root, 0, pitch * 0.42)]          # coincident faces and a shredded mesh
    prof = Part.Wire(Part.makePolygon(pts + [pts[0]]))
    ridge = helix.makePipeShell([prof], True, True)
    core = Part.makeCylinder(core_r, length + 4.0, V(0, 0, -4.0))
    return core, ridge


def _screw_male(plate_h):
    """Plate, chamfer collar, threaded section, then the unthreaded pilot that squares the axis
    before the thread can touch.  Fused a step at a time: fusing a pre-fused core+ridge to the
    plate returns an empty solid (same OCC quirk as the female's cut tool)."""
    body = _plate(plate_h)
    core, ridge = _screw_parts(SCREW_CORE_R, SCREW_MAJ_R, SCREW_PITCH, SCREW_THREAD_LEN)
    body = body.fuse(core).fuse(ridge)
    # cut the thread off square at its top: a cone chamfer across the crest leaves
    # self-intersecting facets, and the pilot is what starts the joint now anyway
    body = body.cut(Part.makeBox(4 * PLATE, 4 * PLATE, 4 * PLATE,
                                 V(-2 * PLATE, -2 * PLATE, SCREW_THREAD_LEN)))
    # chamfer collar at the root: spreads the load off the layer line that tore in round 1
    body = body.fuse(Part.makeCone(SCREW_MAJ_R + 1.0, SCREW_MAJ_R, SCREW_MOUTH, V(0, 0, 0)))
    pilot = Part.makeCylinder(SCREW_PILOT_R, SCREW_PILOT_LEN, V(0, 0, SCREW_THREAD_LEN))
    tip_z = SCREW_THREAD_LEN + SCREW_PILOT_LEN
    pilot = pilot.cut(Part.makeCylinder(SCREW_PILOT_R + 1.0, 0.8, V(0, 0, tip_z - 0.8)).cut(
        Part.makeCone(SCREW_PILOT_R, SCREW_PILOT_R - 0.8, 0.8, V(0, 0, tip_z - 0.8))))
    return _clean(body.fuse(pilot))


def _screw_female(plate_h):
    """Countersink, then the threaded bore, then a plain pilot bore deeper than the thread."""
    body = _plate(plate_h)
    core_r, maj_r = SCREW_CORE_R + SCREW_CLEAR, SCREW_MAJ_R + SCREW_CLEAR
    t_len = SCREW_THREAD_LEN + 0.5
    core, ridge = _screw_parts(core_r, maj_r, SCREW_PITCH, t_len)
    # the threaded bore starts below the countersink; the core already runs 4 mm back past z=0
    for t in (core, ridge):
        body = body.cut(_mate(t))
    # both of these must OVERLAP what they meet, never land exactly on it: a countersink whose
    # small end sits on the crest radius, or a pilot bore whose top sits on the core's end plane,
    # gives coincident faces and the mesh comes out in hundreds of pieces
    body = body.cut(_mate(Part.makeCone(maj_r + 1.4, maj_r - 0.3, SCREW_MOUTH, V(0, 0, 0))))
    body = body.cut(_mate(Part.makeCylinder(SCREW_PILOT_R + 0.15, SCREW_PILOT_LEN + 1.5,
                                            V(0, 0, t_len - 1.0))))
    return _clean(body)


# ============================================================ bayonet
def _bayo_male():
    body = Part.makeCylinder(BAYO_R, BAYO_LEN + 2.0, V(0, 0, -2.0))
    for ang in (0, 180):
        lug = Part.makeCylinder(BAYO_LUG_R, BAYO_R + BAYO_LUG_OUT, V(0, 0, BAYO_LUG_Z), V(1, 0, 0))
        lug.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        body = body.fuse(lug)
    top = Part.makeCone(BAYO_R, BAYO_R - 0.8, 0.8, V(0, 0, BAYO_LEN - 0.8))
    body = body.cut(Part.makeCylinder(BAYO_R + 3, 1.0, V(0, 0, BAYO_LEN - 0.8)).cut(top))
    return _clean(body)


def _bayo_run(r_in, r_out, lug_w, z0, sweep, step=3.0):
    """The circumferential run, as a shallow helix instead of a flat sector: rotating the male
    rides its lugs up the ramp and draws the joint tight.  A detent between two rigid solids can
    only jam or be imperceptible; a 1-degree wedge is self-locking and progressive.

    Built as overlapping annular sectors climbing in z, not as a swept helix: makePipeShell on a
    low-pitch helix came back as a constant-height channel spanning the whole envelope.  The step
    is 3 deg, so the staircase rises 0.017 mm at a time -- far under anything a nozzle resolves."""
    per_deg = BAYO_RAMP / BAYO_TURN
    n = max(1, int(round(sweep / step)))
    run = None
    for i in range(n):
        a0 = sweep * i / n
        a1 = sweep * (i + 1) / n
        z = z0 + per_deg * (a0 + a1) / 2 - lug_w / 2
        seg = Part.makeCylinder(r_out, lug_w, V(0, 0, z), V(0, 0, 1), (a1 - a0) + 0.6)
        seg = seg.cut(Part.makeCylinder(r_in, lug_w + 1.0, V(0, 0, z - 0.5)))
        seg.rotate(V(0, 0, 0), V(0, 0, 1), a0)
        run = seg if run is None else run.fuse(seg)
    return run


def _bayo_cavity(sweep_extra=None, detent_at=None):
    """Bore, plus an L-slot per lug: straight in, then a circumferential run.  The run sweeps
    BAYO_TURN PLUS the lug's own angular half-width at the bore, so the lug's CENTRE reaches
    BAYO_TURN and the sector's end face is a hard stop there.  A shallow dome on the channel
    floor just before the stop is the detent."""
    r_in, r_out = BAYO_R + BAYO_CLEAR, BAYO_R + BAYO_LUG_OUT + 0.6
    lug_w = 2 * BAYO_LUG_R + 2 * BAYO_CHAN_CLEAR
    extra = BAYO_SWEEP_EXTRA if sweep_extra is None else sweep_extra
    sweep = BAYO_TURN + extra
    t = Part.makeCylinder(r_in, BAYO_LEN + 1.0, V(0, 0, -0.5))
    # Channel centre at theta = 0.  What sets the male's depth is the channel FLOOR under the lug,
    # so this has to account for the lug's clearance inside the channel (lug_w/2 - BAYO_LUG_R) --
    # leave it out and that slack silently eats the ramp's draw and nothing ever wedges.
    #   floor(theta) = z_mid0 + (BAYO_RAMP / BAYO_TURN) * theta - lug_w / 2
    #   male proud    = BAYO_LUG_Z - floor - BAYO_LUG_R
    # which gives BAYO_RAMP - BAYO_PRELOAD proud at 0 deg and BAYO_PRELOAD of interference at BAYO_TURN.
    z_mid0 = BAYO_LUG_Z - BAYO_LUG_R + lug_w / 2 - BAYO_RAMP + BAYO_PRELOAD
    z_run = z_mid0 - lug_w / 2                                    # bottom of the run at theta = 0
    for ang in (0, 180):
        # entry runs from the mouth (z=0) up to just past the lug's seated height, along +X so it
        # meets the start of the circumferential sector, which sweeps from azimuth 0
        entry = Part.makeBox(r_out, lug_w, z_run + lug_w + 1.0, V(0, -lug_w / 2, -0.5))
        entry.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        t = t.fuse(entry)
        run = _bayo_run(r_in, r_out, lug_w, z_mid0, sweep)
        run.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        t = t.fuse(run)
    # detent: a dome standing BAYO_DETENT off the channel floor, a few degrees before the stop.
    # Round 1 used a 0.45 mm post across a 0.25 mm gap, which simply jammed.
    # (kept out at the lug's outer end: a dome near the bore would also stand proud inside the
    #  bore itself and block the boss from entering at all)
    r_dome, r_dome_at = 1.2, BAYO_R + BAYO_LUG_OUT - 0.4
    for ang in (() if BAYO_DETENT <= 0 else (0, 180)):
        dome = Part.makeSphere(r_dome, V(r_dome_at, 0, z_run - r_dome + BAYO_DETENT))
        dome.rotate(V(0, 0, 0), V(0, 0, 1), ang + (BAYO_DETENT_AT if detent_at is None else detent_at))
        t = t.cut(dome)
    return _clean(t)


# ============================================================ dovetail
def _dove(grow=0.0, length=None, y0=None):
    """Dovetail tongue running along Y.  length/y0 default to the full plate (the male); the
    female passes a shorter groove open at the plate's front edge and closed at the back, so
    there is somewhere to slide it in from and something to stop against."""
    wb, wt, h = DOVE_WB + 2 * grow, DOVE_WT + 2 * grow, DOVE_H + grow
    ly = PLATE + 2.0 if length is None else length
    y = -PLATE / 2 - 1.0 if y0 is None else y0
    pts = [V(-wb / 2, y, 0), V(wb / 2, y, 0), V(wt / 2, y, h), V(-wt / 2, y, h)]
    face = Part.Face(Part.Wire(Part.makePolygon(pts + [pts[0]])))
    sh = face.extrude(V(0, ly, 0))
    return _clean(sh.fuse(Part.makeBox(wb, ly, 2.0, V(-wb / 2, y, -2.0))))


# ============================================================ builder
def build_jointtest(ctx):
    """One male + one female coupon per mechanism; the snap series is five collets against one
    socket, so only the barb interference changes between them."""
    out = []

    def add(label, shape, gx, gy):
        shape = shape.copy()
        shape.translate(V(gx * 30.0, gy * 30.0, 0))
        o = ctx.obj("Part::Feature", label.replace("-", "_"))
        o.Shape = shape
        o.Label = label
        out.append((label, o))

    # --- split collet snap: five pegs, one socket --------------------------------
    for i, inter in enumerate(SNAPB_INTERFERENCE):
        body = _plate().fuse(_snapb_peg(inter)).fuse(_dots(i + 1))
        add(f"Joint-SnapB-Peg{i+1}", _clean(body), i, 0)
    # One socket serves the whole series, so its groove is sized for the BIGGEST barb -- round 1
    # sized it for a zero-interference barb, so the larger pegs never reached the groove at all;
    # they wedged in the bore instead, which is what tore the fingers off.  The bore (the guiding
    # diameter, and the thing the barb must squeeze past) does not depend on the interference.
    # Print two or three: repeated test fits wear it.
    add("Joint-SnapB-Socket", _female(14.0, _snapb_cavity(max(SNAPB_INTERFERENCE))), 0, 1)

    # --- screw -------------------------------------------------------------------
    add("Joint-Screw-Male", _screw_male(SCREW_PLATE_H), 2, 1)
    add("Joint-Screw-Female", _screw_female(16.0), 3, 1)

    # --- bayonet -----------------------------------------------------------------
    add("Joint-Bayo-Male", _clean(_plate().fuse(_bayo_male())), 4, 1)
    add("Joint-Bayo-Female", _female(11.0, _bayo_cavity()), 0, 2)

    # --- dovetail ----------------------------------------------------------------
    add("Joint-Dove-Male", _clean(_plate().fuse(_dove())), 1, 2)
    add("Joint-Dove-Female", _female(8.0, _dove(DOVE_CLEAR, length=DOVE_LEN + 1.0,
                                                y0=-PLATE / 2 - 1.0)), 2, 2)

    return out
