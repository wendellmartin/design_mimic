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

    # ---- Head (open cage, sphere of HeadCageRadius) ------------------------
    ("HeadCageRadius",  "L", 100, "Head", "Cage sphere radius."),
    ("CageBar",         "L", 10,  "Head", "Small head bar diameter (top bars, eye bars)."),
    ("HeadBar",         "L", 28,  "Head", "Main head bar: the spine continuing around the head."),
    ("EyeDiameter",     "L", 70,  "Head", "Eye sphere."),
    ("EyeSpacing",      "L", 108, "Head", "Centre to centre."),
    ("MouthDiameter",   "L", 60,  "Head", "Speaker barrel."),
    ("MouthLength",     "L", 60,  "Head", ""),
    ("JawBar",          "L", 18,  "Head", "Jaw bar diameter."),
    ("NeckLength",      "L", 60,  "Head", "Shoulder hub top to head neck face."),
    ("NeckDiameter",    "L", 55,  "Head", ""),
    ("NeckPost",        "L", 40,  "Head", "Post between the head neck face and the cage bottom."),

    # ---- Torso -------------------------------------------------------------
    ("SpineDiameter",   "L", 60,  "Torso", "Spine column."),
    ("SpineLength",     "L", 490, "Torso", "Pelvis hub top to shoulder hub bottom."),
    ("VertebraCount",   "I", 4,   "Torso", "Thick collars on the spine."),
    ("VertebraDiameter","L", 90,  "Torso", ""),
    ("HubHeight",       "L", 150, "Torso", "Length of the spine section that carries the shoulder collars."),
    ("YokeBar",         "L", 30,  "Torso", "Yoke bar diameter."),
    ("ShoulderWidth",   "L", 480, "Torso", "Shoulder ball centre to centre."),
    ("ShoulderDrop",    "L", 130, "Torso", "Shoulder balls sit this far below the shoulder hub top."),
    ("PelvisWidth",     "L", 320, "Torso", "Hip ball centre to centre."),
    ("PelvisDrop",      "L", 140, "Torso", "Hip balls sit this far below the pelvis hub top."),
    ("SystemBoxWidth",  "L", 150, "Torso", "The box where the heart would be."),
    ("SystemBoxHeight", "L", 140, "Torso", ""),
    ("SystemBoxDepth",  "L", 90,  "Torso", ""),
    ("SystemBoxDrop",   "L", 0,   "Torso", "Box top sits this far below T1."),
    ("ShoulderForward", "L", 60,  "Torso", "Shoulder ball centres sit this far ahead of the spine axis (midway to the clavicle bar, so traps angle forward and clavicles back equally).", "(SpineDiameter / 2 + SystemBoxDepth) / 2"),
    ("ClavicleBar",     "L", 180, "Torso", "Thick connector at the clavicle centre joint (total, twice a vertebra)."),
    ("PelvisForward",   "L", 60,  "Torso", "Hip balls and the S5 centre joint sit this far ahead of the spine (half the clavicle joint).", "(SpineDiameter / 2 + SystemBoxDepth) / 2"),
    ("PelvisBar",       "L", 110, "Torso", "Thick connector at the S5 centre joint (total)."),

    # ---- Limbs -------------------------------------------------------------
    ("ThighLength",     "L", 480, "Limbs", "Hip centre to knee centre."),
    ("ThighDiameter",   "L", 70,  "Limbs", "Main strut."),
    ("ShinLength",      "L", 460, "Limbs", "Knee centre to ankle centre."),
    ("ShinDiameter",    "L", 60,  "Limbs", ""),
    ("FootLength",      "L", 260, "Limbs", ""),
    ("FootWidth",       "L", 150, "Limbs", "Across the three claws."),
    ("ToeWidth",        "L", 40,  "Limbs", "One claw, side to side."),
    ("FootHeight",      "L", 110, "Limbs", "Ankle centre to sole."),
    ("UpperArmLength",  "L", 420, "Limbs", "Shoulder centre to elbow centre."),
    ("UpperArmDiameter","L", 60,  "Limbs", ""),
    ("ForearmLength",   "L", 400, "Limbs", "Elbow centre to wrist centre."),
    ("ForearmDiameter", "L", 50,  "Limbs", ""),
    ("HandLength",      "L", 245, "Limbs", "Wrist to fingertip."),
    ("PalmWidth",       "L", 70,  "Limbs", "Across the three digits."),
    ("FingerWidth",     "L", 15,  "Limbs", "Digit segment cross-section."),

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

    # ---- Version -----------------------------------------------------------
    ("VersionMajor",    "I", 1, "Version", ""),
    ("VersionMinor",    "I", 0, "Version", ""),
    ("VersionBuild",    "I", 0, "Version", ""),
    ("VersionEmbossDepth","L",0.5,"Version", ""),
    ("VersionNumber",   "S", "1.0.0", "Version", "", "str(VersionMajor) + <<.>> + str(VersionMinor) + <<.>> + str(VersionBuild)"),
    ("VersionString",   "S", "v1.0.0","Version", "", "<<v>> + VersionNumber"),
]

TYPES = {"L": "App::PropertyLength", "F": "App::PropertyFloat", "A": "App::PropertyAngle",
         "I": "App::PropertyInteger", "S": "App::PropertyString"}

def value_of(name):
    """Plain numeric value from the table (no expression evaluation)."""
    for p in PARAMS:
        if p[0] == name:
            return p[2]
    raise KeyError(name)
