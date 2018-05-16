""" Add and Display Clinical Goals

    This package contains functions that manipulate and display clinical goals. The
    print_goal() function will return an AAPM TG-263 compliant text describing the
    goal, and accepts either XML format (see __help__ for details) for a RayStation
    evaluation goal object (default). The following code illustrates how to use this
    function.

    import connect
    import Goals
    plan = connect.get_current('Plan')
    for f in plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
        print Goals.print_goal(f)

    The add_goal() function will add an XML goal to a provided plan. The following
    example illustrates how it is used.

    import xml.etree.ElementTree
    import connect
    import Goals
    tree = xml.etree.ElementTree.parse('example_protocol.xml')
    for g in tree.findall('//goals/roi'):
        print 'Adding goal ' + Goals.print_goal(g, 'xml')
        Goals.add_goal(g, connect.get_current('Plan'))

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Protocol-XMLs'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import logging


def print_goal(goal, goal_type='eval'):
    left = None
    symbol = None
    right = None

    if goal_type == 'xml':
        if goal.find('type').text == 'DX':
            if 'type' in goal.find('volume').attrib and goal.find('volume').attrib['type'] == 'residual':
                left = 'DC{}{}'.format(goal.find('volume').text, goal.find('volume').attrib['units'])

            else:
                left = 'D{}{}'.format(goal.find('volume').text, goal.find('volume').attrib['units'])

            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '&le;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'lt':
                symbol = '&lt;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '&ge;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'gt':
                symbol = '&gt;'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'VX':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                left = 'V{}%'.format(goal.find('dose').text)

            else:
                left = 'V{}Gy'.format(goal.find('dose').text)

            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '&le;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'lt':
                symbol = '&lt;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '&ge;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'gt':
                symbol = '&gt;'

            right = '{}{}'.format(goal.find('volume').text, goal.find('volume').attrib['units'])

        elif goal.find('type').text == 'Max':
            left = 'Max'
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '&le;'

            else:
                symbol = '&lt;'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'Min':
            left = 'Min'
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '&ge;'

            else:
                symbol = '&gt;'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'Mean':
            left = 'Mean'
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '&le;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'lt':
                symbol = '&lt;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '&ge;'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'gt':
                symbol = '&gt;'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'CI':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                left = 'CI{}%'.format(goal.find('dose').text)

            else:
                left = 'CI{}Gy'.format(goal.find('dose').text)

            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '&ge;'

            else:
                symbol = '&gt;'

            right = goal.find('index').text

        elif goal.find('type').text == 'HI':
            left = 'HI{}%'.format(goal.find('volume').text)
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '&ge;'

            else:
                symbol = '&gt;'

            right = goal.find('index').text

        if left is not None:
            return '{} {} {}'.format(left, symbol, right)

        else:
            return None

    elif goal_type == 'eval':
        text = None
        if goal.PlanningGoal.Type == 'VolumeAtDose':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'V{}Gy &lt; {}%'.format(goal.PlanningGoal.ParameterValue / 100,
                                             goal.PlanningGoal.AcceptanceLevel * 100)

            else:
                text = 'V{}Gy &gt; {}%'.format(goal.PlanningGoal.ParameterValue / 100,
                                             goal.PlanningGoal.AcceptanceLevel * 100)

        elif goal.PlanningGoal.Type == 'AbsoluteVolumeAtDose':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'V{}Gy &lt; {}cc'.format(goal.PlanningGoal.ParameterValue / 100,
                                              goal.PlanningGoal.AcceptanceLevel)

            else:
                text = 'V{}Gy &gt; {}cc'.format(goal.PlanningGoal.ParameterValue / 100,
                                              goal.PlanningGoal.AcceptanceLevel)

        elif goal.PlanningGoal.Type == 'DoseAtVolume':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'D{}% &lt; {} Gy'.format(goal.PlanningGoal.ParameterValue * 100,
                                                goal.PlanningGoal.AcceptanceLevel / 100)
            else:
                text = 'D{}% &gt; {} Gy'.format(goal.PlanningGoal.ParameterValue * 100,
                                                goal.PlanningGoal.AcceptanceLevel / 100)

        elif goal.PlanningGoal.Type == 'DoseAtAbsoluteVolume':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'D{}cc &lt; {} Gy'.format(goal.PlanningGoal.ParameterValue,
                                                 goal.PlanningGoal.AcceptanceLevel / 100)
            else:
                text = 'D{}cc &gt; {} Gy'.format(goal.PlanningGoal.ParameterValue,
                                                 goal.PlanningGoal.AcceptanceLevel / 100)

        elif goal.PlanningGoal.Type == 'AverageDose':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'Mean &lt; {} Gy'.format(goal.PlanningGoal.AcceptanceLevel / 100)

            else:
                text = 'Mean &gt; {} Gy'.format(goal.PlanningGoal.AcceptanceLevel / 100)

        elif goal.PlanningGoal.Type == 'ConformityIndex':
            text = 'CI{}Gy &gt; {} '.format(goal.PlanningGoal.ParameterValue / 100, goal.PlanningGoal.AcceptanceLevel)

        elif goal.PlanningGoal.Type == 'HomogeneityIndex':
            text = 'HI{}% &gt; {} '.format(goal.PlanningGoal.ParameterValue * 100, goal.PlanningGoal.AcceptanceLevel)

        return text


def add_goal(goal, plan, roi=None, targets=None, exam=None, case=None):

    if roi is None:
        roi = goal.find('name').text

    if targets is None:
        targets = {}

    # If this is a VX goal
    if goal.find('type').text == 'VX':

        # If greater than or greater than or equal to (RS doesn't distinguish)
        if 'dir' in goal.find('type').attrib and \
                (goal.find('type').attrib['dir'] == 'gt' or goal.find('type').attrib['dir'] == 'ge'):
            criteria = 'AtLeast'

        else:
            criteria = 'AtMost'

        # If this is an absolute volume at dose goal
        if ('units' in goal.find('volume').attrib and goal.find('volume').attrib['units'] == 'cc') \
                or float(goal.find('volume').text) > 100:
            goal_type = 'AbsoluteVolumeAtDose'
            acceptance = float(goal.find('volume').text)

        # Otherwise, assume this is a volume at dose goal
        else:
            goal_type = 'VolumeAtDose'
            acceptance = float(goal.find('volume').text) / 100

        if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['roi'] in targets:
                parameter = float(goal.find('dose').text) * \
                            sum(targets[goal.find('dose').attrib['roi']]['dose'])

            else:
                logging.debug('Goal {} type {} skipped as reference ROI not used'.format(goal.find('name').text,
                                                                                         goal.find('type').text))
                return False

        else:
            parameter = float(goal.find('dose').text) * 100

    elif goal.find('type').text == 'DX':
        if 'dir' in goal.find('type').attrib and \
                (goal.find('type').attrib['dir'] == 'gt' or goal.find('type').attrib['dir'] == 'ge'):
            criteria = 'AtLeast'

        else:
            criteria = 'AtMost'

        if ('units' in goal.find('volume').attrib and goal.find('volume').attrib['units'] == 'cc') \
                or float(goal.find('volume').text) > 100:

            goal_type = 'DoseAtAbsoluteVolume'
            if 'type' in goal.find('volume').attrib and goal.find('volume').attrib['type'] == 'residual' \
                    and exam is not None and case is not None:
                parameter = max(case.PatientModel.StructureSets[exam.Name].RoiGeometries.GetRoiVolume -
                                float(goal.find('volume').text), 0)

            else:
                parameter = float(goal.find('volume').text)

        else:
            goal_type = 'DoseAtVolume'
            parameter = float(goal.find('volume').text) / 100

        if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['roi'] in targets:
                acceptance = float(goal.find('dose').text) * \
                             sum(targets[goal.find('dose').attrib['roi']]['dose'])
            else:
                logging.debug('Goal {} type {} skipped as reference ROI not used'.format(goal.find('name').text,
                                                                                         goal.find('type').text))
                return False

        else:
            acceptance = float(goal.find('dose').text) * 100

    elif goal.find('type').text == 'Max':
        criteria = 'AtMost'
        goal_type = 'DoseAtAbsoluteVolume'
        if goal.find('volume') is not None:
            parameter = float(goal.find('volume').text)

        else:
            parameter = 0.03

        if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
            if 'roi' in goal.find('dose').attrib and goal.find('dose').attrib['roi'] in targets:
                acceptance = float(goal.find('dose').text) * \
                             sum(targets[goal.find('dose').attrib['roi']]['dose'])

            else:
                logging.debug('Goal {} type {} skipped as reference ROI not used'.format(goal.find('name').text,
                                                                                         goal.find('type').text))
                return False

        else:
            acceptance = float(goal.find('dose').text) * 100

    elif goal.find('type').text == 'Min':
        criteria = 'AtLeast'
        goal_type = 'DoseAtAbsoluteVolume'
        if goal.find('volume') is not None:
            diff = float(goal.find('volume').text)

        else:
            diff = 0.03

        if case is not None and exam is not None:
            parameter = max(0, case.PatientModel.StructureSets[exam.Name].RoiGeometries.GetRoiVolume - diff)

        else:
            parameter = None

        if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
            if 'roi' in goal.find('dose').attrib and goal.find('dose').attrib['roi'] in targets:
                acceptance = float(goal.find('dose').text) * \
                             sum(targets[goal.find('dose').attrib['roi']]['dose'])

            else:
                logging.debug('Goal {} type {} skipped as reference ROI not used'.format(goal.find('name').text,
                                                                                         goal.find('type').text))
                return False

        else:
            acceptance = float(goal.find('dose').text) * 100

    elif goal.find('type').text == 'Mean':
        goal_type = 'AverageDose'
        parameter = None
        if 'dir' in goal.find('type').attrib and \
                (goal.find('type').attrib['dir'] == 'gt' or goal.find('type').attrib['dir'] == 'ge'):
            criteria = 'AtLeast'

        else:
            criteria = 'AtMost'

        if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['roi'] in targets:
                acceptance = float(goal.find('dose').text) * \
                             sum(targets[goal.find('dose').attrib['roi']]['dose'])

            else:
                logging.debug('Goal {} type {} skipped as reference ROI not used'.format(goal.find('name').text,
                                                                                         goal.find('type').text))
                return False

        else:
            acceptance = float(goal.find('dose').text) * 100

    elif goal.find('type').text == 'CI':
        criteria = 'AtLeast'
        goal_type = 'ConformityIndex'
        acceptance = float(goal.find('index').text)

        if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['roi'] in targets:
                parameter = float(goal.find('dose').text) * \
                            sum(targets[goal.find('dose').attrib['roi']]['dose'])
            else:
                logging.debug('Goal {} type {} skipped as reference ROI not used'.format(goal.find('name').text,
                                                                                         goal.find('type').text))
                return False

        else:
            parameter = float(goal.find('dose').text) * 100

    elif goal.find('type').text == 'HI':
        criteria = 'AtLeast'
        goal_type = 'HomogeneityIndex'
        acceptance = float(goal.find('index').text)
        parameter = float(goal.find('volume').text) / 100

    else:
        logging.warning('Unknown goal type {} for structure {}'.format(goal.find('type').text,
                                                                       goal.find('name').text))
        return False

    if goal.find('priority') is not None:
        priority = int(goal.find('priority').text)

    else:
        priority = 1

    logging.debug('Adding {} constraint {}, {}, {}, {}, priority {}'.
                  format(roi, criteria, goal_type, acceptance, parameter, priority))

    try:
        if parameter is None:
            plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi,
                                                                 GoalCriteria=criteria,
                                                                 GoalType=goal_type,
                                                                 AcceptanceLevel=acceptance,
                                                                 IsComparativeGoal=False,
                                                                 Priority=priority)

        else:
            plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi,
                                                                 GoalCriteria=criteria,
                                                                 GoalType=goal_type,
                                                                 AcceptanceLevel=acceptance,
                                                                 ParameterValue=parameter,
                                                                 IsComparativeGoal=False,
                                                                 Priority=priority)

        return True

    except Exception as e:
        logging.warning('{} constraint {}, {}, {}, {}, priority {} could not be added: {}'.
                        format(roi, criteria, goal_type, acceptance, parameter, priority, str(e).splitlines()[0]))
        return False
