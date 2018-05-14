
import logging

def print_goal(goal, goal_type='xml'):
    left = None
    symbol = None
    right = None

    if goal_type is 'xml':
        if goal.find('type').text == 'DX':
            if 'type' in goal.find('volume').attrib and goal.find('volume').attrib['type'] == 'residual':
                left = '{}{}'.format(goal.find('volume').text, goal.find('volume').attrib['units'])

            else:
                left = 'D{}{}'.format(goal.find('volume').text, goal.find('volume').attrib['units'])

            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '<='

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'lt':
                symbol = '<'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '>='

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'gt':
                symbol = '>'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'VX':
            left = 'V{}'.format(goal.find('dose').text)
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '<='

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'lt':
                symbol = '<'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '>='

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'gt':
                symbol = '>'

            right = '{}{}'.format(goal.find('volume').text, goal.find('volume').attrib['units'])

        elif goal.find('type').text == 'Max':
            left = 'Max'
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '<='

            else:
                symbol = '<'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'Min':
            left = 'Min'
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '>='

            else:
                symbol = '>'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'Mean':
            left = 'Mean'
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'le':
                symbol = '<='

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'lt':
                symbol = '<'

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '>='

            elif 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'gt':
                symbol = '>'

            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                right = '{}%'.format(goal.find('dose').text)

            else:
                right = '{} Gy'.format(goal.find('dose').text)

        elif goal.find('type').text == 'CI':
            if 'units' in goal.find('dose').attrib and goal.find('dose').attrib['units'] == '%':
                left = 'CI{}%'.format(goal.find('dose').text)

            else:
                left = 'CI{}'.format(goal.find('dose').text)

            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '>='

            else:
                symbol = '>'

            right = goal.find('index').text

        elif goal.find('type').text == 'HI':
            left = 'HI{}%'.format(goal.find('volume').text)
            if 'dir' in goal.find('type').attrib and goal.find('type').attrib['dir'] == 'ge':
                symbol = '>='

            else:
                symbol = '>'

            right = goal.find('index').text

        if left is not None:
            return '{} {} {}'.format(left, symbol, right)

        else:
            return None

    elif goal_type is 'eval':
        text = None
        if goal.PlanningGoal.Type == 'VolumeAtDose':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'V{} &lt; {}%'.format(goal.PlanningGoal.ParameterValue / 100,
                                             goal.PlanningGoal.AcceptanceLevel * 100)

            else:
                text = 'V{} &gt; {}%'.format(goal.PlanningGoal.ParameterValue / 100,
                                             goal.PlanningGoal.AcceptanceLevel * 100)

        elif goal.PlanningGoal.Type == 'AbsoluteVolumeAtDose':
            if goal.PlanningGoal.GoalCriteria == 'AtMost':
                text = 'V{} &lt; {}cc'.format(goal.PlanningGoal.ParameterValue / 100,
                                              goal.PlanningGoal.AcceptanceLevel)

            else:
                text = 'V{} &gt; {}cc'.format(goal.PlanningGoal.ParameterValue / 100,
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
            text = 'CI{} &gt; {} '.format(goal.PlanningGoal.ParameterValue / 100, goal.PlanningGoal.AcceptanceLevel)

        elif goal.PlanningGoal.Type == 'HomogeneityIndex':
            text = 'HI{}% &gt; {} '.format(goal.PlanningGoal.ParameterValue * 100, goal.PlanningGoal.AcceptanceLevel)

        return text


def add_goal(goal, roi, plan, targets=None, exam=None, case=None):

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
        priority = 5

    logging.debug('Adding {} constraint {}, {}, {}, {}, priority {}'.
                  format(roi, criteria, goal_type, acceptance, parameter, priority))

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
