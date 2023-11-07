""" Implanted Medical Device Metrics

"""

__author__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__date__ = "2023-06-19"
__version__ = "0.1.0"
__status__ = "Developmemt"
__deprecated__ = False
__reviewer__ = ""
__reviewed__ = ""
__raystation__ = "11B"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2023, University of Wisconsin Board of Regents"

from connect import get_current
import PySimpleGUI as sg
import sys
from pathlib import Path

ditto_path = Path(__file__).parent.parent / "library"
sys.path.insert(1, str(ditto_path))
import ImplantedDeviceOperations as ido


def main():
    case = get_current("Case")
    plan = get_current("Plan")
    beam_set = get_current("BeamSet")
    examination = get_current("Examination")

    list_of_ROIs = [roi.Name for roi in case.PatientModel.RegionsOfInterest]
    if "Pacemaker" in list_of_ROIs:
        default_value = "Pacemaker"
    else:
        default_value = None

    list_of_plans = [p.Name for p in case.TreatmentPlans]
    default_plan = plan.Name

    layout = [
        [
            sg.Text("Select Plan:"),
            sg.Combo(
                values=list_of_plans, default_value=default_plan, key="-SELECTED PLAN-"
            ),
        ],
        [
            sg.Text("Select Implanted Device ROI:"),
            sg.Combo(
                values=list_of_ROIs, default_value=default_value, key="-SELECTED ROI-"
            ),
        ],
        [
            sg.Text("Maximum Dose (D0.03cc):"),
            sg.Text("Default Text", size=(20, 1), key="-MAX DOSE TEXT-"),
        ],
        [
            sg.Text("Distance from Device to Nearest Collimated Field Edge:"),
            sg.Text("Default Text", size=(20, 1), key="-MIN DIST TEXT-"),
        ],
        [
            sg.Text("Neutron-generating Beams?:"),
            sg.Text("Default Text", size=(20, 1), key="-NEUTRONS TEXT-"),
        ],
        [
            sg.Button("Calculate"),
            sg.Cancel(),
        ],
    ]

    window = sg.Window(
        "Implanted Medical Device Metrics",
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False,
    )

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Calculate":
            roi_name = values["-SELECTED ROI-"]
            max_dose = ido.get_device_D0_03cc(
                case=case, beam_set=beam_set, examination=examination, roi_name=roi_name
            )
            window["-MAX DOSE TEXT-"].update(f"{max_dose:.3f} Gy")
            min_dist = ido.get_device_dist_to_field_edge(
                case=case, beam_set=beam_set, examination=examination, roi_name=roi_name
            )
            window["-MIN DIST TEXT-"].update(f"{min_dist:.3f} cm")
            quality_df = ido.get_beamset_beam_quality(beam_set)
            if quality_df["Beam Has Neutrons"].any():
                window["-NEUTRONS TEXT-"].update("Yes")
            else:
                window["-NEUTRONS TEXT-"].update("No")

    window.close()


if __name__ == "__main__":
    main()
