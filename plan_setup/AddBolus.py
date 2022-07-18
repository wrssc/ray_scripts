""" Add Placeholder Bolus
    Adds a small sphere of air to the user origin for application to beams when custom
    bolus is used.

    Scope: Requires RayStation API

    Example Usage
    Prerequisites:

    Version History

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
__date__ = '2022-Jul-18'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10A SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__credits__ = ['']

import logging
import PySimpleGUI as sg
import sys
from collections import namedtuple
import GeneralOperations

BOLUS = {'--NAME--': 'Bolus_Custom',
         '--RADIUS--': 0.6204  # cm (1 cc)
         }


def bolus_gui(beamset):
    """
    Bolus user gui. prompts user for selection of which beams have custom bolus applied.
    returns a dictionary of beam name:  True(apply bolus)/False(no bolus)
    Args:
        beamset: RS beamset script object

    Returns:
        beam_selections: {BeamName: True/False}

    """
    dialog_name = 'Add Custom Bolus'
    bn = [b.Name for b in beamset.Beams]
    sg.ChangeLookAndFeel('DarkPurple4')
    frames = ['-BEAM CHOICES-']
    layout = [
        [sg.Text(dialog_name,
                 size=(20, 1),
                 justification='center',
                 font=("Helvetica", 16),
                 relief=sg.RELIEF_RIDGE), ],
        [sg.Frame(
            layout=[[sg.Checkbox(b,
                                 size=(30, 3),
                                 key=b,
                                 default=True,
                                 enable_events=True)] for b in bn],
            title='Apply Bolus to the following beams',
            relief=sg.RELIEF_SUNKEN,
            key=frames[0],
            tooltip='Select Beams that will have custom bolus')],
        [sg.Submit(tooltip='Click to submit this window'),
         sg.Cancel()],
    ]
    window = sg.Window(
        'DQA Setup',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            beam_selections = None
            break
        elif event == "Submit":
            beam_selections = values
            break
    window.close()
    if beam_selections == {}:
        sys.exit('QA Script was cancelled')
    else:
        return beam_selections


def find_material(db, name):
    # Find the material selected in list
    material_template = db.GetTemplateMaterial()

    for m in material_template.Materials:
        if m.Name == name:
            return m
    return None


def return_greater(dict1, dict2):
    ret = {k: max(dict1[k], dict2[k]) for k in dict1.keys() if k in dict2.keys()}
    return ret


def bolus_center(pd, radius):
    # Determine the center of the bolus structure for placement
    if len(pd.exam.Series) == 1:
        image_set_edge = pd.exam.Series[0].ImageStack.Corner
    else:
        logging.warning('Unknown number of series in this examination, Bolus placement failed')
        return None
    # Dose grid edge
    dose_grid_edge = pd.beamset.FractionDose.InDoseGrid.Corner
    image_in_grid = return_greater(image_set_edge, dose_grid_edge)
    if image_in_grid:
        return {'x': image_in_grid['x'] + radius,
                'y': image_in_grid['y'] + radius,
                'z': image_in_grid['z'] + radius}
    else:
        logging.debug('Error setting bolus center')
        return None


def make_bolus(pd):
    """
    makes the bolus roi and returns the raystation script object for region of interest
    Args:
        pd: Named Tuple containing ScriptObjects

    Returns:
        bolus_name: RS RegionOfInterest script object
    """
    pm = pd.case.PatientModel
    bolus_name = pm.GetUniqueRoiName(DesiredName=BOLUS['--NAME--'])
    pm.CreateRoi(Name=bolus_name,
                 Color='Pink',
                 Type='Bolus')
    bolus_roi = pm.RegionsOfInterest[bolus_name]
    bolus_roi.CreateSphereGeometry(Radius=BOLUS['--RADIUS--'],
                                   Examination=pd.exam,
                                   Center=bolus_center(pd, radius=BOLUS['--RADIUS--']),
                                   Representation='Voxels',
                                   VoxelSize=0.01)
    air = find_material(pd.db, name="Air")
    if air:
        bolus_roi.SetRoiMaterial(Material=air)
    else:
        logging.warning('While setting bolus roi, the Air template could not be found. Set material density manually')
    return bolus_roi


def place_bolus(pd, beam_list, bolus_roi):
    bolus_placed = []
    for b in pd.beamset.Beams:
        if b.Name in beam_list:
            try:
                b.SetBolus(BolusName=bolus_roi.Name)
                bolus_placed.append(True)
            except:
                bolus_placed.append(False)
    if all(bolus_placed):
        return True
    else:
        return False


def main():
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd = Pd(error=[],
            patient=GeneralOperations.find_scope(level='Patient'),
            case=GeneralOperations.find_scope(level='Case'),
            exam=GeneralOperations.find_scope(level='Examination'),
            db=GeneralOperations.find_scope(level='PatientDB'),
            plan=GeneralOperations.find_scope(level='Plan'),
            beamset=GeneralOperations.find_scope(level='BeamSet'))
    beam_selections = bolus_gui(beamset=pd.beamset)
    if not beam_selections:
        sys.exit('Dialog canceled no bolus made or applied')
    bolused_beams = [k for k, v in beam_selections.items() if v]
    logging.debug('Bolus to be applied to ' + ','.join([b for b in bolused_beams]))
    # Make the bolus
    bolus_roi = make_bolus(pd)
    # Apply it to the beamlist
    success = place_bolus(pd, beam_list=bolused_beams, bolus_roi=bolus_roi)
    if success:
        GeneralOperations.logcrit('Bolus applied to {}'.format(bolused_beams))
    else:
        GeneralOperations.logcrit('Bolus could not be applied via script')


if __name__ == '__main__':
    main()
