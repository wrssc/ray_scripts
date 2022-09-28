# Tests for the Beamsets
import numpy as np
import logging
from dateutil import parser
from collections import namedtuple
from math import isclose
import connect
from ReviewDefinitions import *
import ExamTests


def approval_info(plan, beamset):
    """
    Determine if beamset is approved and then if plan is approved. Return data
    Args:
        plan: RS plan object
        beamset: RS beamset object

    Returns:
        approval: NamedTuple.(beamset_approved, beamset_approved, beamset_exported,
                              beamset_reviewer, beamset_approval_time, plan_approved,
                              plan_exported, plan_reviewer, plan_approval_time)
    """
    Approval = namedtuple('Approval',
                          ['beamset_approved',
                           'beamset_exported',
                           'beamset_reviewer',
                           'beamset_approval_time',
                           'plan_approved',
                           'plan_exported',
                           'plan_reviewer',
                           'plan_approval_time'])
    plan_approved = False
    plan_reviewer = ""
    plan_time = ""
    plan_exported = False
    beamset_approved = False
    beamset_reviewer = ""
    beamset_time = ""
    beamset_exported = False
    try:
        if beamset.Review.ApprovalStatus == 'Approved':
            beamset_approved = True
            beamset_reviewer = beamset.Review.ReviewerName
            beamset_time = parser.parse(str(beamset.Review.ReviewTime))
            beamset_exported = beamset.Review.HasBeenExported
            if plan.Review.ApprovalStatus == 'Approved':
                plan_approved = True
                plan_reviewer = plan.Review.ReviewerName
                plan_time = parser.parse(str(plan.Review.ReviewTime))
                plan_exported = plan.Review.HasBeenExported
        else:
            plan_approved = False
            plan_reviewer = plan.Review.ReviewerName
            plan_time = parser.parse(str(plan.Review.ReviewTime))
            plan_exported = plan.Review.HasBeenExported
    except AttributeError:
        pass
    approval = Approval(beamset_approved=beamset_approved,
                        beamset_exported=beamset_exported,
                        beamset_reviewer=beamset_reviewer,
                        beamset_approval_time=beamset_time,
                        plan_approved=plan_approved,
                        plan_exported=plan_exported,
                        plan_reviewer=plan_reviewer,
                        plan_approval_time=plan_time)
    return approval


def check_beamset_approved(rso, **kwargs):
    """
    Check if a plan is approved
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
        physics_review: Bool: True then beamset is expected to be approved

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]
    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: THI: Plan: Anal_THI
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA

    """
    child_key = "Beamset approval status"
    physics_review = kwargs.get('physics_review')

    approval_status = approval_info(rso.plan, rso.beamset)
    if approval_status.beamset_approved:
        message_str = "Beamset: {} was approved by {} on {}".format(
            rso.beamset.DicomPlanLabel,
            approval_status.beamset_reviewer,
            approval_status.beamset_approval_time
        )
        pass_result = PASS
    else:
        message_str = "Beamset: {} is not approved".format(
            rso.beamset.DicomPlanLabel)
        if physics_review:
            pass_result = FAIL
        else:
            pass_result = ALERT
    return pass_result, message_str


def get_volumes(geometries):
    vols = {g.OfRoi.Name: g.GetRoiVolume() for g in geometries}
    return vols


def get_slice_positions(rso):
    # Get slice positions in linear array
    slice_positions = np.array(rso.exam.Series[0].ImageStack.SlicePositions)
    #
    # Starting corner
    image_corner = rso.exam.Series[0].ImageStack.Corner
    #
    # Actual z positions
    dicom_slice_positions = image_corner.z + slice_positions
    return dicom_slice_positions


def couch_type_correct(rso):
    child_key = 'Couch type correct'
    # Abbreviate geometries
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    roi_list = [r.OfRoi.Name for r in rg]
    beam = rso.beamset.Beams[0]
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    wrong_supports = []
    correct_supports = []
    if current_machine.Name in TRUEBEAM_DATA['MACHINES']:
        wrong_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
    elif current_machine.Name in TOMO_DATA['MACHINES']:
        wrong_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
    if wrong_supports:
        message_str = 'Support Structure(s) {} are INCORRECT for  machine {}'.format(
            wrong_supports, current_machine.Name)
        pass_result = FAIL
    elif correct_supports:
        message_str = 'Support Structure(s) {} are correct for machine {}'.format(
            correct_supports, current_machine.Name)
        pass_result = PASS
    else:
        message_str = 'No couch structure found'
        pass_result = ALERT
    # Prepare output
    return pass_result, message_str


def pass_control_point_spacing(s, s0, spacing):
    if not s0:
        if s.DeltaGantryAngle <= spacing:
            return True
        else:
            return False
    else:
        if s.DeltaGantryAngle - s0.DeltaGantryAngle <= spacing:
            return True
        else:
            return False


def message_format_control_point_spacing(beam_spacing_failures, spacing):
    # Takes in a message dictionary that is labeled per beam, then parses
    if beam_spacing_failures:
        for b, v in beam_spacing_failures.items():
            message_str = 'Beam {}: Gantry Spacing Exceeds {} in Control Points {}\n' \
                .format(b, spacing, v)
            message_result = FAIL
    else:
        message_str = "No control points > {} detected".format(spacing)
        message_result = PASS
    return message_str, message_result


def check_control_point_spacing(rso, **kwargs):
    """
    bs: RayStation beamset
    expected: Integer delineating the gantry angle between control points in a beam
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
    """
    expected = kwargs.get('expected')
    child_key = 'Control Point Spacing'
    beam_result = {}
    for b in rso.beamset.Beams:
        s0 = None
        fails = []
        for s in b.Segments:
            if not pass_control_point_spacing(s, s0, spacing=expected):
                fails.append(s.SegmentNumber + 1)
            s0 = s
        if fails:
            beam_result[b.Name] = fails
    message_str, pass_result = message_format_control_point_spacing(beam_spacing_failures=beam_result,
                                                                    spacing=expected)
    return pass_result, message_str


def check_transfer_approved(rso, ):
    """

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    Returns:
        message (list str): [Pass_Status, Message String]

    """
    child_key = "Transfer Beamset approval status"
    parent_beamset_name = rso.beamset.DicomPlanLabel
    daughter_plan_name = rso.plan.Name + TOMO_DATA['PLAN_TR_SUFFIX']
    if TOMO_DATA['MACHINES'][0] in rso.beamset.MachineReference['MachineName']:
        daughter_machine = TOMO_DATA['MACHINES'][1]
    else:
        daughter_machine = TOMO_DATA['MACHINES'][0]

    daughter_beamset_name = parent_beamset_name[:8] \
                            + TOMO_DATA['PLAN_TR_SUFFIX'] \
                            + daughter_machine[-3:]
    plan_names = [p.Name for p in rso.case.TreatmentPlans]
    beamset_names = [bs.DicomPlanLabel for p in rso.case.TreatmentPlans for bs in p.BeamSets]
    if daughter_beamset_name in beamset_names and daughter_plan_name in plan_names:
        transfer_beamset = rso.case.TreatmentPlans[daughter_plan_name].BeamSets[daughter_beamset_name]
    else:
        transfer_beamset = None
        message_str = "Beamset: {} is missing a transfer plan!".format(rso.beamset.DicomPlanLabel)
        pass_result = FAIL
    if transfer_beamset:
        approval_status = approval_info(rso.plan, transfer_beamset)
        if approval_status.beamset_approved:
            message_str = "Transfer Beamset: {} was approved by {} on {}".format(
                transfer_beamset.DicomPlanLabel,
                approval_status.beamset_reviewer,
                approval_status.beamset_approval_time
            )
            pass_result = PASS
        else:
            message_str = "Beamset: {} is not approved".format(
                transfer_beamset.DicomPlanLabel)
            pass_result = FAIL
    return pass_result, message_str


def check_edw_MU(rso):
    """
    Checks to see if all MU are greater than the EDW limit
    Args:
        beamset:

    Returns:
        messages: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_13May2022, C1
        PASS: ChwR_3DC_R0A0
        FAIL: ChwR_3DC_R2A0
    """
    child_key = "EDW MU Check"
    edws = {}
    for b in rso.beamset.Beams:
        try:
            if b.Wedge:
                if 'EDW' in b.Wedge.WedgeID:
                    edws[b.Name] = b.BeamMU
        except AttributeError:
            logging.debug('No wedge object in {} with technique {}. Electrons?'.format(
                rso.beamset.DicomPlanLabel, rso.beamset.DeliveryTechnique))
            break
    if edws:
        passing = True
        edw_passes = []
        edw_message = "Beam(s) have EDWs: "
        for bn, mu in edws.items():
            if mu < EDW_MU_LIMIT:
                passing = False
                edw_message += "{}(MU)={:.2f},".format(bn, mu)
            else:
                edw_passes.append(bn)
        if passing:
            edw_message += "{} all with MU > {}".format(edw_passes, EDW_MU_LIMIT)
        else:
            edw_message += "< {}".format(EDW_MU_LIMIT)
    else:
        passing = True
        edw_message = "No beams with EDWs found"

    if passing:
        pass_result = PASS
        message_str = edw_message
    else:
        pass_result = FAIL
        message_str = edw_message
    return pass_result, message_str


def check_common_isocenter(rso, **kwargs):
    """
    Checks all beams in beamset for shared isocenter

    Args:
        beamset (object):
        tolerance (flt): largest acceptable difference in isocenter location
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    """
    tolerance = kwargs.get('tolerance')
    child_key = "Isocenter Position Identical"
    initial_beam_name = rso.beamset.Beams[0].Name
    iso_pos_x = rso.beamset.Beams[0].Isocenter.Position.x
    iso_pos_y = rso.beamset.Beams[0].Isocenter.Position.y
    iso_pos_z = rso.beamset.Beams[0].Isocenter.Position.z
    iso_differs = []
    iso_match = []
    for b in rso.beamset.Beams:
        b_iso = b.Isocenter.Position
        if all([isclose(b_iso.x, iso_pos_x, rel_tol=tolerance, abs_tol=0.0),
                isclose(b_iso.y, iso_pos_y, rel_tol=tolerance, abs_tol=0.0),
                isclose(b_iso.z, iso_pos_z, rel_tol=tolerance, abs_tol=0.0)]):
            iso_match.append(b.Name)
        else:
            iso_differs.append(b.Name)
    if iso_differs:
        pass_result = FAIL
        message_str = "Beam(s) {} differ in isocenter location from beam {}".format(iso_differs, initial_beam_name)
    else:
        pass_result = PASS
        message_str = "Beam(s) {} all share the same isocenter to within {} mm".format(iso_match, tolerance)
    return pass_result, message_str


def check_tomo_isocenter(rso):
    """
    Checks isocenter for lateral less than 2 cm.

    Args:
        rso (object): Named tuple of ScriptObjects
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    """
    child_key = "Isocenter Lateral Acceptable"
    iso_pos_x = rso.beamset.Beams[0].Isocenter.Position.x
    if np.less_equal(abs(iso_pos_x), TOMO_DATA['LATERAL_ISO_MARGIN']):
        pass_result = PASS
        message_str = "Isocenter [{}] lateral shift is acceptable: {} < {} cm".format(
            rso.beamset.Beams[0].Isocenter.Annotation.Name,
            iso_pos_x,
            TOMO_DATA['LATERAL_ISO_MARGIN'])
    else:
        pass_result = FAIL
        message_str = "Isocenter [{}] lateral shift is inconsistent with indexing: {} > {} cm!".format(
            rso.beamset.Beams[0].Isocenter.Name,
            iso_pos_x,
            TOMO_DATA['LATERAL_ISO_MARGIN'])
    return pass_result, message_str


def check_bolus_included(rso):
    """

    Args:

    Returns:
        message: list of lists of format: [parent key, key, value, result]
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, ChwL
        Pass: Bolus_Roi_Check_Pass: ChwL_VMA_R1A0
        Fail: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    child_key = "Bolus Application"
    exam_name = rso.exam.Name
    roi_list = ExamTests.get_roi_list(rso.case, exam_name=exam_name)
    bolus_names = ExamTests.match_roi_name(roi_names=BOLUS_NAMES, roi_list=roi_list)
    if bolus_names:
        fail_str = "Stucture(s) {} named bolus, ".format(bolus_names) \
                   + "but not applied to beams in beamset {}".format(rso.beamset.DicomPlanLabel)
        try:
            applied_boli = set([bolus.Name for b in rso.beamset.Beams for bolus in b.Boli])
            if any(bn in applied_boli for bn in bolus_names):
                bolus_matches = {bn: [] for bn in bolus_names}
                for ab in applied_boli:
                    bolus_matches[ab].extend([b.Name for b in rso.beamset.Beams
                                              for bolus in b.Boli
                                              if bolus.Name == ab])
                pass_result = PASS
                message_str = "".join(
                    ['Roi {0} applied on beams {1}'.format(k, v) for k, v in bolus_matches.items()])
            else:
                pass_result = FAIL
                message_str = fail_str
        except AttributeError:
            pass_result = FAIL
            message_str = fail_str
    else:
        message_str = "No rois including {} found for Exam {}".format(BOLUS_NAMES, exam_name)
        pass_result = PASS
    return pass_result, message_str


# DOSE CHECKS
def check_fraction_size(rso):
    """
    Check the fraction size for common errors
    Args:
        rso: Raystation Beamset Object

    Returns:
        message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, Fraction_Size_Check
        Pass: Pelv_THI_R0A0
        Fail: Pelv_T3D_R0A0
    """
    child_key = 'Check Fractionation'
    results = {0: FAIL, 1: ALERT, 2: PASS}
    num_fx = rso.beamset.FractionationPattern.NumberOfFractions
    pass_result = results[2]
    message_str = 'Beamset {} fractionation not flagged'.format(rso.beamset.DicomPlanLabel)
    rx_dose = None
    try:
        rx_dose = rso.beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue
    except AttributeError:
        pass_result = results[1]
        message_str = 'No Prescription is Defined for Beamset'.format(rso.beamset.DicomPlanLabel)
    #
    # Look for matches in dose pairs
    if rx_dose:
        for t in DOSE_FRACTION_PAIRS:
            if t[0] == num_fx and t[1] == rx_dose:
                pass_result = results[1]
                message_str = 'Potential fraction/dose transcription error, ' \
                              + 'check with MD to confirm {} fractions should be delivered'.format(num_fx) \
                              + ' and dose per fraction {:.2f} Gy'.format(int(rx_dose / 100. / num_fx))
    return pass_result, message_str


def check_no_fly(rso):
    """

    Args:
        rso:

    Returns:
    message (list str): [Pass_Status, Message String]

    Test Patient:
        PASS: Script_Testing, #ZZUWQA_ScTest_13May2022, ChwR_3DC_R0A0
        FAIL: Script_Testing, #ZZUWQA_ScTest_13May2022b, Esop_VMA_R1A0
    """
    try:
        no_fly_dose = rso.plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName=NO_FLY_NAME, DoseType='Max')
        if no_fly_dose > NO_FLY_DOSE:
            message_str = "{} is potentially infield. Dose = {:.2f} cGy (exceeding tolerance {:.2f} cGy)".format(
                NO_FLY_NAME, no_fly_dose, NO_FLY_DOSE)
            pass_result = FAIL
        else:
            message_str = "{} is likely out of field. Dose = {:.2f} cGy (tolerance {:.2f} cGy)".format(
                NO_FLY_NAME, no_fly_dose, NO_FLY_DOSE)
            pass_result = PASS
    except Exception as e:
        if "exists no ROI" in e.Message:
            message_str = "No ROI {} found, Incline Board not used"
            pass_result = PASS
        else:
            message_str = "Unknown error in looking for incline board info {}".format(e.Message)
            pass_result = ALERT

    return pass_result, message_str


def make_unsubtracted_dose_structure(pdata, dose_value):
    """
    Make the structure for the dose threshold supplied
    makes unsubtracted_doses (RS Region of Interest Object) with name like <5%Rx>
    pdata: exactly the same as pdiddy
    dose_thresholds_normalized ({dose_roi_names: dose_levels(int)}): dose levels in cGy
    """
    # threshold_level = (float(d) / 100.) * float(rx)  # Threshold in cGy
    roi_name = str(dose_value / 100.) + '_Gy'
    roi_name = pdata.case.PatientModel.GetUniqueRoiName(DesiredName=roi_name)
    raw_geometry = pdata.case.PatientModel.CreateRoi(
        Name=roi_name,
        Color='Gray',
        Type='Control')
    # Get the Region of Interest object
    roi = pdata.case.PatientModel.RegionsOfInterest[roi_name]
    # Make an roi geometry that is at least the threshold level dose
    try:
        roi.CreateRoiGeometryFromDose(
            DoseDistribution=pdata.plan.TreatmentCourse.TotalDose,
            ThresholdLevel=dose_value)
    except Exception as e:
        print(e)
    return roi_name


def make_sphere_roi(rso, roi_name):
    # Make a sphere centered in roi_name
    center = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name].GetCenterOfRoi()
    sphere_roi_name = rso.case.PatientModel.GetUniqueRoiName(DesiredName="Sphere")
    rso.case.PatientModel.CreateRoi(Name=sphere_roi_name,
                                    Color='Pink',
                                    Type='Control')
    sphere_roi = rso.case.PatientModel.RegionsOfInterest[sphere_roi_name]
    sphere_roi.CreateSphereGeometry(Radius=PACEMAKER_SEARCH_DISTANCE,
                                    Examination=rso.exam,
                                    Center=center,
                                    Representation='Voxels',
                                    VoxelSize=1)
    return sphere_roi_name


def make_dose_warning_zone(rso, dose_level, prv_name, roi_name):
    # Get the center of the pacer prv
    sphere_roi_name = make_sphere_roi(rso, prv_name)
    # Build the warning zone structure
    roi_name = rso.case.PatientModel.GetUniqueRoiName(DesiredName=roi_name)
    roi_geometry = rso.case.PatientModel.CreateRoi(
        Name=roi_name,
        Color='Gray',
        Type='Control')
    margin_settings = {"Type": "Expand", "Superior": 0.,
                       "Inferior": 0.,
                       "Anterior": 0.,
                       "Posterior": 0.,
                       "Right": 0.,
                       "Left": 0.,
                       }
    rso.case.PatientModel.RegionsOfInterest[roi_name].SetAlgebraExpression(
        ExpressionA={
            "Operation": "Union",
            "SourceRoiNames": [dose_level],
            "MarginSettings": margin_settings,
        },
        ExpressionB={
            "Operation": "Union",
            "SourceRoiNames": [sphere_roi_name],
            "MarginSettings": margin_settings,
        },
        ResultOperation="Intersection",
        ResultMarginSettings=margin_settings,
    )
    rso.case.PatientModel.RegionsOfInterest[roi_name].UpdateDerivedGeometry(
        Examination=rso.exam, Algorithm="Auto")
    rso.case.PatientModel.RegionsOfInterest[sphere_roi_name].DeleteRoi()
    return roi_name


# Evaluate pacemaker doses
def dose_below_tolerance(plan, target, tolerance):
    try:
        dose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(
            RoiName=target,
            DoseType='Max')
        if dose <= tolerance:
            return True, dose
        else:
            return False, dose
    except Exception as e:
        return False, "Unknown error in looking for pacemaker info {}".format(e.Message)


#
def evaluate_pacer_safe_distance(rso):
    # Now generate an extra check looking for the pacemaker tolerance dose

    deletion_rois = []
    dose_name = str(int(PACEMAKER_DOSE / 100.)) + ' Gy'
    dose_level = make_unsubtracted_dose_structure(pdata=rso,
                                                  dose_value=PACEMAKER_DOSE)
    deletion_rois.append(dose_level)
    # Construct the nearby dose
    warning_zone = make_dose_warning_zone(rso=rso, dose_level=dose_level,
                                          prv_name=PACEMAKER_PRV_NAME,
                                          roi_name=PACEMAKER_NAME + "_EZ")
    deletion_rois.append(warning_zone)
    if rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[warning_zone].HasContours():
        distance = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiSurfaceToSurfaceDistanceBasedOnDT(
            ReferenceRoiName=warning_zone, TargetRoiName=PACEMAKER_PRV_NAME)
    else:
        # No contours found in the pacemaker search distance
        distance = {'Min': float('inf')}
    if distance['Min'] <= PACEMAKER_DISTANCE_TOLERANCE:
        message_str = f"{dose_name} isodose is within {PACEMAKER_DISTANCE_TOLERANCE:.0f} cm from " \
                      + f"{PACEMAKER_PRV_NAME} ({distance['Min']:.1f} cm)!!"
        safe_distance = False
    else:
        message_str = f"{dose_name} isodose is > {PACEMAKER_DISTANCE_TOLERANCE:.0f} cm from " \
                      + f"{PACEMAKER_PRV_NAME} ({distance['Min']:.1f} cm)"
        safe_distance = True

    for d in deletion_rois:
        rso.case.PatientModel.RegionsOfInterest[d].DeleteRoi()
    return safe_distance, message_str


def energy_acceptable(rso, energy_list=["6", "6 FFF", "10", "10 FFF"]):
    """

    Args:
        rso:
        energy_list:

    Returns:

    """


def check_pacemaker(rso):
    """
        Check pacemaker dose is less than 2. Alert if PRV exceeds dose
        Args:
            rso:

        Returns:
        message (list str): [Pass_Status, Message String]

        Test Patient:
            PASS but warn about distance: Script_Testing, ZZUWQA_ScTest_24Aug2022, LunR_3DC_R2A0
            FAIL warn about distance: Script_Testing, ZZUWQA_ScTest_24Aug2022, LunR_VMA_R1A0
            FAIL dose limit: Script_Testing, ZZUWQA_ScTest_24Aug2022, LunR_VMA_R0A0
    """
    # Get the current list of rois
    roi_list = ExamTests.get_roi_list(rso.case, exam_name=rso.exam.Name)
    # Find the pacemaker names we are using
    pacer_roi_list = ExamTests.match_roi_name(roi_names=[PACEMAKER_NAME], roi_list=roi_list)
    pacer_prv_roi_list = ExamTests.match_roi_name(roi_names=[PACEMAKER_PRV_NAME], roi_list=roi_list)

    if pacer_roi_list:
        pacer_underdose, pacer_dose = dose_below_tolerance(rso.plan, target=PACEMAKER_NAME, tolerance=PACEMAKER_DOSE)
        if pacer_prv_roi_list:
            prv_underdose, prv_dose = dose_below_tolerance(rso.plan, target=PACEMAKER_PRV_NAME,
                                                           tolerance=PACEMAKER_DOSE)
            if type(pacer_dose) == str:
                message_str = pacer_dose
                pass_result = ALERT
            elif type(prv_dose) == str:
                message_str = prv_dose
                pass_result = ALERT
            elif prv_underdose and pacer_underdose:
                safe_distance, message_dist = evaluate_pacer_safe_distance(rso)
                if safe_distance:
                    message_str = f"{PACEMAKER_NAME} and {PACEMAKER_PRV_NAME} are likely out of field." \
                                  + f"Dose = {pacer_dose:.0f} and {prv_dose:.0f} cGy (tol={PACEMAKER_DOSE:.0f} cGy). " \
                                  + message_dist
                    pass_result = PASS
                else:
                    message_str = message_dist
                    pass_result = ALERT
            elif pacer_underdose:
                message_str = f"Dose to {PACEMAKER_NAME} = {pacer_dose:.0f} ok, but Dose to {PACEMAKER_PRV_NAME}" \
                              + f" = {prv_dose:.0f} may be in field. " \
                              + f"(tol={PACEMAKER_DOSE:.0f} cGy)"
                pass_result = FAIL
            else:
                message_str = f"{PACEMAKER_NAME} and {PACEMAKER_PRV_NAME} are likely in field!! " \
                              + f"Dose = {pacer_dose:.0f} and {prv_dose:.0f} cGy (tol={PACEMAKER_DOSE:.0f} cGy)"
                pass_result = FAIL
        else:
            message_str = f"No ROI {PACEMAKER_PRV_NAME} found, no pacemaker prv contoured"
            pass_result = FAIL
    else:
        message_str = f"No ROI {PACEMAKER_NAME} found, no pacemaker contoured"
        pass_result = PASS
    return pass_result, message_str


def check_dose_grid(rso):
    """
    Based on plan name and dose per fraction, determines size of appropriate grid.
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    Returns:
        message (list str): [Pass_Status, Message String]

    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """
    child_key = "Dose Grid Size Check"
    #
    # Get beamset dose grid
    rs_grid = rso.beamset.FractionDose.InDoseGrid.VoxelSize
    grid = (rs_grid.x, rs_grid.y, rs_grid.z)
    #
    # Try (if specified to get dose per fraction)
    try:
        total_dose = rso.beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue
        num_fx = rso.beamset.FractionationPattern.NumberOfFractions
        fractional_dose = total_dose / float(num_fx)
    except AttributeError:
        num_fx = None
        fractional_dose = None
    #
    # Get beamset name is see if there is a match
    message_str = ""
    pass_result = None
    for k, v in GRID_PREFERENCES.items():
        # Check to see if plan obeys a naming convention we have flagged
        if any([n in rso.beamset.DicomPlanLabel for n in v['PLAN_NAMES']]):
            name_match = []
            for n in v['PLAN_NAMES']:
                if n in rso.beamset.DicomPlanLabel:
                    name_match.append(n)
            violation_list = [i for i in grid if i > v['DOSE_GRID']]
            if violation_list:
                message_str = "Dose grid too large for plan type {}. ".format(name_match) \
                              + "Grid size is {} cm and should be {} cm".format(grid, v['DOSE_GRID'])
                pass_result = FAIL
            else:
                message_str = "Dose grid appropriate for plan type {}. ".format(name_match) \
                              + "Grid size is {} cm  and ≤ {} cm".format(grid, v['DOSE_GRID'])
                pass_result = PASS
        # Look for fraction size violations
        elif v['FRACTION_SIZE_LIMIT']:
            if not fractional_dose:
                message_str = "Dose grid cannot be evaluated for this plan. No fractional dose"
                pass_result = FAIL
            elif fractional_dose >= v['FRACTION_SIZE_LIMIT'] and \
                    any([g > v['DOSE_GRID'] for g in grid]):
                message_str = "Dose grid may be too large for this plan based on fractional dose " \
                              + "{:.0f} > {:.0f} cGy. ".format(fractional_dose, v['FRACTION_SIZE_LIMIT']) \
                              + "Grid size is {} cm and should be {} cm".format(grid, v['DOSE_GRID'])
                pass_result = FAIL
    # Plan is a default plan. Just Check against defaults
    if not message_str:
        violation_list = [i for i in grid if i > DOSE_GRID_DEFAULT]
        if violation_list:
            message_str = "Dose grid too large. " \
                          + "Grid size is {} cm and should be {} cm".format(grid, DOSE_GRID_DEFAULT)
            pass_result = FAIL
        else:
            message_str = "Dose grid appropriate." \
                          + "Grid size is {} cm  and ≤ {} cm".format(grid, DOSE_GRID_DEFAULT)
            pass_result = PASS
    return pass_result, message_str


def check_slice_thickness(rso):
    """
    Checks the current exam used in this case for appropriate slice thickness
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
    Returns:
        messages: [[str1, ...,],...]: [[parent_key, child_key, messgae display, Pass/Fail/Alert]]

    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """
    child_key = 'Slice thickness Comparison'
    message_str = ""
    for k, v in GRID_PREFERENCES.items():
        # Check to see if plan obeys a naming convention we have flagged
        if any([n in rso.beamset.DicomPlanLabel for n in v['PLAN_NAMES']]):
            nominal_slice_thickness = v['SLICE_THICKNESS']
            for s in rso.exam.Series:
                slice_positions = np.array(s.ImageStack.SlicePositions)
                slice_thickness = np.diff(slice_positions)
                if np.isclose(slice_thickness, nominal_slice_thickness).all() \
                        or all(slice_thickness < nominal_slice_thickness):
                    message_str = 'Slice spacing {:.3f} ≤ {:.3f} cm appropriate for plan type {}'.format(
                        slice_thickness.max(), nominal_slice_thickness, v['PLAN_NAMES'])
                    pass_result = PASS
                else:
                    message_str = 'Slice spacing {:.3f} > {:.3f} cm TOO LARGE for plan type {}'.format(
                        slice_thickness.max(), nominal_slice_thickness, v['PLAN_NAMES'])
                    pass_result = FAIL
    if not message_str:
        for s in rso.exam.Series:
            slice_positions = np.array(s.ImageStack.SlicePositions)
            slice_thickness = np.diff(slice_positions)
        message_str = 'Plan type unknown, check slice spacing {:.3f} cm carefully'.format(
            slice_thickness.max())
        pass_result = ALERT
    return pass_result, message_str


def closed_leaf_gaps(banks, min_gap_moving):
    threshold = 1e-6
    leaf_gaps = np.empty_like(banks, dtype=bool)
    leaf_gaps[:, 0, :] = abs(banks[:, 0, :] - banks[:, 1, :]) < \
                         (1 + threshold) * min_gap_moving
    leaf_gaps[:, 1, :] = leaf_gaps[:, 0, :]
    return leaf_gaps


def get_segment_number(beam):
    # Get total number of segments in the beam
    try:
        seg_num = 0
        # Find the number of leaves in the first segment to initialize the array
        for s in beam.Segments:
            seg_num += 1
    except:
        return None
    return seg_num


def get_relative_weight(beam):
    # Get each segment weight
    weights = []
    for s in beam.Segments:
        weights.append(s.RelativeWeight)
    return weights


def get_mlc_bank_array(beam):
    # Find the number of segments
    segment_number = get_segment_number(beam)
    if not segment_number:
        return None
    else:
        s0 = beam.Segments[0]
    #
    # Get the number of leaves
    num_leaves_per_bank = int(s0.LeafPositions[0].shape[0])
    # Bank array declaration
    banks = np.empty((num_leaves_per_bank, 2, segment_number))
    # Combine the segments into a single ndarray of size:
    # number of MLCs x number of banks x number of segments
    s_i = 0
    for s in beam.Segments:
        # Take the bank positions on X1-bank, and X2 Bank and put them in column 0, 1 respectively
        banks[:, 0, s_i] = s.LeafPositions[0]  # np.dstack((banks, bank))
        banks[:, 1, s_i] = s.LeafPositions[1]
        s_i += 1
    return banks


def filter_banks(beam, banks):
    # MLCs x number of banks x number of segments
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Min gap
    min_gap_moving = current_machine.Physics.MlcPhysics.MinGapMoving
    # Find all closed leaf gaps and zero them
    closed = closed_leaf_gaps(banks, min_gap_moving)
    # Filtered banks is dimension [N_MLC,Bank Index, Control Points]
    filtered_banks = np.copy(banks)
    filtered_banks[closed] = np.nan
    return filtered_banks


def compute_mcs(beam, override_square=False):
    # Step and Shoot
    #
    # Get the beam mlc banks
    banks = get_mlc_bank_array(beam)
    weights = get_relative_weight(beam)
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Leaf Widths
    leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
    #
    # Segment weights
    segment_weights = np.array(weights)
    #
    # Filter the banks
    filtered_banks = filter_banks(beam, banks)
    #
    # Square field test
    if override_square:
        filtered_banks[:, 0, :] = np.nan
        filtered_banks[:, 1, :] = np.nan
        filtered_banks[32:38, 0, :] = -2.
        filtered_banks[32:38, 1, :] = 2.
    # Mask out the closed mlcs
    mask_banks = np.ma.masked_invalid(filtered_banks)
    #
    # Jm Number of active leaves in both banks in each control point
    jm = np.count_nonzero(mask_banks, axis=0) - 1.  # Subtract for n+1 leaf without next in mask
    # Max position
    pos_max = np.amax(mask_banks, axis=0) - np.amin(mask_banks, axis=0)  # Checked
    # Handle amax = amin (rectangles)
    if np.amax(mask_banks[:, 0, :]) == np.amin(mask_banks[:, 0, :]):
        pos_max[0, :] = np.amax(mask_banks[:, 0, :])
    if np.amax(mask_banks[:, 1, :]) == np.amin(mask_banks[:, 1, :]):
        pos_max[1, :] = np.amax(mask_banks[:, 1, :])
    #
    # Absolute value of difference in single bank leaf movement
    pos_max = np.abs(pos_max)
    #
    # Difference in leaf positions for each segment on each bank
    # Absolute value since the relative difference between leaves on the same
    # bank is used
    banks_diff = np.abs(mask_banks[:-1, :, :] - mask_banks[1:, :, :])
    separated_lsv = np.divide(np.sum(pos_max - banks_diff, axis=0), (jm * pos_max))
    # Compute the leaf sequence variability
    lsv = separated_lsv[0, :] * separated_lsv[1, :]
    weighted_lsv = np.sum(lsv * segment_weights)
    #
    # AAV calculation
    apertures = mask_banks * leaf_widths[:, None, None]
    mlc_diff = apertures[:, 1, :] - apertures[:, 0, :]
    segment_aperture_area = np.sum(mlc_diff, axis=0)
    #
    # CIAO
    beam_ciao = np.amax(mlc_diff, axis=1)
    aav = segment_aperture_area / np.sum(beam_ciao)
    weighted_aav = np.sum(aav * segment_weights)
    #
    # MCS calc
    mcsv = np.sum(lsv * aav * segment_weights)
    return weighted_lsv, weighted_aav, mcsv


def compute_mcs_masi(beam, override_square=False):
    #
    # Get the beam mlc banks
    banks = get_mlc_bank_array(beam)
    weights = get_relative_weight(beam)
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Leaf Widths
    leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
    #
    # Segment weights
    segment_weights = np.array(weights)
    averaged_segment_weights = segment_weights[0:-1]  # Last control point is zero MU
    #
    # Filter the banks
    filtered_banks = filter_banks(beam, banks)
    #
    # Square field test
    if override_square:
        filtered_banks[:, 0, :] = np.nan
        filtered_banks[:, 1, :] = np.nan
        filtered_banks[32:38, 0, :] = -2.
        filtered_banks[32:38, 1, :] = 2.
    # Mask out the closed mlcs
    mask_banks = np.ma.masked_invalid(filtered_banks)
    #
    # Jm Number of active leaves in both banks in each control point
    jm = np.count_nonzero(mask_banks, axis=0) - 1.  # Subtract for n+1 leaf without next in mask
    # Max position
    pos_max = np.amax(mask_banks, axis=0) - np.amin(mask_banks, axis=0)  # Checked
    # Handle amax = amin (rectangles)
    if np.amax(mask_banks[:, 0, :]) == np.amin(mask_banks[:, 0, :]):
        pos_max[0, :] = np.amax(mask_banks[:, 0, :])
    if np.amax(mask_banks[:, 1, :]) == np.amin(mask_banks[:, 1, :]):
        pos_max[1, :] = np.amax(mask_banks[:, 1, :])
    # Absolute value of difference in single bank leaf movement
    pos_max = np.abs(pos_max)
    #
    # Difference in leaf positions for each segment on each bank
    banks_diff = np.abs(mask_banks[:-1, :, :] - mask_banks[1:, :, :])
    separated_lsv = np.divide(np.sum(pos_max - banks_diff, axis=0), (jm * pos_max))
    # Compute the leaf sequence variability
    lsv = separated_lsv[0, :] * separated_lsv[1, :]
    vmat_lsv = (lsv[:-1] + lsv[1:]) / 2.
    weighted_vmat_lsv = np.sum(vmat_lsv * segment_weights[:-1])
    #
    # AAV calculation
    apertures = mask_banks * leaf_widths[:, None, None]
    mlc_diff = apertures[:, 1, :] - apertures[:, 0, :]
    segment_aperature_area = np.sum(mlc_diff, axis=0)
    #
    # CIAO
    beam_ciao = np.amax(mlc_diff, axis=1)
    aav = segment_aperature_area / np.sum(beam_ciao)
    vmat_aav = (aav[:-1] + aav[1:]) / 2.
    weighted_vmat_aav = np.sum(vmat_aav * segment_weights[:-1])
    #
    # MCS calc
    mcsv = np.sum(vmat_lsv * vmat_aav * averaged_segment_weights)
    return weighted_vmat_lsv, weighted_vmat_aav, mcsv


def get_machine(machine_name):
    """Finds the current machine name from the list of currently commissioned machines
    :param: machine_name (name of the machine in raystation,
    usually this is machine_name = beamset.MachineReference.MachineName
    return: machine (RS object)"""
    machine_db = connect.get_current("MachineDB")
    machine = machine_db.GetTreatmentMachine(machineName=machine_name, lockMode=None)
    return machine


def compute_beam_properties(rso):
    # Compute MCS and any other desired beam properties
    child_key = "Beamset Complexity"
    message_str = "[Beam Name: LSV, AAV, MCS] :: "
    tech = rso.beamset.DeliveryTechnique
    pass_result = PASS
    for b in rso.beamset.Beams:
        if tech == 'DynamicArc':
            lsv, aav, mcs = compute_mcs_masi(b)
        elif tech == 'SMLC':
            # TODO Review versus a non segmented case with big opening differences
            lsv, aav, mcs = compute_mcs(b)
        else:
            message_str = 'Error Unknown technique {}'.format(tech)
            break
        message_str += '[{}: '.format(b.Name)
        # TODO: Sort MCS by technique then replace with PASS/FAIL
        # LSV
        if lsv < MCS_TOLERANCES['LSV']['MEAN'] - 2. * MCS_TOLERANCES['LSV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} OVERMOD,'.format(lsv)
        elif lsv > MCS_TOLERANCES['LSV']['MEAN'] + 2. * MCS_TOLERANCES['LSV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} UNDERMOD,'.format(lsv)
        else:
            message_str += '{:.3f},'.format(lsv)
        # AAV
        if aav < MCS_TOLERANCES['AAV']['MEAN'] - 2. * MCS_TOLERANCES['AAV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} OVERMOD,'.format(aav)
        elif aav > MCS_TOLERANCES['AAV']['MEAN'] + 2. * MCS_TOLERANCES['AAV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} UNDERMOD,'.format(aav)
        else:
            message_str += '{:.3f},'.format(aav)
        # MCS
        if mcs < MCS_TOLERANCES['MCS']['MEAN'] - 2. * MCS_TOLERANCES['MCS']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} OVERMOD,'.format(mcs)
        elif mcs > MCS_TOLERANCES['MCS']['MEAN'] + 2. * MCS_TOLERANCES['MCS']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} UNDERMOD,'.format(mcs)
        else:
            message_str += '{:.3f}'.format(mcs)
        message_str += '],'
    return pass_result, message_str
