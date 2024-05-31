""" Load a Standard Electon Cutout

    Versions:
    0.0.0 Test version

    Known issues:

     This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by the
    Free Software Foundation, either version 3 of the License, or (at your
    option) any later version.

    This program is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
    or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License along
    with this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = "Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__date__ = "2024-05-28"

__version__ = "0.0.0"
__status__ = "Testing"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"

__reviewed__ = ""
__raystation__ = "11"
__maintainer__ = "Adam Bayliss"

__email__ = "rabayliss@wisc.edu"
__license__ = "GPLv3"
__help__ = ""
__copyright__ = "Copyright (C) 2024, University of Wisconsin Board of Regents"

import math
import PySimpleGUI as Sg
from collections import namedtuple
from library.GeneralOperations import find_scope
import sys

def generate_circle_points(num_points, diameter, scaling_factor=1.0):
    """
    Generate points along a circle.

    Args:
        num_points (int): Number of unique points along the circle.
        diameter (float): Diameter of the circle.
        scaling_factor (float): factor to scale cut-out size. Block is defined
                                in RayStation at 100 cm from source.

    Returns:
        list: A list of dictionaries with 'x' and 'y' coordinates of the points.
    """
    radius = scaling_factor * diameter / 2
    angle_increment = 2 * math.pi / num_points

    points = []
    for i in range(num_points):
        angle = i * angle_increment
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append({'x': x, 'y': y})

    # Append the first point again to close the circle
    if points:
        points.append(points[0])

    return points


def generate_ellipse_points(num_points, largest_diameter, perpendicular_diameter, scaling_factor=0.95):
    """
    Generate points along an ellipse.

    Args:
        num_points (int): Number of unique points along the ellipse.
        largest_diameter (float): Largest diameter of the ellipse.
        perpendicular_diameter (float): Perpendicular diameter of the ellipse.
        scaling_factor (float): Factor to scale cut-out size. Block is defined
                                in RayStation at 100 cm from source.

    Returns:
        list: A list of dictionaries with 'x' and 'y' coordinates of the points.
    """
    largest_radius = scaling_factor * largest_diameter / 2
    perpendicular_radius = scaling_factor * perpendicular_diameter / 2
    angle_increment = 2 * math.pi / num_points

    points = []
    for i in range(num_points):
        angle = i * angle_increment
        x = largest_radius * math.cos(angle)
        y = perpendicular_radius * math.sin(angle)
        points.append({'x': x, 'y': y})

    # Append the first point again to close the ellipse
    if points:
        points.append(points[0])

    return points


def generate_cutout_points(key, num_points, scaling_factor=1.0):
    """
    Generate points for the specified cutout shape based on the key.

    Args:
        key (str): The key identifying the cutout in the dictionary.
        num_points (int): Number of unique points to generate.
        scaling_factor (float): Factor to scale cut-out size.

    Returns:
        list: A list of dictionaries with 'x' and 'y' coordinates of the points.
    """
    cutout = standard_cutouts.get(key)
    if not cutout:
        raise ValueError("Invalid key provided")

    shape = cutout['Shape']
    largest_diameter = cutout['Largest_Diameter']
    perpendicular_diameter = cutout['Perpendicular_Diameter']

    if shape == 'Circle':
        return generate_circle_points(num_points, largest_diameter, scaling_factor)
    elif shape == 'Ellipse':
        return generate_ellipse_points(num_points, largest_diameter, perpendicular_diameter, scaling_factor)
    else:
        raise ValueError("Unsupported shape type")


def check_beam(beam):
    try:
        applicator_name = beam.Applicator.ElectronApplicatorName
    except AttributeError:
        return False
    if applicator_name == 'A06':
        return True
    else:
        return False


standard_cutouts = {
    '2 cm Circle': {'Name': 'xxx0', 'Largest_Diameter': 2, 'Perpendicular_Diameter': None, 'Shape': 'Circle'},
    '2.5 cm Circle': {'Name': 'xxx1', 'Largest_Diameter': 2.5, 'Perpendicular_Diameter': None, 'Shape': 'Circle'},
    '3 cm Circle': {'Name': 'xxx2', 'Largest_Diameter': 3, 'Perpendicular_Diameter': None, 'Shape': 'Circle'},
    '3.5 cm Circle': {'Name': 'xxx3', 'Largest_Diameter': 3.5, 'Perpendicular_Diameter': None, 'Shape': 'Circle'},
    '4 cm Circle': {'Name': 'xxx4', 'Largest_Diameter': 4, 'Perpendicular_Diameter': None, 'Shape': 'Circle'},
    '5 cm Circle': {'Name': 'xxx5', 'Largest_Diameter': 5, 'Perpendicular_Diameter': None, 'Shape': 'Circle'},
    '2 x 3 cm Oval': {'Name': 'xxx6', 'Largest_Diameter': 3, 'Perpendicular_Diameter': 2, 'Shape': 'Ellipse'},
    '3 x 4 cm Oval': {'Name': 'xxx6', 'Largest_Diameter': 4, 'Perpendicular_Diameter': 3, 'Shape': 'Ellipse'},
}


def main():
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    rso = Pd(error=[],
            patient=find_scope(level='Patient'),
            case=find_scope(level='Case'),
            exam=find_scope(level='Examination'),
            db=find_scope(level='PatientDB'),
            plan=find_scope(level='Plan'),
            beamset=find_scope(level='BeamSet'))
    if not rso.beamset:
        sys.exit('A Beamset must be loaded to proceed')
    #
    beam_dict = {b.Name: b for b in rso.beamset.Beams}

    layout = [
        [Sg.Text('Select a Standard Electron Cutout')],
        [Sg.Combo(values=list(beam_dict.keys()), size=(30, 10), key='-BEAM_NAME-')],
        [Sg.Combo(values=list(standard_cutouts.keys()), size=(30, 10), key='-CUTOUT-')],
        [Sg.Button('Generate'), Sg.Button('Cancel')]
    ]

    window = Sg.Window('Standard Electron Cutout Generator', layout)

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED or event == 'Cancel':
            break
        if event == 'Generate':
            selected_cutout = values['-CUTOUT-']
            selected_beam = beam_dict[values['-BEAM_NAME-']]
            beam_ok = check_beam(selected_beam)
            if not beam_ok:
                Sg.popup(f'Standard cutout cannot be applied to {selected_beam.Name} due to wrong applicator size')
                break
            if selected_cutout:
                points = generate_cutout_points(selected_cutout, 100)
                selected_beam.Blocks[0].Contour = points
                Sg.popup(f"Generated points for {selected_cutout} on beam {selected_beam.Name}")
                break
            else:
                Sg.popup("Please select a cutout and beam")

    window.close()


if __name__ == '__main__':
    main()
