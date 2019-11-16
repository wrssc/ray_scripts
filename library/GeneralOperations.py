""" General Operations

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2019-11-15'

__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = ''
__raystation__ = '8.0 SP B'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


def find_scope(level=None, find_scope=False):
    """
    Find the current available scope in RS at the level of level.
        If level is used, and the level is not in the current scope, produce a fault
        If find_scope is used, go as deep as possible and return a dictionary of all levels
            with None used for those not in current scope.
    :param level: if specified, return the RS object at level if it exists
    :param find_scope: if True, return a dict of the available scopes
    :return: if level is specified the RS object is returned.
        If find_scope, then a dict of plan variables is used
    """
    import connect
    import logging

    # Find the deepest available scope and return a dict with available names
    scope = {}
    scope_levels = ['Patient', 'Case', 'Examination', 'Plan', 'BeamSet']

    for l in scope_levels:
        try:
            rs_obj = connect.get_current(l)
        except SystemError:
            rs_obj = None
        if l == level:
            if rs_obj is None:
                raise IOError("No {} loaded, load {}".format(l, l))
            else:
                return rs_obj
        elif find_scope:
            scope[l] = rs_obj

    if find_scope:
        return scope


def logcrit(message):
    import logging
    # Determine deepest scope
    current_scope = find_scope(find_scope=True)
    level = ''
    # if current_scope['Patient'] is not None:
    #    level += 'PatientID: ' + current_scope['Patient'].PatientID + ':'
    if current_scope['Case'] is not None:
        level += 'Case: ' + current_scope['Case'].CaseName + ':'
    if current_scope['Examination'] is not None:
        level += 'Exam: ' + current_scope['Examination'].Name + ':'
    if current_scope['Plan'] is not None:
        level += 'Plan: ' + current_scope['Plan'].Name + ':'
    if current_scope['BeamSet'] is not None:
        level += 'Beamset: ' + current_scope['BeamSet'].DicomPlanLabel + '::'
    message = level + message
    logging.critical(message)
