""" PRDR Calculation Sheet
    Load a table that shows the PRDR calculation for the present beamset.
    The table consists of a row for each beam with:
    * the monitor units (MU),
    * Dose to the Isocenter for each fraction
    * Maximum dose to the prescription target per fraction
        (evaluation volume specified in the volume_units dictionary)
    * Mean dose to the prescription target per fraction

    Selecting the Toggle button switches to the Plan Dose (used in our segmentation worksheet)
    Copy to Clipboard loads the table into an excel-friendly formatted clip

    Validation:
    PRDR Beamtables have been populated manually by Dosimetry since RayStation
    was commissioned. 5 were opened, and this table was generated
    for them using the 1% maximum dose convention we adopted for evaluating the
    13.3 cGy/Min maximum dose to target limit set by Ma.
    This data was compared to the clinically used PRDR calcsheet. No deviations were
    found.

    Version:
    0.0.0 Validation with Dmax evaluated at 1%
    0.0.1 Switch to Dmax evaluated at 0.03 cc to prescribing target
          When this process was done manually, evaluating each beam's contribution
          to the maximum dose to 0.03 cc volume of the target was prohibitively time
          consuming. Now that the script is written, we will switch to the more
          conventional max dose evaluation at 0.03 cc.
    0.0.2 Force the loading of the dataframe in the same order as the beams
    1.0.0 Clinical Release

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
__date__ = '26-Jan-2023'
__version__ = '1.0.0'
__status__ = 'Clinical'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import sys
import PySimpleGUI as sg
import pandas as pd
from collections import namedtuple

import connect
import UserInterface
import StructureOperations as so
import GeneralOperations


def get_iso_coords(beamset, beam_name):
    # For the supplied beamset and for the beam_name supplied:
    # Get coordinates of current isocenter and return as a tuple
    for b in beamset.Beams:
        if b.Name == beam_name:
            position = b.Isocenter.Position
            break
    return (position['x'], position['y'], position['z'])


def match_beam_fracdose(beamset, beam_name):
    # Return the index of the fractional dose object matching beam_name
    index = 0
    found_index = None
    for d in beamset.FractionDose.BeamDoses:
        if d.ForBeam.Name == beam_name:
            found_index = index
        else:
            index += 1
    return found_index


def get_dose_at_isocenter(beamset, beam_name):
    # For the supplied beamset and beam_name compute the dose at the isocenter
    iso_coords = get_iso_coords(beamset, beam_name)
    index = match_beam_fracdose(beamset, beam_name)
    dose = beamset.FractionDose.BeamDoses[index] \
        .InterpolateDoseInPoint(Point={'x': iso_coords[0],
                                       'y': iso_coords[1],
                                       'z': iso_coords[2]},
                                PointFrameOfReference=beamset.FrameOfReference)
    return dose


def get_relative_volume(rs_obj, roi_name, vol_evaluation_absolute):
    """
     Get the relative value of an roi (0 vol to 100%) from the
     absolute volume of a structure. Return the relative volume
     patient_data: A namedtuple containing the raystation script objects defined in main
             of note:
                       patient_data.case is the current case
                       patient_data.exam is the current exam
                       patient_data.beamset is the current beamset
     roi_name: Name of roi of interest
     vol_evaluation_absolute: absolute volume of interest in cc
     Returns the relative volume of the roi_name structure between 0 and 1.0
    """
    vol_roi = rs_obj.case.PatientModel \
        .StructureSets[rs_obj.exam.Name] \
        .RoiGeometries[roi_name].GetRoiVolume()
    return vol_evaluation_absolute / vol_roi


def get_maximum_dose_roi_at_volume(rs_obj, beam_name, roi_name, volume_units):
    """
     Get the fractional dose value of an roi (0 vol to 100%) from the
     absolute volume of a structure. Return the relative volume
     patient_data: A namedtuple containing the raystation script objects defined in main
             of note:
                       patient_data.case is the current case
                       patient_data.exam is the current exam
                       patient_data.beamset is the current beamset
     beam_dose: name of beam of interest
     roi_name: Name of roi of interest
     volume_units: DICT: {"UNITS": '%' or 'cc', "VOL": <Volume relative or abs>}
     Returns the fractional dose in cGy for the roi for the beam named in beam_name
    """
    #
    # Find the fractional dose for the input beam_name
    index = match_beam_fracdose(rs_obj.beamset, beam_name)
    #
    # Determine the evaluation volume
    if volume_units["UNITS"] == "%":
        vol_eval_rel = volume_units["VOLUME"]
    else:
        vol_eval_rel = get_relative_volume(rs_obj, roi_name, volume_units["VOLUME"])
    # Retrieve the dose
    dose = rs_obj.beamset.FractionDose.BeamDoses[index].GetDoseAtRelativeVolumes(
        RoiName=roi_name,
        RelativeVolumes=[vol_eval_rel])[0]
    return dose


def sorted_beamset_dict(rs_obj):
    beam_dict = {}
    n_beams = 0
    for b in rs_obj.beamset.Beams:
        beam_dict[b.Name] = b.Number
        n_beams += 1
    beam_dict = dict(sorted(beam_dict.items(), key=lambda item: item[1]))
    return beam_dict


def get_dose_dataframes(rs_obj, volume_units, beam_dict):
    """
     For the beamset: For each beam in the beamset get the MU, Max, Mean, and iso doses
     patient_data: A namedtuple containing the raystation script objects defined in main
             of note:
                       patient_data.case is the current case
                       patient_data.exam is the current exam
                       patient_data.beamset is the current beamset
     volume_units: DICT: {"UNITS": '%' or 'cc', "VOL": <Volume relative or abs>}
     beam_dict: LIST: [{'BEAM_NAME': Raystation Beam Number}]
                A list sorted by the desired order of the pandas dataframe, e.g. beam number

     Return: a pandas dataframe of these values
    """
    Rx_Roi = rs_obj.beamset.Prescription.PrimaryPrescriptionDoseReference.OnStructure.Name
    nfx = rs_obj.beamset.FractionationPattern.NumberOfFractions
    fraction_data = []
    plan_data = []
    beam_number = []
    for b_name, b_number in beam_dict.items():
        for dose in rs_obj.beamset.FractionDose.BeamDoses:
            beam_dose_so = None
            if dose.ForBeam.Name == b_name:
                beam_dose_so = dose
                break
        fx_dose_to_isocenter = get_dose_at_isocenter(rs_obj.beamset, b_name)
        fx_mean_dose = beam_dose_so.GetDoseStatistic(RoiName=Rx_Roi, DoseType="Average")
        fx_max_dose = get_maximum_dose_roi_at_volume(rs_obj,
                                                     beam_name=b_name, roi_name=Rx_Roi,
                                                     volume_units=volume_units)
        beam_mu = beam_dose_so.ForBeam.BeamMU
        beam_number.append(b_number)
        fraction_data.append(
            {'Beam_Name': b_name,
             'MU': round(beam_mu, 2),
             'Beam Dose to Iso (cGy)': round(fx_dose_to_isocenter, 2),
             'Beam Max Dose to PTV (cGy)': round(fx_max_dose, 2),
             'Beam Dmean to PTV (cGy)': round(fx_mean_dose, 2)})
        plan_data.append(
            {'Beam_Name': b_name,
             'MU': round(beam_mu, 2),
             'Plan Dose to Iso (Gy)': round(fx_dose_to_isocenter * nfx / 100., 3),
             'Plan Max Dose to PTV (Gy)': round(fx_max_dose * nfx / 100., 3),
             'Plan Dmean to PTV (Gy)': round(fx_mean_dose * nfx / 100., 3)})
    fraction_df = pd.DataFrame(fraction_data,index=beam_number)
    fraction_df.index.names = ['Beam Number']

    plan_df = pd.DataFrame(plan_data,index=beam_number)
    plan_df.index.names = ['Beam Number']
    return fraction_df, plan_df


def update_table_title(table, old_headings, headings):
    # Update the table widget
    for cid, text in zip(old_headings, headings):
        table.heading(cid, text=text)


def pd_to_header_table(df):
    # Convert the first row and values of the dataframe to a list
    header = df.columns.to_list()
    table = df.values.tolist()
    return (header, table)


def display_beam_worksheet(df_plan, df_fraction):
    """
    Build the Sg table for the user
    df_plan: data frame containing the beamset level PRDR calculation data
    df_fraction: data frame containing the fraction dose PRDR calculation data
    """
    sg.theme('Dark')
    (headings_fraction, table_fraction) = pd_to_header_table(df_fraction)
    (headings_plan, table_plan) = pd_to_header_table(df_plan)

    per_fraction = True  # Beam Data display
    # ------ Window Layout ------
    layout = [[sg.Table(values=table_fraction[:][:], headings=headings_fraction, max_col_width=25,
                        # background_color='light blue',
                        auto_size_columns=True,
                        display_row_numbers=False,
                        justification='center',
                        num_rows=20,
                        alternating_row_color='brown',
                        key='-TABLE-',
                        row_height=35,
                        tooltip='PRDR Beam Doses')],
              [sg.Button('Toggle Plan Data', button_color=(('white', ('red', 'green')[per_fraction])), key='-TOGGLE-')],
              [sg.Button('Copy to Clipboard', key='-COPY-')],
              [sg.Text('Toggle Plan/Fraction Data = Toggle Between Plan and Fractional Data : (MU Sheet uses Plan)')]]

    # ------ Create Window ------
    # Add the version of the script to the header window
    # This will be matched with the excel spreadsheet version
    window = sg.Window("".join(('PRDR Dose Data (Version: ', __version__, ')')),
                       layout, font='Garamond 12')

    # ------ Event Loop ------
    while True:
        event, values = window.read()
        print(event, values)
        if event == sg.WIN_CLOSED:
            break
        if event == '-TOGGLE-':
            table = window['-TABLE-'].Widget
            if per_fraction:
                update_table_title(table, old_headings=headings_fraction, headings=headings_plan)
                window['-TABLE-'].update(values=table_plan[:][:])
                window['-TABLE-'].update(alternating_row_color='green')
            else:
                update_table_title(table, old_headings=headings_fraction, headings=headings_fraction)
                window['-TABLE-'].update(values=table_fraction[:][:])
                window['-TABLE-'].update(alternating_row_color='brown')
            per_fraction = not per_fraction
            window.Element('-TOGGLE-').Update(('Fraction Data', 'Plan Data')[per_fraction],
                                              button_color=(('white', ('brown', 'green')[per_fraction])))
        if event == '-COPY-':
            if per_fraction:
                print(df_fraction)
                df_fraction.to_clipboard(excel=True, index=False, header=None)
            else:
                print(df_plan)
                df_plan.to_clipboard(excel=True, index=False, header=None)
        elif event == 'Change Colors':
            window['-TABLE-'].update(row_colors=((8, 'white', 'red'), (9, 'green')))

    window.close()


def main():
    # Initialize return variable
    PatientData = namedtuple('RS_OBJ', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    rs_obj = PatientData(error=[],
                         patient=GeneralOperations.find_scope(level='Patient'),
                         case=GeneralOperations.find_scope(level='Case'),
                         exam=GeneralOperations.find_scope(level='Examination'),
                         db=GeneralOperations.find_scope(level='PatientDB'),
                         plan=GeneralOperations.find_scope(level='Plan'),
                         beamset=GeneralOperations.find_scope(level='BeamSet'))
    # Determine how max doses should be reported
    volume_units = {
        'UNITS': 'cc',
        'VOLUME': 0.03
    }
    # Get an ordered dictionary of each beam in the beamset of the form:
    # {'BEAM_NAME': Raystation Beam Number}
    beam_order_dictionary = sorted_beamset_dict(rs_obj)
    # Compute the plan and fraction dose (mean, max, and dose to isocenter)
    df_fraction, df_plan = get_dose_dataframes(rs_obj, volume_units,beam_order_dictionary)
    # Display the results
    display_beam_worksheet(df_plan, df_fraction)


if __name__ == '__main__':
    main()
