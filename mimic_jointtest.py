"""Joint test coupons: one small pair per locking mechanism, printed and clicked by hand.

Everything here is ABSOLUTE millimetres (like the peg itself) -- these are test pieces, not
scaled parts.  Each male coupon is a plate lying z = -PLATE..0 with its feature standing up in
+Z; each female coupon is a plate with the mating cavity opening upward at z = 0.  So both print
plate-down with no supports, and the cavity is the male feature (grown by a clearance) rotated
180 deg about X -- the pose it will actually be in when mated, so handed features (threads,
bayonet lugs) match.

Raised dots on the plate identify a variant (one dot = first in the series).

The series:
  Joint-SnapA-*   the current barbed peg, as a baseline (built by build_snaptest)
  Joint-SnapB-*   split cantilever peg, 5 interferences -- the tuning matrix
  Joint-Screw-*   coarse trapezoidal thread
  Joint-Bayo-*    quarter-turn bayonet with a detent bump
  Joint-Dove-*    dovetail slide
  Joint-Magnet-*  magnet pocket + two alignment pins
"""
import math
import FreeCAD as App
import Part

V = App.Vector

PLATE = 20.0            # coupon plate, mm square
PLATE_H = 5.0           # male plate thickness
DOT_R, DOT_H = 0.7, 0.6

# ---- split cantilever peg (the tuning matrix) ---------------------------------
SNAPB_SHAFT_R = 2.0     # shaft radius: 4 mm shaft, ~10 extrusion widths at 0.4 mm nozzle
SNAPB_LEN = 8.0         # protruding length
SNAPB_BORE_CLEAR = 0.15 # socket bore over shaft radius: this guides the peg
SNAPB_SLIT = 0.8        # cross-slit width (two perimeters)
SNAPB_SLIT_FLOOR = 1.0  # slits stop this far above the mating plane
SNAPB_FACE = 5.5        # flat retaining face height above the mating plane
SNAPB_TIP_R = 1.6       # radius where the lead-in cone meets the tip
SNAPB_GROOVE = 0.25     # socket groove over the barb: room to snap out
# radial interference at the barb = how far each finger must flex on the way in
SNAPB_INTERFERENCE = (0.15, 0.20, 0.25, 0.30, 0.35)

# ---- coarse trapezoidal screw --------------------------------------------------
SCREW_CORE_R, SCREW_MAJ_R = 3.5, 4.5
SCREW_PITCH, SCREW_LEN = 2.0, 8.0
SCREW_CLEAR = 0.25

# ---- bayonet -------------------------------------------------------------------
BAYO_R, BAYO_LEN = 4.0, 8.0
BAYO_LUG_R, BAYO_LUG_OUT = 1.4, 1.6      # lug radius and how far it stands out
BAYO_LUG_Z = 6.2                          # lug centre height
BAYO_TURN = 90.0                          # degrees of twist to lock
BAYO_CLEAR = 0.25

# ---- dovetail ------------------------------------------------------------------
DOVE_WB, DOVE_WT, DOVE_H, DOVE_LEN = 6.0, 9.0, 4.0, 16.0
DOVE_CLEAR = 0.2

# ---- magnet + alignment pins ---------------------------------------------------
MAG_R, MAG_DEPTH = 3.1, 3.2               # 6 x 3 mm disc magnet pocket
MAG_PIN_R, MAG_PIN_H, MAG_PIN_X = 2.0, 4.0, 6.0
MAG_PIN_CLEAR = 0.2


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


def _female(plate_h, cavity, dots=0):
    """A female coupon: the cavity is the male feature rotated into its mated pose and cut out."""
    c = cavity.copy()
    c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    body = _plate(plate_h).cut(c)
    if dots:
        body = body.fuse(_dots(dots))
    return _clean(body)


# ============================================================ split cantilever peg
def _snapb_peg(interference, slit=SNAPB_SLIT):
    """Peg: shaft, then a barb whose underside is a flat retaining face and whose top is a shallow
    lead-in cone.  A cross-slit turns it into four cantilever fingers, so the interference is taken
    up by bending (elastic) instead of by hooping a solid wall (which cracks)."""
    r_barb = SNAPB_SHAFT_R + SNAPB_BORE_CLEAR + interference
    sh = Part.makeCylinder(SNAPB_SHAFT_R, SNAPB_FACE + 2.0, V(0, 0, -2.0))      # 2 mm buried in the plate
    sh = sh.fuse(Part.makeCone(r_barb, SNAPB_TIP_R, SNAPB_LEN - SNAPB_FACE, V(0, 0, SNAPB_FACE)))
    for ang in (0, 90):
        s = Part.makeBox(slit, 4 * SNAPB_SHAFT_R, SNAPB_LEN - SNAPB_SLIT_FLOOR + 0.5,
                         V(-slit / 2, -2 * SNAPB_SHAFT_R, SNAPB_SLIT_FLOOR))
        s.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        sh = sh.cut(s)
    return _clean(sh)


def _snapb_cavity(interference):
    """Socket: a bore that guides the shaft, then a groove the barb springs out into.  The step
    between them is the ledge the peg's flat face catches under."""
    r_barb = SNAPB_SHAFT_R + SNAPB_BORE_CLEAR + interference
    r_bore = SNAPB_SHAFT_R + SNAPB_BORE_CLEAR
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
    core = Part.makeCylinder(core_r, length + 2.0, V(0, 0, -2.0))
    return core, ridge


def _screw_male(plate_h, core_r, maj_r, pitch, length):
    """Plate plus the screw, fused a step at a time: fusing a pre-fused core+ridge to the plate
    returns an empty solid (same OCC quirk as the female's cut tool)."""
    body = _plate(plate_h)
    core, ridge = _screw_parts(core_r, maj_r, pitch, length)
    body = body.fuse(core).fuse(ridge)
    # cut the top off square: a cone chamfer crossing the thread crest leaves self-intersecting
    # facets, and with 0.25 mm radial clearance the blunt start still engages by feel
    body = body.cut(Part.makeBox(4 * PLATE, 4 * PLATE, 4 * PLATE,
                                 V(-2 * PLATE, -2 * PLATE, length - 1.2)))
    return _clean(body)


def _screw_female(plate_h, core_r, maj_r, pitch, length):
    """Threaded hole: bore first, then the ridge, both cut separately (see _screw_parts)."""
    core, ridge = _screw_parts(core_r, maj_r, pitch, length)
    body = _plate(plate_h)
    for t in (core, ridge):
        c = t.copy()
        c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
        body = body.cut(c)
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


def _bayo_cavity():
    """Bore, plus an L-slot per lug: straight in, quarter turn across, with a bump at the end of
    the run that the lug has to ride over -- that bump is what stops it shaking loose."""
    r_in, r_out = BAYO_R + BAYO_CLEAR, BAYO_R + BAYO_LUG_OUT + 0.6
    lug_w = 2 * BAYO_LUG_R + 2 * BAYO_CLEAR
    t = Part.makeCylinder(r_in, BAYO_LEN + 1.0, V(0, 0, -0.5))
    z_run = BAYO_LUG_Z - BAYO_LUG_R - BAYO_CLEAR                  # bottom of the circumferential run
    for ang in (0, 180):
        # entry runs from the mouth (z=0) up to just past the lug's seated height, along +X so it
        # meets the start of the circumferential sector, which sweeps from azimuth 0
        entry = Part.makeBox(r_out, lug_w, z_run + lug_w + 1.0, V(0, -lug_w / 2, -0.5))
        entry.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        t = t.fuse(entry)
        run = Part.makeCylinder(r_out, lug_w, V(0, 0, z_run), V(0, 0, 1), BAYO_TURN + 12)
        run = run.cut(Part.makeCylinder(r_in, lug_w + 1.0, V(0, 0, z_run - 0.5)))
        run.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        t = t.fuse(run)
    # detent bumps: put material back at the end of each run so the lug clicks past them
    for ang in (0, 180):
        a = math.radians(ang + BAYO_TURN)
        bump = Part.makeCylinder(0.45, r_out - r_in + 0.4, V(r_in + 0.2, 0, z_run + lug_w / 2), V(1, 0, 0))
        bump.rotate(V(0, 0, 0), V(0, 0, 1), ang + BAYO_TURN - 6)
        t = t.cut(bump)
    return _clean(t)


# ============================================================ dovetail
def _dove(grow=0.0):
    wb, wt, h, ly = DOVE_WB + 2 * grow, DOVE_WT + 2 * grow, DOVE_H + grow, DOVE_LEN
    pts = [V(-wb / 2, -ly / 2, 0), V(wb / 2, -ly / 2, 0), V(wt / 2, -ly / 2, h), V(-wt / 2, -ly / 2, h)]
    face = Part.Face(Part.Wire(Part.makePolygon(pts + [pts[0]])))
    sh = face.extrude(V(0, ly, 0))
    return _clean(sh.fuse(Part.makeBox(wb, ly, 2.0, V(-wb / 2, -ly / 2, -2.0))))


# ============================================================ magnet + pins
def _magnet(grow=0.0):
    sh = None
    for sx in (-1, 1):
        pin = Part.makeCylinder(MAG_PIN_R + grow, MAG_PIN_H + grow, V(sx * MAG_PIN_X, 0, 0))
        sh = pin if sh is None else sh.fuse(pin)
    return _clean(sh)


# ============================================================ builder
def build_jointtest(ctx):
    """One male + one female coupon per mechanism; the snap series is five males against one socket
    so the shaft clearance stays constant and only the barb interference changes."""
    out = []
    col = {}

    def add(label, shape, gx, gy):
        shape = shape.copy()
        shape.translate(V(gx * 30.0, gy * 30.0, 0))
        o = ctx.obj("Part::Feature", label.replace("-", "_"))
        o.Shape = shape
        o.Label = label
        out.append((label, o))

    # --- split cantilever snap: five pegs, one socket ---------------------------
    for i, inter in enumerate(SNAPB_INTERFERENCE):
        body = _plate().fuse(_snapb_peg(inter)).fuse(_dots(i + 1))
        add(f"Joint-SnapB-Peg{i+1}", _clean(body), i, 0)
    # the socket only has to be printed once (print two or three: repeated test fits wear it)
    add("Joint-SnapB-Socket", _female(11.0, _snapb_cavity(0.0)), 0, 1)

    # --- screw -------------------------------------------------------------------
    add("Joint-Screw-Male", _screw_male(PLATE_H, SCREW_CORE_R, SCREW_MAJ_R, SCREW_PITCH, SCREW_LEN), 2, 1)
    add("Joint-Screw-Female", _screw_female(11.0, SCREW_CORE_R + SCREW_CLEAR, SCREW_MAJ_R + SCREW_CLEAR,
                                            SCREW_PITCH, SCREW_LEN + 0.5), 3, 1)

    # --- bayonet -----------------------------------------------------------------
    add("Joint-Bayo-Male", _clean(_plate().fuse(_bayo_male())), 4, 1)
    add("Joint-Bayo-Female", _female(11.0, _bayo_cavity()), 0, 2)

    # --- dovetail ----------------------------------------------------------------
    add("Joint-Dove-Male", _clean(_plate().fuse(_dove())), 1, 2)
    add("Joint-Dove-Female", _female(8.0, _dove(DOVE_CLEAR)), 2, 2)

    # --- magnet + alignment pins --------------------------------------------------
    pocket = Part.makeCylinder(MAG_R, MAG_DEPTH, V(0, 0, -MAG_DEPTH))
    add("Joint-Magnet-Male", _clean(_plate(8.0).fuse(_magnet()).cut(pocket)), 3, 2)
    add("Joint-Magnet-Female", _clean(_female(8.0, _magnet(MAG_PIN_CLEAR)).cut(pocket)), 4, 2)

    return out
