"""Numeric geometry shared by the yoke builders, the ball builders and the assembly.

A yoke has collars on the spine; from each attachment a bar runs straight toward the centre of
the joint ball.  Shoulders: C7 pad -> trap; the clavicles start at a centre joint on the control
box's top-front edge and the balls sit ShoulderForward ahead of the spine.  Pelvis: L5 and S1
pads; the S5 bars start at a centre joint PelvisForward ahead of the spine, run straight and
level to the hip balls, which sit at that same forward distance.  The connector disc that
carries the ball faces along the bisector of the top and bottom bar directions; its outer face is
the ball's proximal mating face.
"""
import math
import FreeCAD as App

V = App.Vector

YOKES = {
    # kind: (width param, ball param, [(collar tag, z function, start kind)] top to bottom)
    # z is relative to the part origin; the ball sits at the lowest collar's height + BALL_RISE
    "shoulder": ("ShoulderWidth", "ShoulderBall", [
        ("C7", lambda s: s("HubHeight") - s("SpineDiameter") * 0.35, "pad"),
        ("T1", lambda s: s("HubHeight") - s("ShoulderDrop"), "junction"),
    ]),
    "pelvis": ("PelvisWidth", "HipBall", [
        ("L5", lambda s: -s("SpineDiameter") * 0.35, "pad"),
        ("S1", lambda s: (-s("SpineDiameter") * 0.35 - s("PelvisDrop")) / 2, "pad"),
        ("S5", lambda s: -s("PelvisDrop"), "junction"),
    ]),
}
BALL_RISE = {"shoulder": lambda s: s("YokeBar") * 2, "pelvis": lambda s: 0.0}   # ball centre above the lowest collar
FORWARD = {"shoulder": "ShoulderForward", "pelvis": "PelvisForward"}            # ball centre ahead of the spine
CONNECTOR = {"shoulder": "ClavicleBar", "pelvis": "PelvisBar"}                  # thick connector length at the centre joint

def pad_x(v):
    """Outer face of the collar pads (numeric, scaled)."""
    s = lambda n: v[n] * v["Scale"]
    return s("VertebraDiameter") / 2 + s("YokeBar") * 0.3

def junction(v, kind, z):
    """Centre joint the lowest bars start from.  Shoulders: over the control box's top-front edge,
    half a bar up.  Pelvis: PelvisForward ahead of the spine at the S5 height."""
    s = lambda n: v[n] * v["Scale"]
    if kind == "shoulder":
        return V(0, s("SpineDiameter") / 2 + s("SystemBoxDepth"), z + s("YokeBar") / 2)
    return V(0, s("PelvisForward"), z)

def yoke_side(v, kind, sx):
    """Numeric frame for one side of a yoke.  Returns a dict with:
    B (ball centre), n (disc normal, unit), F (mating face centre), c (face-to-centre offset),
    CL (disc thickness), bars: list of (tag, start point, unit direction start->ball, collar z, kind),
    rot (App.Rotation taking local +Z to n)."""
    s = lambda n: v[n] * v["Scale"]
    width, ball, collars = YOKES[kind]
    xp = pad_x(v) * 0.98 * sx
    zl = collars[-1][1](s)
    B = V(sx * s(width) / 2, s(FORWARD[kind]), zl + BALL_RISE[kind](s))
    bars = []
    for tag, zf, start in collars:
        z = zf(s)
        P = V(xp, 0, z) if start == "pad" else junction(v, kind, z)
        u = B - P; u.normalize()
        bars.append((tag, P, u, z, start))
    n = bars[0][2] + bars[-1][2]; n.normalize()
    c = s(ball) / 2 * v["JointCupOffset"]
    CL = s(ball) * 0.25
    F = B - n * c
    rot = App.Rotation(V(0, 0, 1), n)
    return dict(B=B, n=n, F=F, c=c, CL=CL, bars=bars, rot=rot)

def ball_bend(v, kind, sx):
    """Rotation of a hip/shoulder ball's distal face so the limb hangs as designed
    despite the tilted mating face: expressed in the ball's own frame."""
    g = yoke_side(v, kind, sx)
    if kind == "shoulder":
        a = math.radians(v["ArmSplay"])
        d_world = V(sx * math.sin(a), 0, -math.cos(a))
    else:
        d_world = V(0, 0, -1)
    inv = g["rot"].inverted()
    z = inv.multVec(d_world)
    # full frame, not a shortest-arc Z->d: keep the limb's local Y on world +Y so the chain has no
    # twist about its own axis (feet point forward, elbows bend forward)
    y = inv.multVec(V(0, 1, 0)); y = y - z * y.dot(z); y.normalize()
    x = y.cross(z)
    return App.Rotation(App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1))
