""" Automatic OTV Maker

"""

__author__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__date__ = "2024-08-20"
__version__ = "0.1.0"
__status__ = "Development"
__deprecated__ = False
__reviewer__ = ""
__reviewed__ = ""
__raystation__ = "11B"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2024, University of Wisconsin Board of Regents"

from connect import get_current
import PySimpleGUI as sg
import sys
from pathlib import Path
import re
import numpy as np

ditto_path = Path(__file__).parent.parent / "library"
sys.path.insert(1, str(ditto_path))

def make_too_hot_structure(
    case,
    examination,
    dose_name,
    PTV_name,
    expansion
):

    hot_roi = case.PatientModel.CreateRoi(Name=f"Hot_{expansion}", Color="Orange", Type="Organ")

    ExpressionA = {
        "Operation": "Union",
        "SourceRoiNames": [dose_name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ExpressionB = {
        "Operation": "Union",
        "SourceRoiNames": [PTV_name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': expansion,
            'Inferior': expansion,
            'Anterior': expansion,
            'Posterior': expansion,
            'Right': expansion,
            'Left': expansion,
        }
    }

    ResultMarginSettings = {
        'Type': "Expand",
        'Superior': 2*expansion,
        'Inferior': 2*expansion,
        'Anterior': 2*expansion,
        'Posterior': 2*expansion,
        'Right': 2*expansion,
        'Left': 2*expansion,
    }

    hot_roi.CreateAlgebraGeometry(
        Examination=examination,
        Algorithm="Auto",
        ExpressionA=ExpressionA,
        ExpressionB=ExpressionB,
        ResultOperation="Subtraction",
        ResultMarginSettings=ResultMarginSettings,
    )

    return hot_roi

def make_too_cold_structure(
    case,
    examination,
    dose_name,
    PTV_name,
    expansion
):

    cold_roi = case.PatientModel.CreateRoi(Name=f"Cold_{expansion}", Color="Blue", Type="Organ")

    ExpressionA = {
        "Operation": "Union",
        "SourceRoiNames": [PTV_name],
        "MarginSettings": {
            'Type': "Contract",
            'Superior': expansion,
            'Inferior': expansion,
            'Anterior': expansion,
            'Posterior': expansion,
            'Right': expansion,
            'Left': expansion,
        }
    }

    ExpressionB = {
        "Operation": "Union",
        "SourceRoiNames": [dose_name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ResultMarginSettings = {
        'Type': "Expand",
        'Superior': 2*expansion,
        'Inferior': 2*expansion,
        'Anterior': 2*expansion,
        'Posterior': 2*expansion,
        'Right': 2*expansion,
        'Left': 2*expansion,
    }

    cold_roi.CreateAlgebraGeometry(
        Examination=examination,
        Algorithm="Auto",
        ExpressionA=ExpressionA,
        ExpressionB=ExpressionB,
        ResultOperation="Subtraction",
        ResultMarginSettings=ResultMarginSettings,
    )

    return cold_roi

def create_optimized_otv(
        ptv_name,
        hot_roi,
        cold_roi,
        otv_name):

    case = get_current("Case")
    examination = get_current("Examination")

    otv_auto = case.PatientModel.CreateRoi(Name=otv_name, Color="Green", Type="Ptv")

    ExpressionA = {
        "Operation": "Union",
        "SourceRoiNames": [cold_roi.Name, ptv_name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ExpressionB = {
        "Operation": "Union",
        "SourceRoiNames": [hot_roi.Name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ResultMarginSettings = {
        'Type': "Expand",
        'Superior': 0,
        'Inferior': 0,
        'Anterior': 0,
        'Posterior': 0,
        'Right': 0,
        'Left': 0,
    }

    otv_auto.CreateAlgebraGeometry(
        Examination=examination,
        Algorithm="Auto",
        ExpressionA=ExpressionA,
        ExpressionB=ExpressionB,
        ResultOperation="Subtraction",
        ResultMarginSettings=ResultMarginSettings,
    )

def union_of_rois(name_of_roi, list_of_rois, color_of_roi="Green"):
    case = get_current("Case")
    examination = get_current("Examination")

    union_roi = case.PatientModel.CreateRoi(Name=name_of_roi, Color=color_of_roi, Type="Organ")

    ExpressionA = {
        "Operation": "Union",
        "SourceRoiNames": [roi.Name for roi in list_of_rois],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ExpressionB = {
        "Operation": "Union",
        "SourceRoiNames": [],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ResultMarginSettings = {
        'Type': "Expand",
        'Superior': 0,
        'Inferior': 0,
        'Anterior': 0,
        'Posterior': 0,
        'Right': 0,
        'Left': 0,
    }

    union_roi.CreateAlgebraGeometry(
        Examination=examination,
        Algorithm="Auto",
        ExpressionA=ExpressionA,
        ExpressionB=ExpressionB,
        ResultOperation="None",
        ResultMarginSettings=ResultMarginSettings,
    )

    return union_roi

def create_otv(ptv_name, dose_name):

    case = get_current("Case")
    examination = get_current("Examination")

    if "PTV" in ptv_name:
        otv_name = ptv_name.replace("PTV", "OTV", 1) + "_AUTO"
    else:
        otv_name = "OTV_AUTO"

    expansions = (np.arange(40)+1)/100
    # expansions = (np.arange(15)+1)/100


    for expansion in expansions:
        try:
            hot_roi = case.PatientModel.RegionsOfInterest[f"Hot_{expansion}"]
            hot_roi.DeleteRoi()
        except:
            pass

        try:
            cold_roi = case.PatientModel.RegionsOfInterest[f"Cold_{expansion}"]
            cold_roi.DeleteRoi()
        except:
            pass

    try:
        hot_roi = case.PatientModel.RegionsOfInterest["_Hot"]
        hot_roi.DeleteRoi()
    except:
        pass

    try:
        cold_roi = case.PatientModel.RegionsOfInterest["_Cold"]
        cold_roi.DeleteRoi()
    except:
        pass

    try:
        new_otv = case.PatientModel.RegionsOfInterest[otv_name]
        new_otv.DeleteRoi()
    except:
        pass

    list_of_too_hot_rois = []
    list_of_too_cold_rois = []
    for expansion in expansions:
        list_of_too_hot_rois.append(
            make_too_hot_structure(
                    case,
                    examination,
                    dose_name,
                    ptv_name,
                    expansion,
            )
        )

        list_of_too_cold_rois.append(
            make_too_cold_structure(
                    case,
                    examination,
                    dose_name,
                    ptv_name,
                    expansion,
            )
        )

    list_of_non_empty_hot_rois = []
    for roi in list_of_too_hot_rois:
        if case.PatientModel.StructureSets[examination.Name].RoiGeometries[roi.Name].HasContours():
            list_of_non_empty_hot_rois.append(roi)
        else:
            roi.DeleteRoi()

    list_of_non_empty_cold_rois = []
    for roi in list_of_too_cold_rois:
        if case.PatientModel.StructureSets[examination.Name].RoiGeometries[roi.Name].HasContours():
            list_of_non_empty_cold_rois.append(roi)
        else:
            roi.DeleteRoi()

    hot_roi = union_of_rois("_Hot", list_of_non_empty_hot_rois, color_of_roi="Orange")
    cold_roi = union_of_rois("_Cold", list_of_non_empty_cold_rois, color_of_roi="Blue")

    for roi in list_of_non_empty_hot_rois:
        roi.DeleteRoi()
    for roi in list_of_non_empty_cold_rois:
        roi.DeleteRoi()

    create_optimized_otv(ptv_name, hot_roi, cold_roi, otv_name)

    hot_roi.DeleteRoi()
    cold_roi.DeleteRoi()

def main():
    case = get_current("Case")

    list_of_ROIs = [roi.Name for roi in case.PatientModel.RegionsOfInterest]
    if "PTV1" in list_of_ROIs:
        default_ptv = "PTV1"
    else:
        default_ptv = None

    if "Dose 24[Gy]" in list_of_ROIs:
        default_dose = "Dose 24[Gy]"
    elif "Dose 22[Gy]" in list_of_ROIs:
        default_dose = "Dose 22[Gy]"
    elif "Dose 21[Gy]" in list_of_ROIs:
        default_dose = "Dose 21[Gy]"
    elif "Dose 20[Gy]" in list_of_ROIs:
        default_dose = "Dose 20[Gy]"
    elif "Dose 19[Gy]" in list_of_ROIs:
        default_dose = "Dose 19[Gy]"
    elif "Dose 18[Gy]" in list_of_ROIs:
        default_dose = "Dose 18[Gy]"
    elif "Dose 17[Gy]" in list_of_ROIs:
        default_dose = "Dose 17[Gy]"
    elif "Dose 16[Gy]" in list_of_ROIs:
        default_dose = "Dose 16[Gy]"
    elif "Dose 15[Gy]" in list_of_ROIs:
        default_dose = "Dose 15[Gy]"
    elif "Dose 14[Gy]" in list_of_ROIs:
        default_dose = "Dose 14[Gy]"
    elif "Dose 12.5[Gy]" in list_of_ROIs:
        default_dose = "Dose 12.5[Gy]"

    else:
        default_dose = None

    layout = [
        [
            sg.Text("Select PTV:"),
            sg.Combo(
                values=list_of_ROIs, default_value=default_ptv, key="-SELECTED PTV-"
            ),
        ],
        [
            sg.Text("Select Dose Cloud:"),
            sg.Combo(
                values=list_of_ROIs, default_value=default_dose, key="-SELECTED DOSE-"
            ),
        ],
        [
            sg.Button("Create OTV"),
            sg.Cancel(),
        ],
    ]

    window = sg.Window(
        "Automatic OTV Maker",
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False,
    )

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Create OTV":
            ptv_name = values["-SELECTED PTV-"]
            dose_name = values["-SELECTED DOSE-"]
            create_otv(ptv_name, dose_name)

    window.close()


if __name__ == "__main__":
    main()
