""" Copy Goals
Script for copying goals to a clinical case in prep for export
Copies goals from one plan to another. Defines dose levels
Toggles to plan evaluation.
"""
import connect
import sys
import platform
import clr
import logging
import UserInterface
import StructureOperations as so


def isodose_reconfig(case, ref_dose, max_dose=None, levels=None):
    """
    This function takes the current case, an optional max_dose
    :param case: ScriptObject of RS case
    :param ref_dose: The normalization dose in Gy
    :param max_dose: an optional argument that can specify the maximum dose within the plan
    :param levels: a dictionary of relative isodose levels and colors levels[10]=[R, G, B]
    :return:
    """
    # Clear current contents
    if max_dose:
        max_ratio = max_dose / ref_dose
        max_isodose = int(100 * 0.99 * max_ratio)
    else:
        logging.info('No max dose found. Using 115%')
        max_isodose = int(115)

    dose_levels = {}
    if levels is None:
        dose_levels = {10: so.define_sys_color([127, 0, 255]),
                       20: so.define_sys_color([0, 0, 255]),
                       30: so.define_sys_color([0, 127, 255]),
                       40: so.define_sys_color([0, 255, 255]),
                       50: so.define_sys_color([0, 255, 127]),
                       60: so.define_sys_color([0, 255, 0]),
                       70: so.define_sys_color([127, 255, 0]),
                       80: so.define_sys_color([255, 255, 0]),
                       90: so.define_sys_color([255, 127, 0]),
                       95: so.define_sys_color([255, 0, 0]),
                       100: so.define_sys_color([255, 0, 255]),
                       105: so.define_sys_color([255, 0, 127]),
                       max_isodose: so.define_sys_color([128, 20, 20])}
    else:
        for k, v in levels.items():
            dose_levels[k] = so.define_sys_color(levels[k])

    dose_color_table = {}
    for k, v in dose_levels.items():
        dose_color_table[k] = v

    case.CaseSettings.DoseColorMap.ColorTable = dose_color_table
    case.CaseSettings.DoseColorMap.ReferenceValue = ref_dose
    case.CaseSettings.DoseColorMap.PresentationType = 'Absolute'


def find_max_dose_in_plan(examination, case, plan):
    rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries
    if so.check_structure_exists(case=case,
                                 structure_name='External_Clean',
                                 roi_list=rois,
                                 option='Check'):
        max_dose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName='External_Clean', DoseType='Max')
    elif so.check_structure_exists(case=case,
                                   structure_name='External',
                                   roi_list=rois,
                                   option='Check'):
        max_dose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName='External', DoseType='Max')
    else:
        max_dose = None

def main():
    """ Temp chunk of code to try to open an xml file"""
    try:
        ui = connect.get_current("ui")
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
    except:
        logging.warning("patient, case and examination must be loaded")

    # Configs
    source_plan = 'WBHA_05Nov2020'
    source_beamset = 'TOMO_30Gy'
    destination_plan = 'Clinical'
    destination_beamset = 'Clinical'
    rename = False
    if rename:
        # Open a dialog and ask what the clinical plan name will be
        input_dialog = UserInterface.InputDialog(
            inputs ={'input0':'Clinical Plan is A or B'},
            title='Choose input',
            datatype={'input0':'combo'},
            options={'input0':['A','B']}
        )
        response = input_dialog.show()
        if response == {}:
            sys.exit('script cancelled by user')
        clinical_plan_name = input_dialog.values['input0']
    # Save any user changes
    patient.Save()
    case.TreatmentPlans[source_plan].SetCurrent()
    plan = connect.get_current("Plan")
    case.TreatmentPlans[source_plan].BeamSets[source_beamset].SetCurrent()
    beamset = connect.get_current('BeamSet')
    clinical_beamset = case.TreatmentPlans[destination_plan].BeamSets[destination_plan]

    # Turn beamset visualization off
    for b in beamset.Beams:
        beamset.SetBeamIsVisible(BeamName = b.Name, IsVisible=False)
    for b in clinical_beamset.Beams:
        clinical_beamset.SetBeamIsVisible(BeamName = b.Name, IsVisible=False)

    # Copy goals to clinical plan
    source_eval = case.TreatmentPlans[source_plan].TreatmentCourse.EvaluationSetup
    dest_eval = case.TreatmentPlans[destination_plan].TreatmentCourse.EvaluationSetup
    roi_list = []
    for e in source_eval.EvaluationFunctions:
        dest_eval.CopyClinicalGoal(FunctionToCopy=e)
        r = e.ForRegionOfInterest.Name
        if r not in roi_list:
            roi_list.append(r)
    patient.Save()
    if rename:
        case.TreatmentPlans[destination_plan].BeamSets[destination_beamset].DicomPlanLabel = clinical_plan_name
        case.TreatmentPlans[destination_plan].Name = clinical_plan_name
        patient.Save()
        if clinical_plan_name == 'A':
            case.TreatmentPlans[source_plan].BeamSets[source_beamset].DicomPlanLabel = 'B'
            case.TreatmentPlans[source_plan].Name = "B"
        else:
            case.TreatmentPlans[source_plan].BeamSets[source_beamset].DicomPlanLabel = 'A'
            case.TreatmentPlans[source_plan].Name = "A"
        patient.Save()
    # Update Dose Grid structures in both plans
    # Update patient dose data
    case.TreatmentPlans[source_plan].BeamSets[source_beamset].FractionDose.UpdateDoseGridStructures()
    case.TreatmentPlans[source_plan].TreatmentCourse.TotalDose.UpdateDoseGridStructures()
    case.TreatmentPlans[destination_plan].BeamSets[destination_beamset].FractionDose.UpdateDoseGridStructures()
    case.TreatmentPlans[destination_plan].TreatmentCourse.TotalDose.UpdateDoseGridStructures()

    # go to plan evaluation
    ui.TitleBar.MenuItem['Plan Evaluation'].Button_Plan_Evaluation.Click()

    # Capture the current list of ROI's to avoid saving over them in the future
    targets = so.find_targets(case)
    for t in targets:
        patient.Set2DvisualizationForRoi(RoiName=t,
                                         Mode='filled')

    max_dose = find_max_dose_in_plan(examination=examination,
                                     case=case,
                                     plan=plan)

    try:
        ref_dose = beamset.Prescription.PrimaryDosePrescription.DoseValue
    except AttributeError:
        ref_dose = max_dose
        logging.info('Neither prescription nor max dose are defined in the plan. Setting to default max_dose')

    isodose_reconfig(case=case,
                     ref_dose=ref_dose,
                     max_dose=max_dose)
    # Turn visualization on for anything in the above list, and off for everything else
    for r in case.PatientModel.RegionsOfInterest:
        if r.Name in roi_list:
            patient.SetRoiVisibility(RoiName=r.Name,IsVisible=True)
        else:
            patient.SetRoiVisibility(RoiName=r.Name,IsVisible=False)
    # Delete extraneous plans
    # Save visibility settings presumably
    patient.Save()



if __name__ == '__main__':
    main()
