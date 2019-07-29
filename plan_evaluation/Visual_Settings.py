""" Load isodose and target visualization
    Loads some simple visual settings for targets and isodoses since this is not a sticky
    property of the RayStation (RS) software

    Version:
    1.0 Load targets as filled. Normalize isodose to prescription, and try to normalize to the
        maximum dose in External or External_Clean

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '29-Jul-2019'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8b.SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import connect
import logging
import sys
import platform
import clr

clr.AddReference('System.Drawing')
import System.Drawing


def find_targets(case):
    """
    Find all structures with type 'Target' within the current case. Return the matches as a list
    :param case: Current RS Case
    :return: plan_targets # A List of targets
    """
    # Find RS targets
    plan_targets = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.OrganData.OrganType == 'Target':
            plan_targets.append(r.Name)
    # Add user threat: empty PTV list.
    if not plan_targets:
        connect.await_user_input("The target list is empty." +
                                 " Please apply type PTV to the targets and continue.")
        for r in case.PatientModel.RegionsOfInterest:
            if r.OrganData.OrganType == 'Target':
                plan_targets.append(r.Name)
    if plan_targets:
        return plan_targets
    else:
        sys.exit('Script cancelled')


def check_structure_exists(case, structure_name, roi_list=None, option='Check'):
    """
    Verify if a structure with the exact name specified exists or not
    :param case: Current RS case
    :param structure_name: the name of the structure to be confirmed
    :param roi_list: complete list of all available ROI's.
    :param option: desired behavior
        Delete - deletes structure if found
        Check - simply returns true or false if found
    :return: Logical - True if structure is present in ROI List, false otherwise
    """
    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for r in case.PatientModel.RegionsOfInterest:
            roi_list.append(r.Name)

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if option == 'Delete':
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            logging.warning(structure_name + 'found - deleting and creating')
        elif option == 'Check':
            logging.info(structure_name + 'found')
        return True
    elif option == 'Wait':
        connect.await_user_input(
            'Create the structure {} and continue script.'.format(structure_name))
    else:
        logging.info(structure_name + 'not found')
        return False


def isodose_reconfig(case, ref_dose, max_dose=None, levels=None):
    """
    This function takes the current case, an optional max_dose
    :param case: ScriptObject of RS case
    :param ref_dose: The normalization dose in Gy
    :param max_dose: an optional argument that can specify the maximum dose within the plan
    :param levels: a dictionary of relative isodose levels and colors levels[10]=[A, R, G, B]
    :return:
    """
    # dose_color_table =  case.CaseSettings.DoseColorMap.ColorTable
    # Clear current contents
    if max_dose:
        max_ratio = max_dose / ref_dose
        max_isodose = int(100 * 0.99 * max_ratio)
    else:
        logging.info('No max dose found. Using 115%')
        max_isodose = int(115)

    dose_levels = {}
    if levels is None:
        dose_levels = {10: System.Drawing.Color.FromArgb(255, 127, 0, 255),
                       20: System.Drawing.Color.FromArgb(255, 0, 0, 255),
                       30: System.Drawing.Color.FromArgb(255, 0, 127, 255),
                       40: System.Drawing.Color.FromArgb(255, 0, 255, 255),
                       50: System.Drawing.Color.FromArgb(255, 0, 255, 127),
                       60: System.Drawing.Color.FromArgb(255, 0, 255, 0),
                       70: System.Drawing.Color.FromArgb(255, 127, 255, 0),
                       80: System.Drawing.Color.FromArgb(255, 255, 255, 0),
                       90: System.Drawing.Color.FromArgb(255, 255, 127, 0),
                       95: System.Drawing.Color.FromArgb(255, 255, 0, 0),
                       100: System.Drawing.Color.FromArgb(255, 255, 0, 255),
                       105: System.Drawing.Color.FromArgb(255, 255, 0, 127),
                       max_isodose: System.Drawing.Color.FromArgb(255, 128, 20, 20)}
    else:
        for k, v in levels.iteritems():
            dose_levels[k] = System.Drawing.Color.FromArgb(
                levels[k][0], levels[k][1], levels[k][2], levels[k][3])

    dose_color_table = {}
    for k, v in dose_levels.iteritems():
        dose_color_table[k] = v

    case.CaseSettings.DoseColorMap.ColorTable = dose_color_table
    case.CaseSettings.DoseColorMap.ReferenceValue = ref_dose
    case.CaseSettings.DoseColorMap.PresentationType = 'Absolute'


def find_max_dose_in_plan(examination, case, plan):
    rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries
    if check_structure_exists(case=case,
                              structure_name='External_Clean',
                              roi_list=rois,
                              option='Check'):
        max_dose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName='External_Clean', DoseType='Max')
    elif check_structure_exists(case=case,
                                structure_name='External',
                                roi_list=rois,
                                option='Check'):
        max_dose = plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName='External', DoseType='Max')
    else:
        max_dose = None

    return max_dose


def main():

    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        examination = connect.get_current("Examination")
        patient_db = connect.get_current('PatientDB')
        plan = connect.get_current('Plan')
        beamset = connect.get_current('BeamSet')
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        UserInterface.WarningBox(message)
        UserInterface.WarningBox('This script requires a patient, case, and beamset to be loaded')
        sys.exit('This script requires a patient, case, and beamset to be loaded')

    # Capture the current list of ROI's to avoid saving over them in the future
    targets = find_targets(case)
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


if __name__ == '__main__':
    main()
