""" Plan Check
    Run basic plan integrity checks and parse the log file. Meant to be run
    on completed plans.

    This is basically a wrapper for the physics review that will launch the
    tree only.


    Scope: Requires RayStation beamset to be loaded

    Example Usage:

    Script Created by RAB May 1st 2022
    Prerequisites:

    Version history:


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
__date__ = '2023-July-19'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__credits__ = ['']

import logging
import PySimpleGUI as Sg
import connect
from GeneralOperations import find_scope
from collections import namedtuple
from System import Environment
from PlanReview.utils import comment_to_clipboard, perform_automated_checks


def automated_tests():
    try:
        user_name = str(Environment.UserName)
    except Exception as e:
        logging.debug('{}'.format(e))
        user_name = None

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
    r = comment_to_clipboard(rso)

    beamsets = [b.Name for b in rso.plan.BeamSets]
    #
    # Run the automated tests
    tree_data, tree_children = perform_automated_checks(
        rso, do_physics_review=False, display_progress=True,values=None,
        beamsets=True)

    #
    # Gui
    Sg.theme('Topanga')
    col_widths = [20]
    col1 = Sg.Column([[Sg.Frame('ReviewChecks:',
                                [[
                                    Sg.Tree(
                                        data=tree_data,
                                        headings=['Checks', ],
                                        auto_size_columns=False,
                                        num_rows=40,
                                        col0_width=120,
                                        col_widths=col_widths,
                                        key='-TREE-',
                                        show_expanded=False,
                                        justification="left",
                                        enable_events=True),
                                ], [Sg.Button('Ok'), Sg.Button('Pause Script'),
                                    Sg.Button('Repeat Tests')]])]], pad=(0, 0))
    layout = [[col1]]

    window = Sg.Window('Plan Review: ' + user_name, layout)

    while True:  # Event Loop
        event, values = window.read()
        if event in (Sg.WIN_CLOSED, 'Cancel'):
            break
        elif event == 'Pause Script':
            connect.await_user_input('Review Paused. Resume Script to Continue')
        elif event == 'Repeat Tests':
            tree_data, tree_children = perform_automated_checks(
                rso, do_physics_review=False, display_progress=True, values=None,
                beamsets=None)
            window['-TREE-'].update(values=tree_data)
        elif event in 'Ok':
            break

    window.close()
    r.destroy()

