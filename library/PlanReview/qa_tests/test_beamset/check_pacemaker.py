from PlanReview.review_definitions import (
    PACEMAKER_NAME, PACEMAKER_DOSE, PACEMAKER_PRV_NAME, PASS, ALERT, FAIL,
    PACEMAKER_DISTANCE_TOLERANCE, PACEMAKER_SEARCH_DISTANCE)
from PlanReview.utils import get_roi_list, match_roi_name


def make_unsubtracted_dose_structure(pdata, dose_value):
    """
    Make the structure for the dose threshold supplied
    makes unsubtracted_doses (RS Region of Interest Object) with name like <5%Rx>
    patient_data: exactly the same as pdiddy
    dose_thresholds_normalized ({dose_roi_names: dose_levels(int)}): dose levels in cGy
    """
    # threshold_level = (float(d) / 100.) * float(rx)  # Threshold in cGy
    roi_name = str(dose_value / 100.) + '_Gy'
    roi_name = pdata.case.PatientModel.GetUniqueRoiName(DesiredName=roi_name)
    _ = pdata.case.PatientModel.CreateRoi(
        Name=roi_name, Color='Gray', Type='Control')
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
    center = rso.case.PatientModel.StructureSets[rso.exam.Name]\
        .RoiGeometries[roi_name].GetCenterOfRoi()
    sphere_roi_name = rso.case.PatientModel.GetUniqueRoiName(
        DesiredName="Sphere")
    rso.case.PatientModel.CreateRoi(
        Name=sphere_roi_name, Color='Pink', Type='Control')
    sphere_roi = rso.case.PatientModel.RegionsOfInterest[sphere_roi_name]
    sphere_roi.CreateSphereGeometry(
        Radius=PACEMAKER_SEARCH_DISTANCE, Examination=rso.exam,
        Center=center, Representation='Voxels', VoxelSize=1)
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
    # TODO: volume=patient.Cases[0].PatientModel.StructureSets[0].RoiGeometries[17].GetRoiVolume()
    # TODO: rel_volume = 0.03/volume
    # TODO: patient.Cases[0].TreatmentPlans[2].TreatmentCourse.TotalDose.GetDoseAtRelativeVolumes(
    #  RoiName='Pacemaker',RelativeVolumes=[ral_vol])
    try:
        dose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(
            RoiName=target,
            DoseType='Max')
        if dose <= tolerance:
            return True, dose
        else:
            return False, dose
    except Exception as e:
        return False, f"Unknown error in looking for pacemaker info {e}"


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
        distance = rso.case.PatientModel.StructureSets[
            rso.exam.Name].RoiSurfaceToSurfaceDistanceBasedOnDT(
            ReferenceRoiName=warning_zone, TargetRoiName=PACEMAKER_PRV_NAME)
    else:
        # No contours found in the pacemaker search distance
        distance = {'Min': float('inf')}
    if distance['Min'] <= PACEMAKER_DISTANCE_TOLERANCE:
        message_str = f"{dose_name} isodose is within " \
                      f"{PACEMAKER_DISTANCE_TOLERANCE:.0f} cm from " \
                      f"{PACEMAKER_PRV_NAME} ({distance['Min']:.1f} cm)!!"
        safe_distance = False
    else:
        message_str = f"{dose_name} isodose is > " \
                      f"{PACEMAKER_DISTANCE_TOLERANCE:.0f} cm from " \
                      f"{PACEMAKER_PRV_NAME} ({distance['Min']:.1f} cm)"
        safe_distance = True

    for d in deletion_rois:
        rso.case.PatientModel.RegionsOfInterest[d].DeleteRoi()
    return safe_distance, message_str


def check_pacemaker(rso):
    """
        Check pacemaker dose is less than 2. Alert if PRV exceeds dose
        Args:
            rso (namedtuple): RayStation Beamset Object

        Returns:
            message (list str): [Pass_Status, Message String]

        Test Patient:
            PASS but warn about distance: Script_Testing, ZZUWQA_ScTest_24Aug2022, LunR_3DC_R2A0
            FAIL warn about distance: Script_Testing, ZZUWQA_ScTest_24Aug2022, LunR_VMA_R1A0
            FAIL dose limit: Script_Testing, ZZUWQA_ScTest_24Aug2022, LunR_VMA_R0A0
    """
    # Get the current list of rois
    roi_list = get_roi_list(rso.case, exam_name=rso.exam.Name)
    # Find the pacemaker names we are using
    pacer_roi_list = match_roi_name(roi_names=[PACEMAKER_NAME], roi_list=roi_list)
    pacer_prv_roi_list = match_roi_name(
        roi_names=[PACEMAKER_PRV_NAME], roi_list=roi_list)

    if pacer_roi_list:
        pacer_underdose, pacer_dose = dose_below_tolerance(
            rso.plan, target=PACEMAKER_NAME, tolerance=PACEMAKER_DOSE)
        if pacer_prv_roi_list:
            prv_underdose, prv_dose = dose_below_tolerance(
                rso.plan, target=PACEMAKER_PRV_NAME, tolerance=PACEMAKER_DOSE)
            if type(pacer_dose) == str:
                message_str = pacer_dose
                pass_result = ALERT
            elif type(prv_dose) == str:
                message_str = prv_dose
                pass_result = ALERT
            elif prv_underdose and pacer_underdose:
                safe_distance, message_dist = evaluate_pacer_safe_distance(rso)
                if safe_distance:
                    message_str = \
                        f"{PACEMAKER_NAME} and {PACEMAKER_PRV_NAME}" \
                        f"are likely out of field. Dose = {pacer_dose:.0f}" \
                        f" and {prv_dose:.0f} cGy (tol={PACEMAKER_DOSE:.0f} " \
                        f"cGy). " + message_dist
                    pass_result = PASS
                else:
                    message_str = message_dist
                    pass_result = ALERT
            elif pacer_underdose:
                message_str = f"Dose to {PACEMAKER_NAME} = {pacer_dose:.0f} " \
                              f"ok, but Dose to {PACEMAKER_PRV_NAME}" \
                              f" = {prv_dose:.0f} may be in field. " \
                              f"(tol={PACEMAKER_DOSE:.0f} cGy)"
                pass_result = FAIL
            else:
                message_str = f"{PACEMAKER_NAME} and {PACEMAKER_PRV_NAME} are" \
                              f" likely in field!! Dose = {pacer_dose:.0f} " \
                              f"and {prv_dose:.0f} cGy (tol=" \
                              f"{PACEMAKER_DOSE:.0f} cGy)"
                pass_result = FAIL
        else:
            message_str = f"No ROI {PACEMAKER_PRV_NAME} found, no pacemaker" \
                          f" prv contoured"
            pass_result = FAIL
    else:
        message_str = f"No ROI {PACEMAKER_NAME} found, no pacemaker contoured"
        pass_result = PASS
    return pass_result, message_str
