""" AI Contour and Export

    This script prompts the user to select an appropriate site, generates AI contours, exports these contours to MIM,
deletes existing contours, and saves the patient data.


    Prompt user for appropriate site.
    Generate AI contours
    Export contours to MIM
    Delete existing Contours
    Save patient

"""

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '18-Jul-2023'
__version__ = '0.0.0'
__status__ = 'Validation'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import PySimpleGUI as Sg
import re
from GeneralOperations import find_scope
import DicomExport

OAR_LIBRARY = {
    "RSL Head and Neck CT": [
        "Brain", "Brainstem", "Cochlea_L", "Cochlea_R", "Esophagus", "Eye_L",
        "Eye_R", "Glnd_Lacrimal_L", "Glnd_Lacrimal_R", "Glottis",
        "Larynx_SG", "Lens_L", "Lens_R", "Lips", "Lung_L", "Lung_R", "Bone_Mandible",
        "Nasolacrimal_Duct_L", "Nasolacrimal_Duct_R", "OpticChiasm", "OpticNrv_L",
        "OpticNrv_R", "Cavity_Oral", "Parotid_L", "Parotid_R", "Pituitary",
        "Fossa_Posterior", "SpinalCanal", "SpinalCord", "Glnd_Submand_L", "Glnd_Submand_R",
        "Joint_TM_L", "Joint_TM_R", "Glnd_Thyroid", "Tongue_Base", "Trachea",
    ],
    "RSL Male Pelvic CT": [
        "Prostate",
        "Anorectum",
        "Bladder",
        "Femur_Head_L",
        "Femur_Head_R"],
    "RSL Thorax-Abdomen CT": [
        "A_LAD", "Esophagus", "Heart_Inferior_Left_PA", "Heart",
        "Kidney_L", "Kidney_R", "Liver", "Lung_L", "Lung_R", "Pancreas",
        "SpinalCanal", "Spleen", "Sternum", "Stomach", "Glnd_Thyroid",
        "Trachea"],
    "RSL Breast CT": [
        "HumeralHead_L", "HumeralHead_R", "Breast_L", "Breast_R",
        "LN_Ax_L1_L", "LN_Ax_L1_R", "LN_Ax_L2_L", "LN_Ax_L2_R",
        "LN_Ax_L3_L", "LN_Ax_L3_R", "LN_Ax_L4_L", "LN_Ax_L4_R",
        "LN_Ax_Pectoral_L", "LN_Ax_Pectoral_R", "LN_IMN_L", "LN_IMN_R"
    ]}

# set theme for fun
Sg.theme('BrightColors')

Sg.theme('DarkBlue')


def create_dialog():
    """
       Creates a PySimpleGUI dialog to let the user select a template and the ROI prefix,
       and see the template contours.

       Returns:
           selected_template (str): Selected template name
           selected_contours (list): List of contours in the selected template
           roi_prefix (str): Selected ROI prefix
    """
    max_oars = 0
    max_name = 0
    machine_learning_prefix = "RS_"
    for k, v in OAR_LIBRARY.items():
        max_name = len(k) if len(k) > max_name else max_name
        max_oars = len(v) if len(v) > max_oars else max_oars

    layout = [
        [Sg.Frame('Select Template and ROI Prefix',
                  [[Sg.Text('RS ML Template:'),
                    Sg.Combo(list(OAR_LIBRARY.keys()),
                             key='-COMBO-',
                             enable_events=True,
                             size=(max_name, 1))],
                   [Sg.Text('ROI Prefix:'),
                    Sg.InputText(default_text=machine_learning_prefix,
                                 key='-ML_PREFIX-',
                                 size=(10, 1))]]
                  ),
         Sg.Frame('Template Contours:',
                  [[Sg.Text("Listed Contours", key='-OUT-',
                            enable_events=True)]],
                  key='-CONTOURS-',
                  visible=False
                  )],
        [Sg.Button('Submit', key='-SUBMIT-', disabled=True)]
    ]

    window = Sg.Window('Library Selector', layout, return_keyboard_events=True)

    selected_template = None
    selected_contours = None

    while True:
        event, values = window.read()

        if event == Sg.WINDOW_CLOSED:
            break

        if event == '-COMBO-':
            selected_template = values['-COMBO-']
            selected_contours = '\n'.join(OAR_LIBRARY[selected_template])
            window['-OUT-'].update(selected_contours)
            window['-CONTOURS-'].update(visible=True)
            window['-SUBMIT-'].update(disabled=False)

        if event == '-SUBMIT-':
            selected_template = values['-COMBO-']
            selected_contours = OAR_LIBRARY[selected_template]
            machine_learning_prefix = values['-ML_PREFIX-']
            break

    window.close()
    return selected_template, selected_contours, machine_learning_prefix


def rename_existing(case, prefix, add=True, contour_list=None):
    """
        Renames existing contours based on a given prefix.
        If 'add' is True, the prefix is added. If 'add' is False, the prefix is removed.

        Args:
            case: Patient case instance
            prefix (str): Prefix for ROI
            add (bool, optional): Flag to determine if the prefix is added or removed. Default is True.
            contour_list (list, optional): List of contours to rename. If None, all ROIs are considered.

        Returns:
            renamed (list): List of renamed contours
    """
    reo_prefix = re.compile("^" + prefix)
    renamed = []
    # Rename the MD-drawn contours
    if not contour_list:
        contour_list = [r.Name for r in case.PatientModel.RegionsOfInterest]
    for c in contour_list:
        r = case.PatientModel.RegionsOfInterest[c]
        if not re.match(reo_prefix, c):
            if add:
                r.Name = re.sub("^", prefix, c)
                renamed.append(r.Name)
        else:
            if not add:
                r.Name = re.sub(reo_prefix, "", c)
                renamed.append(r.Name)
    return renamed


# Record the time
def add_machine_learning_contours(case, machine_learning_prefix, model, rois_to_include, exam_name=None):
    """
        Adds ML contours to the specified case based on the provided model and ROIs.

        Args:
            case: Patient case instance
            machine_learning_prefix (str): Prefix for ML-generated ROIs
            model (str): Model name
            rois_to_include (list): List of ROIs to include in ML segmentation
            exam_name (str, optional): Examination name. If None, all exams are considered.

        Returns:
            renamed (list): List of renamed ML contours
    """
    if not exam_name:
        examinations = {e.Name: None for e in case.Examinations}
    else:
        examinations = {exam_name: None}
    for e_name, reg in examinations.items():
        case.Examinations[e_name].RunOarSegmentation(
            ModelName=model,
            ExaminationsAndRegistrations={e_name: reg},
            RoisToInclude=rois_to_include)
    renamed = rename_existing(case, machine_learning_prefix, add=True, contour_list=rois_to_include)
    return renamed


def delete_rois(case, regions_of_interest):
    """
        Deletes specified ROIs from the given case.

        Args:
            case: Patient case instance
            regions_of_interest (list): List of ROIs to delete
    """
    patient_rois = [r.Name for r in case.PatientModel.RegionsOfInterest]
    for r in regions_of_interest:
        if r in patient_rois:
            case.PatientModel.RegionsOfInterest[r].DeleteRoi()


def main():
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    template, oars, machine_learning_prefix = create_dialog()
    ml_contours = add_machine_learning_contours(case, machine_learning_prefix, template, oars, exam.Name)
    patient.Save()
    DicomExport.send(case=case,
                     destination='MIM',
                     exam=exam,
                     plan_dose=False,
                     beam_dose=False,
                     bar=True)
    delete_rois(case, ml_contours)
    patient.Save()


if __name__ == '__main__':
    main()
