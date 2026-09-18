"""Parameter table for the Mimic.

Every entry becomes a property on the `Dimensions` VarSet in Mimic-Resources.FCStd.
Body dimensions are LIFE-SIZE millimetres; parts multiply them by `Scale`.
Peg/Socket dimensions are ABSOLUTE and never scaled (the 3 mm barb is proven in PLA).

(name, type, value, group, doc)   type: L=Length  F=Float  A=Angle  I=Integer  S=String
An `expr` 5th element makes the property expression-driven inside the VarSet.
"""

PARAMS = [
    # ---- Global -----------------------------------------------------------
    ("Scale",           "F", 0.25,  "Global", "Print scale. 1.0 = life size (TargetHeight). 0.25 = proof of concept."),
    ("TargetHeight",    "L", 2134,  "Global", "Life-size standing height, top of skull to sole (7 ft)."),
    ("BuildVolume",     "L", 270,   "Global", "Snapmaker U1 build cube edge. Pieces longer than this get split."),
    ("PegMinFace",      "L", 9,     "Global", "Smallest mating face diameter that still gets pegs; below this the joint is fused."),

    # ---- Peg (copied from Shelf with Rail v0.2.0, absolute mm) -----------
    ("PegBaseDiameter", "L", 3.0,   "Peg", "Shaft diameter."),
    ("PegFlareDiameter","L", 3.4,   "Peg", "Diameter where the tip cone meets the barb round-over."),
    ("PegDepth",        "L", 3.0,   "Peg", "Nominal hole depth (drives PegFlareDepth)."),
    ("PegTolerance",    "L", 0.2,   "Peg", "Radial clearance added to the socket."),
    ("PegTipAngle",     "A", 35,    "Peg", "Tip cone flank angle from the mating plane."),
    ("PegEmbed",        "L", 2.0,   "Peg", "How far the shaft is buried inside its host part for a clean fuse."),
    ("PegFlareDepth",   "L", 2.3,   "Peg", "Shoulder plane height above the mating face.", "PegDepth - 0.5 mm - PegTolerance"),
    ("PegRadius",       "L", 1.5,   "Peg", "", "PegBaseDiameter / 2"),
    ("PegFlareRadius",  "L", 1.7,   "Peg", "", "PegFlareDiameter / 2"),
    ("PegBarbRadius",   "L", 1.849, "Peg", "Max barb radius (shaft radius + round-over).", "PegRadius + (PegFlareRadius - PegRadius) / sin(PegTipAngle)"),
    ("PegBarbTop",      "L", 2.586, "Peg", "Top of round-over / bottom of tip cone.", "PegFlareDepth + (PegFlareRadius - PegRadius) / tan(PegTipAngle)"),
    ("PegTip",          "L", 3.776, "Peg", "Tip height above the mating face.", "PegBarbTop + PegFlareRadius * tan(PegTipAngle)"),

    # ---- Socket (negative of the peg + tolerance) ------------------------
    ("SocketBoreRadius","L", 1.849, "Socket", "", "PegBarbRadius"),
    ("SocketLipTop",    "L", 1.7,   "Socket", "Where the lip taper starts.", "PegFlareDepth - 3 * PegTolerance"),
    ("SocketLipBottom", "L", 2.1,   "Socket", "Lip lands here; barb shoulder sits just below.", "PegFlareDepth - PegTolerance"),
    ("SocketLipRadius", "L", 1.749, "Socket", "Lip is 0.1 mm smaller than the barb: that is the snap.", "PegBarbRadius - PegTolerance / 2"),
    ("SocketCavityRadius","L",2.049,"Socket", "", "PegBarbRadius + PegTolerance"),
    ("SocketTip",       "L", 3.976, "Socket", "", "PegTip + PegTolerance"),
    ("SocketCavityTop", "L", 2.541, "Socket", "", "SocketTip - SocketCavityRadius * tan(PegTipAngle)"),
    ("SocketExtend",    "L", 5.0,   "Socket", "Bore extends this far out of the mating face so the cut is clean."),

    # ---- Head --------------------------------------------------------------
    ("HeadHeight",      "L", 250, "Head", "Skull height, cranium top to chin (jaw closed)."),
    ("HeadWidth",       "L", 190, "Head", ""),
    ("HeadDepth",       "L", 230, "Head", ""),
    ("EyeDiameter",     "L", 70,  "Head", "Eye socket bore."),
    ("EyeSpacing",      "L", 80,  "Head", "Centre to centre."),
    ("JawHeight",       "L", 60,  "Head", ""),
    ("NeckLength",      "L", 90,  "Head", "Visible neck strut."),
    ("NeckDiameter",    "L", 55,  "Head", ""),

    # ---- Torso -------------------------------------------------------------
    ("ChestHeight",     "L", 380, "Torso", "Rib cage top to bottom."),
    ("ChestWidth",      "L", 400, "Torso", "Widest rib, outside."),
    ("ChestDepth",      "L", 240, "Torso", ""),
    ("RibCount",        "I", 6,   "Torso", "Rib pairs."),
    ("RibDiameter",     "L", 22,  "Torso", "Rib bar thickness."),
    ("SpineDiameter",   "L", 60,  "Torso", "Spine column."),
    ("SpineGap",        "L", 120, "Torso", "Exposed spine between rib cage and pelvis."),
    ("PelvisHeight",    "L", 150, "Torso", ""),
    ("PelvisWidth",     "L", 320, "Torso", "Hip joint centre to centre + ball."),
    ("PelvisDepth",     "L", 160, "Torso", ""),
    ("ShoulderWidth",   "L", 480, "Torso", "Shoulder ball centre to centre."),

    # ---- Limbs -------------------------------------------------------------
    ("ThighLength",     "L", 545, "Limbs", "Hip centre to knee centre."),
    ("ThighDiameter",   "L", 70,  "Limbs", "Main strut."),
    ("ShinLength",      "L", 520, "Limbs", "Knee centre to ankle centre."),
    ("ShinDiameter",    "L", 60,  "Limbs", ""),
    ("FootLength",      "L", 260, "Limbs", ""),
    ("FootWidth",       "L", 110, "Limbs", ""),
    ("FootHeight",      "L", 110, "Limbs", "Ankle centre to sole."),
    ("UpperArmLength",  "L", 420, "Limbs", "Shoulder centre to elbow centre."),
    ("UpperArmDiameter","L", 60,  "Limbs", ""),
    ("ForearmLength",   "L", 400, "Limbs", "Elbow centre to wrist centre."),
    ("ForearmDiameter", "L", 50,  "Limbs", ""),
    ("HandLength",      "L", 245, "Limbs", "Wrist to fingertip."),
    ("PalmWidth",       "L", 100, "Limbs", ""),
    ("FingerDiameter",  "L", 18,  "Limbs", ""),

    # ---- Joints (ball diameters) ------------------------------------------
    ("HipBall",         "L", 110, "Joints", ""),
    ("KneeBall",        "L", 90,  "Joints", ""),
    ("AnkleBall",       "L", 70,  "Joints", ""),
    ("ShoulderBall",    "L", 110, "Joints", ""),
    ("ElbowBall",       "L", 80,  "Joints", ""),
    ("WristBall",       "L", 60,  "Joints", ""),
    ("JointCupRatio",   "F", 0.8, "Joints", "Limb end flares to this fraction of its ball diameter (mating face)."),

    # ---- Pose (degrees) ----------------------------------------------------
    ("KneeBend",        "A", 0,  "Pose", "Knee flex."),
    ("ElbowBend",       "A", 20,  "Pose", "Elbow flex."),
    ("ArmSplay",        "A", 8,   "Pose", "Upper arm out from the body."),
    ("HeadTilt",        "A", 10,  "Pose", "Head forward tilt (the Mimic's stoop)."),

    # ---- Version -----------------------------------------------------------
    ("VersionMajor",    "I", 0, "Version", ""),
    ("VersionMinor",    "I", 1, "Version", ""),
    ("VersionBuild",    "I", 0, "Version", ""),
    ("VersionEmbossDepth","L",0.5,"Version", ""),
    ("VersionNumber",   "S", "0.1.0", "Version", "", "str(VersionMajor) + <<.>> + str(VersionMinor) + <<.>> + str(VersionBuild)"),
    ("VersionString",   "S", "v0.1.0","Version", "", "<<v>> + VersionNumber"),
]

TYPES = {"L": "App::PropertyLength", "F": "App::PropertyFloat", "A": "App::PropertyAngle",
         "I": "App::PropertyInteger", "S": "App::PropertyString"}

def value_of(name):
    """Plain numeric value from the table (no expression evaluation)."""
    for p in PARAMS:
        if p[0] == name:
            return p[2]
    raise KeyError(name)
