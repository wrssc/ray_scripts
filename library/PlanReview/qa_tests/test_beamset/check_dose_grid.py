from PlanReview.review_definitions import GRID_PREFERENCES, \
    PASS, FAIL, DOSE_GRID_DEFAULT


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
                message_str = \
                    f"Dose grid too large for plan type {name_match}. " \
                    f"Grid size is {grid} cm and should be {v['DOSE_GRID']} cm"
                pass_result = FAIL
            else:
                message_str = \
                    f"Dose grid appropriate for plan type {name_match}" \
                    f". Grid size is {grid} cm  and ≤ {v['DOSE_GRID']} cm"
                pass_result = PASS
        # Look for fraction size violations
        elif v['FRACTION_SIZE_LIMIT']:
            if not fractional_dose:
                message_str = \
                    "Dose grid cannot be evaluated for this plan." \
                    "No fractional dose"
                pass_result = FAIL
            elif fractional_dose >= v['FRACTION_SIZE_LIMIT'] and \
                    any([g > v['DOSE_GRID'] for g in grid]):
                message_str = \
                    "Dose grid may be too large for this plan " \
                    f"based on fractional dose {fractional_dose:.0f} > " \
                    f"{v['FRACTION_SIZE_LIMIT']:.0f} cGy. " \
                    f"Grid size is {grid} cm and should be {v['DOSE_GRID']} cm"
                pass_result = FAIL
    # Plan is a default plan. Just Check against defaults
    if not message_str:
        violation_list = [i for i in grid if i > DOSE_GRID_DEFAULT]
        if violation_list:
            message_str = \
                "Dose grid too large. " \
                f"Grid size is {grid} cm and should be {DOSE_GRID_DEFAULT} cm"
            pass_result = FAIL
        else:
            message_str = \
                "Dose grid appropriate." \
                f"Grid size is {grid} cm  and ≤ {DOSE_GRID_DEFAULT} cm"
            pass_result = PASS
    return pass_result, message_str
