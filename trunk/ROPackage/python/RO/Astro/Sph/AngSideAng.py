#!/usr/bin/env python
import RO.MathUtil
import RO.SysConst

def angSideAng (side_aa, ang_B, side_cc):
    """
    Solves a spherical triangle for two angles and the side connecting them,
    given the remaining quantities.
    
    Inputs:
    - side_aa   side  aa; range of sides:  [0, 180]
    - ang_B     angle b; range of angles: [0, 360)
    - side_cc   side  cc
    
    Returns a tuple containing:
    - ang_A     angle a
    - side_bb   side  bb
    - ang_C     angle c
    - unknownAng   if true, angle A and angle C could not be computed
                    (and are both set to 90); bb will be 0 or 180
    
    Error Conditions:
    - If the inputs are too small to allow computation, raises ValueError
    - If side bb is near 0 or 180 (see Special Cases below for when this occurs)
      then angles a and c cannot be computed. In this case "unknownAng" = true,
      ang_A = ang_C = 90.0. Also side_bb = 0.0, which is essentially correct.
      Note that the sum ang_A + ang_C is 180, which is also essentially correct.
    
    Special Cases (in the order they are handled):
    side_aa  ang_B   side_cc     ang_A       side_bb        ang_C
    ----------------------------------------------------------------
      ~0      any      ~0     unknown(90)       0        unknown(90)
      ~0      any     ~180    unknown(90)      180       unknown(90)
      ~0      any     !pole        0         side_cc      180-ang_B

     ~180     any     ~0      unknown(90)      180       unknown(90)
     ~180     any    ~180     unknown(90)       0        unknown(90)
     ~180     any    !pole        180      180-side_cc      ang_B

     !pole    any     ~0       180-ang_B     side_aa          0
     !pole    any    ~180        ang_B     180-side_aa       180

      any     ~0   ~=side_aa  unknown(90)       0        unknown(90)
      any     ~0    <side_aa      180       side_aa-cc        0
      any     ~0    >side_aa       0        side_cc-aa       180
    
    where:
    - !pole means not nearly 0 and not nearly 180 (modulo 360)
    - unknown(90) means unknownAng is set True and the angle is unknown and is
      abitrarily set to 90 degrees. The sum of ang_A and ang_C is correct
      and the value of side_bb is correct to within epsilon.
    - all relations are modulo 360. For example ~0 means approximately zero, 360, etc.
    
    Warnings:
    Allowing angles in the 3rd and 4th quadrants is unusual.
    
    References:
    Selby, Standard Math Tables, crc, 15th ed, 1967, p161 (Spherical Trig.)
    
    History:
    2002-07-22 ROwen    Converted from TCC's sph_AngSideAng 1-6.
    2010-07-30 ROwen    Changed output zero_bb to unknownAng; side_bb may be 180 instead of 0.
                        Bug fix: in some cases side_bb may be 180 and ang_A and ang_C unknown.
                        Improved accuracy in some corner cases; all unit tests now pass.
                        Greatly expanded the unit tests.
    2010-08-04 ROwen    Bug fix: mis-handled two cases:
                        - side_aa tiny + side_cc normal: special case table, code and unit test were incorrect
                        - side_aa normal + side_cc tiny: table was right but code and unit test had errors
    2011-01-28 ROwen    Bug fix: unknownAng should always be true if side_aa and side_cc are nearly 0 or 180
                        but that was not happening if ang_B was nearly 0. Fixed by evaluating ang_B
                        special cases after side_aa and side_cc special cases.
                        Tweaked the documentation to clarify the special cases.
    """
    sin_h_aa = RO.MathUtil.sind(side_aa)
    sin_h_cc = RO.MathUtil.sind(side_cc)
    sin_h_B = RO.MathUtil.sind(ang_B * 0.5)
    cos_h_B = RO.MathUtil.cosd(ang_B * 0.5)
    sin_h_aa = RO.MathUtil.sind(side_aa * 0.5)
    cos_h_aa = RO.MathUtil.cosd(side_aa * 0.5)
    sin_h_cc = RO.MathUtil.sind(side_cc * 0.5)
    cos_h_cc = RO.MathUtil.cosd(side_cc * 0.5)
    
    if abs(sin_h_aa) < RO.SysConst.FAccuracy:
        # side_aa is nearly zero (modulo 360)
        if abs(sin_h_cc) < RO.SysConst.FAccuracy:
            # side_cc is nearly 0 (modulo 360)
            return (90.0, 0.0, 90.0, True)
        elif abs(cos_h_cc) < RO.SysConst.FAccuracy:
            # side_cc is nearly 180 (modulo 360)
            return (90.0, 180.0, 90.0, True)
        else:
            # side_cc is not nearly 0 or 180
            ang_A = 0.0
            side_bb = side_cc
            ang_C = 180.0 - ang_B
    elif abs(cos_h_aa) < RO.SysConst.FAccuracy:
        # side_aa is nearly 180 (modulo 360)
        if abs(cos_h_cc) < RO.SysConst.FAccuracy:
            # side_cc is nearly 180 (modulo 360)
            return (90.0, 0.0, 90.0, True)
        elif abs(sin_h_cc) < RO.SysConst.FAccuracy:
            # side_cc is nearly 0 (modulo 360)
            return (90.0, 180.0, 90.0, True)
        else:
            # side_cc is not nearly 0 or 180 (modulo 360)
            ang_A = 180.0
            side_bb = 180.0 - side_cc
            ang_C = ang_B
    elif abs(sin_h_cc) < RO.SysConst.FAccuracy:
        # side_cc is nearly zero (modulo 360) and side_aa is not
        ang_A = 180.0 - ang_B
        side_bb = side_aa
        ang_C = 0.0
    elif abs(cos_h_cc) < RO.SysConst.FAccuracy:
        # side_cc is nearly 180 (modulo 360) and side_aa is not
        ang_A = ang_B
        side_bb = 180.0 - side_aa
        ang_C = 180.0
    elif abs(sin_h_B) < RO.SysConst.FAccuracy:
        # B is nearly 0 (modulo 360)
        if abs(side_aa - side_cc) < RO.SysConst.FAccuracy:
            # ang_B ~= 0 (modulo 360) and side_aa ~= side_cc (modulo 360); cannot compute ang_A or ang_C:
            return (90.0, 0.0, 90.0, True)
        elif side_cc < side_aa:
            ang_A = 180.0
            side_bb = side_aa - side_cc
            ang_C = 0.0
        else:
            ang_A = 0.0
            side_bb = side_cc - side_aa
            ang_C = 180.0
    else:
        # +
        #  compute angles a and c using Napier's analogies
        # -
        
        #  compute sin((aa +/- cc) / 2) and cos((aa +/- cc) / 2)
        sin_h_sum_aacc  = sin_h_aa * cos_h_cc + cos_h_aa * sin_h_cc
        sin_h_diff_aacc = sin_h_aa * cos_h_cc - cos_h_aa * sin_h_cc
        cos_h_sum_aacc  = cos_h_aa * cos_h_cc - sin_h_aa * sin_h_cc
        cos_h_diff_aacc = cos_h_aa * cos_h_cc + sin_h_aa * sin_h_cc
    
        #  compute numerator and denominator, where tan((a +/- c) / 2) = num/den
        num1 = cos_h_B * cos_h_diff_aacc
        den1 = sin_h_B * cos_h_sum_aacc
        num2 = cos_h_B * sin_h_diff_aacc
        den2 = sin_h_B * sin_h_sum_aacc
    
        #  if numerator and denominator are too small
        #  to accurately determine angle = atan2 (num, den), give up
        if (((abs (num1) <= RO.SysConst.FAccuracy) and (abs (den1) <= RO.SysConst.FAccuracy))
            or ((abs (num2) <= RO.SysConst.FAccuracy) and (abs (den2) <= RO.SysConst.FAccuracy))):
            raise RuntimeError("Bug: can't compute ang_A and C with side_aa=%s, ang_B=%s, side_cc=%s" % (side_aa, ang_B, side_cc))
    
        #  compute (a +/- c) / 2, and use to compute angles a and c
        h_sum_AC = RO.MathUtil.atan2d (num1, den1)
        h_diff_AC = RO.MathUtil.atan2d (num2, den2)
    
#         print "sin_h_B, cos_h_B =", sin_h_B, cos_h_B
#         print "sin_h_aa, cos_h_aa =", sin_h_aa, cos_h_aa
#         print "sin_h_cc, cos_h_cc =",sin_h_cc, cos_h_cc
#         print "sin_h_diff_aacc, sin_h_sum_aacc =", sin_h_diff_aacc, sin_h_sum_aacc
#         print "num1, den1, num2, den2 =", num1, den1, num2, den2
#         print "h_sum_AC, h_diff_AC =", h_sum_AC, h_diff_AC
    
        ang_A = h_sum_AC + h_diff_AC
        ang_C = h_sum_AC - h_diff_AC

        # +
        #  compute side bb using one of two Napier's analogies
        #  (one is for bb - aa, one for bb + aa)
        # -
        #  preliminaries
        sin_h_A = RO.MathUtil.sind(ang_A * 0.5)
        cos_h_A = RO.MathUtil.cosd(ang_A * 0.5)
        sin_h_sum_BA  = sin_h_B * cos_h_A + cos_h_B * sin_h_A
        sin_h_diff_BA = sin_h_B * cos_h_A - cos_h_B * sin_h_A
        cos_h_sum_BA  = cos_h_B * cos_h_A - sin_h_B * sin_h_A
        cos_h_diff_BA = cos_h_B * cos_h_A + sin_h_B * sin_h_A
    
        #  numerator and denominator for analogy for bb - aa
        num3 = sin_h_cc * sin_h_diff_BA
        den3 = cos_h_cc * sin_h_sum_BA
    
        #  numerator and denominator for analogy for bb + aa
        num4 = sin_h_cc * cos_h_diff_BA
        den4 = cos_h_cc * cos_h_sum_BA
    
        #  compute side bb
        if abs (num3) + abs (den3) > abs (num4) + abs (den4):
            #  use Napier's analogy for bb - aa
            side_bb = 2.0 * RO.MathUtil.atan2d (num3, den3) + side_aa
        else:
            side_bb = 2.0 * RO.MathUtil.atan2d (num4, den4) - side_aa
        side_bb = RO.MathUtil.wrapPos (side_bb)

    return (RO.MathUtil.wrapPos(ang_A), side_bb, RO.MathUtil.wrapPos(ang_C), False)


if __name__ == "__main__":
    import RO.SeqUtil
    print "testing angSideAng"
    
    Eps = 1.0e-15
    EpsTest = Eps * 1.001
    testData = []
    # test data is formatted as follows:
    # a list of entries, each consisting of:
    # - the input argument
    # - the expected result: ang_C, side_bb, ang_A, [unknownAng] (unknownAng defaults to False)


    # a ~ 0, B = various, c various:
    # if c nearly 0 (modulo 360): expect C = 90, b = 0, A = 90, unknownAng
    # if c nearly 180 (modulo 360): expect C = 90, b = 180, A = 90, unknownAng
    # else: expect A = 0, b = a - c, C = 180 - B
    for side_aa in (-Eps, 0.0, Eps):
        for ang_B in (0.0, Eps, 32.0, 97.0, 179.0, 180.0 - Eps, 180.0, 180.0 + Eps, 210.0, 360.0 - Eps, 360.0):
            for side_cc in (180.0, 180.0 - Eps, 179.0, 47.0, Eps, 0.0):
                if abs(side_cc % 360.0) < EpsTest:
                    expRes = (90.0, 0.0, 90.0, True)
                elif abs((side_cc - 180) % 360.0) < EpsTest:
                    expRes = (90.0, 180.0, 90.0, True)
                else:
                    expRes = (0.0, side_cc - side_aa, 180.0 - ang_B)
                testData.append(((side_aa, ang_B, side_cc), expRes))

    # a ~ 180, B = various, c various:
    # if c nearly 180 (modulo 360): expect C = 90, b = 0, A = 90, unknownAng
    # if c nearly 0 (modulo 360): expect C = 90, b = 180, A = 90, unknownAng
    # else: expect A = 180, b = 180 - c, C = B
    for side_aa in (180.0 - Eps, 180.0, 180.0 + Eps):
        for ang_B in (0.0, Eps, 32.0, 97.0, 179.0, 180.0 - Eps, 180.0, 180.0 + Eps, 210.0, 360.0 - Eps, 360.0):
            for side_cc in (180.0, 180.0 - Eps, 179.0, 47.0, Eps, 0.0):
                if abs((180.0 - side_cc) % 360.0) < EpsTest:
                    expRes = (90.0, 0.0, 90.0, True)
                elif abs(side_cc % 360.0) < EpsTest:
                    expRes = (90.0, 180.0, 90.0, True)
                else:
                    expRes = (180.0, 180.0 - side_cc, ang_B)
                testData.append(((side_aa, ang_B, side_cc), expRes))

    # c ~ 0, B = various, a various:
    # if a nearly 0: expect C = 90, b = 0, A = 90, unknownAng
    # if a nearly 180: expect C = 90, b = 180, A = 90, unknownAng
    # else: expect A = 180 - B, b = a, C = 0
    for side_cc in (0.0, Eps):
        for ang_B in (0.0, Eps, 32.0, 97.0, 179.0, 180.0 - Eps, 180.0, 180.0 + Eps, 210.0, 360.0 - Eps, 360.0):
            for side_aa in (180.0, 180.0 - Eps, 179.0, 47.0, Eps, 0.0):
                if abs(side_aa % 360.0) < EpsTest:
                    expRes = (90.0, 0.0, 90.0, True)
                elif abs((180.0 - side_aa) % 360.0) < EpsTest:
                    expRes = (90.0, 180.0, 90.0, True)
                else:
                    expRes = (180.0 - ang_B, side_aa, 0.0)
                testData.append(((side_aa, ang_B, side_cc), expRes))
    
    # c ~ 180, B = various, a various:
    # if a nearly 0 (modulo 360): expect C = 90, b = 180, A = 90, unknownAng
    # if a nearly 180 (modulo 360): expect C = 90, b = 0, A = 90, unknownAng
    # else: expect A = 180, b = 180 - c, C = B
    for side_cc in (180.0 - Eps, 180.0):
        for ang_B in (0.0, Eps, 32.0, 97.0, 179.0, 180.0 - Eps, 180.0, 180.0 + Eps, 210.0, 360.0 - Eps, 360.0):
            for side_aa in (180.0, 180.0 - Eps, 179.0, 47.0, Eps, 0.0):
                if side_aa < EpsTest:
                    expRes = (90.0, 180.0, 90.0, True)
                elif 180.0 - side_aa < EpsTest:
                    expRes = (90.0, 0.0, 90.0, True)
                else:
                    expRes = (ang_B, 180.0 - side_aa, 180.0)
                testData.append(((side_aa, ang_B, side_cc), expRes))

    # a = 90, B varies but not nearly 0 or 360, c fairly small but >> Eps
    # expect: A = 180 - B, b = a + c cos(B), C ~= 0
    side_aa = 90.0
    for side_cc in (1.0e-12, 1.0e-10):
        for ang_B in (23, 90, 180 - Eps, 180, 180 + Eps, 256, 359):
            expRes = (180.0 - ang_B, side_aa + (side_cc * RO.MathUtil.cosd(ang_B)), 0.0)
            testData.append(((side_aa, ang_B, side_cc), expRes))

    # a fairly small but >> Eps, B varies, c = 90
    # expect: C = 180 - B, b = c + a cos(B), A ~= 0
    side_cc = 90.0
    for side_aa in (1.0e-12, 1.0e-10):
        for ang_B in (23, 90, 180 - Eps, 180, 180 + Eps, 256, 359):
            expRes = (0.0, side_cc + (side_aa * RO.MathUtil.cosd(ang_B)), 180.0 - ang_B)
            testData.append(((side_aa, ang_B, side_cc), expRes))

    # B small, a = any not small, c = any not small:
    # if c != a: expect A = 90, b = 0, C = 90, unknown
    # if c << a: expect A = 180,   b = c - a, C = 0
    # if c >> a: expect A = 0, b = a - c, C = 180
    for side_aa in (179.9, -27.0, 27.0, 0.1):
        for side_cc in (side_aa - 45.0, side_aa - Eps, side_aa, side_aa + Eps, side_aa + 45.0):
            if abs(side_cc - side_aa) < EpsTest:
                expRes = (90.0, 0.0, 90.0, True)
            elif side_cc < side_aa:
                expRes = (180.0, side_aa - side_cc, 0.0)
            else:
                expRes = (0.0, side_cc - side_aa, 180.0)
            for ang_B in (-Eps, 0.0, Eps):
                testData.append(((side_aa, ang_B, side_cc), expRes))
    
    # right triangle: B = 90, a and c vary but avoid poles
    # tan C = tan c / sin a
    # tan c = (tan a / sinA * sinb)
    # with some tweaks to handle the other quadrants
    ang_B = 90.0
    for side_aa in (1.0, 20.0, 45.0, 90, 110.0, 179.0):
        for side_cc in (1.0, 20.0, 45.0, 90.0, 110.0, 179.0):
            ang_A = RO.MathUtil.atan2d(RO.MathUtil.tand(side_aa), RO.MathUtil.sind(side_cc))
            ang_C = RO.MathUtil.atan2d(RO.MathUtil.tand(side_cc), RO.MathUtil.sind(side_aa))
            side_bb = RO.MathUtil.atan2d(RO.MathUtil.tand(side_aa), RO.MathUtil.sind(ang_A) * RO.MathUtil.cosd(side_cc))
            # these tweaks handle other quadrants; they're based on what works, so are somewhat suspect
            if side_bb < 0:
                side_bb = - side_bb
            if ang_A < 0:
                ang_A = 180.0 + ang_A
            if ang_C < 0:
                ang_C = 180.0 + ang_C
            testData.append(((side_aa, ang_B, side_cc), (ang_A, side_bb, ang_C)))

    testData += [
        # 90/90/90 triangle
        ((90, 90, 90), (90, 90, 90)),
        
        # inputs that might cause side_bb < 0, (but should not)
        ((45, 1, 45), (89.6464421219342, 0.707102293688337, 89.6464421219342)),
        ((45, -1, 45), (270.353557878066, 0.707102293688337, 270.353557878066)),
        ((135, 1, 135), (90.3535578780658, 0.707102293688337, 90.3535578780658)),
        ((135, -1, 135), (269.646442121934, 0.707102293688308, 269.646442121934)),
    ]
    
    def processOutput(outputVec):
        return (
            RO.MathUtil.sind(outputVec[0]), RO.MathUtil.cosd(outputVec[0]),
            outputVec[1],
            RO.MathUtil.sind(outputVec[2]), RO.MathUtil.cosd(outputVec[2]),
            outputVec[3],
        )
    
    for testInput, expectedOutput in testData:
        if len(expectedOutput) < 4:
            expectedOutput = expectedOutput + (False,)
        actualOutput = angSideAng(*testInput)

        # to handle angles comparing things like 359.999... to 0, compare sin and cos of ang_A and ang_C:
        procExpected = processOutput(expectedOutput)
        procActual = processOutput(actualOutput)
        if RO.SeqUtil.matchSequences(procExpected, procActual, rtol=1.0e-10, atol=1.0e-10):
            print "failed on input:", testInput
            print "expected output:", expectedOutput
            print "actual output:", actualOutput
            print
        if actualOutput[0] < 0.0 or actualOutput[0] >= 360.0 \
            or actualOutput[1] < 0.0 or actualOutput[1] >= 360.0 \
            or actualOutput[2] < 0.0 or actualOutput[2] >= 360.0:
            print "failed on input:", testInput
            print "one or more angles out of range:", actualOutput
            print
