""" VMAT PRDR

    Version:

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

__author__ = 'Adam Bayliss"
__contact__ = 'rabayliss@wisc.edu'
__date__ = '12-May-2022'
__version__ = '0.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '10A SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import logging


#
# Make plan copy
def make_plan_copy(case, old_plan_name, new_plan_name):
    case.CopyPlan(PlanName=old_plan_name,
                  NewPlanName=new_plan_name,
                  KeepBeamSetNames=True)


def new_col(old_col):
    return (old_col + 90) % 360


def change_col(beam, old_col):
    new_angle = new_col(old_col)
    beam.InitialCollimatorAngle = new_angle


def reverse_dir(beam, old_dir):
    if old_dir == 'CounterClockwise':
        new_dir = 'Clockwise'
    else:
        new_dir = 'CounterClockwise'
    beam.ArcDirectionRotation = new_dir


def reverse_gantry(beam, start, stop):
    new_start = stop
    new_stop = start
    beam.GantryAngle = new_start
    beam.ArcStopGantryAngle = new_stop
    beam.ArcRotationDirection = reverse_dir(beam,
                                            old_dir=beam.ArcRotationDirection)


def reverse_plan(old_plan, new_plan):
    old_data = {}
    for bs in old_plan.BeamSets:
        old_data[bs.DicomPlanLabel] = {}
        for b in bs.Beams:
            old_data[bs.DicomPlanLabel][b.Name] = {'Col': b.InitialCollimatorAngle,
                                                   'Gantry_Start': b.GantryAngle,
                                                   'Gantry_Stop': b.ArcStopGantryAngle,
                                                   'Arc_Rot': b.ArcRotationDirection}
    #
    # Cycle new beamset
    for bs in new_plan.BeamSets:
        for b in bs.Beams:
            col_changed = change_col(b,
                                     old_col=old_data[bs.DicomPlanLabel][b.Name]['Col'])
            gan_changed = reverse_gantry(b,
                                         b.GantryAngle,
                                         b.ArcStopGantryAngle)


def make_prdr_vmat_companion_plans():
    current_plan_name = plan.Name
    new_plan_name = current_plan_name + '_Rvrs'
    make_plan_copy(case, current_plan_name, new_plan_name)
    #
    # Reverse beam directions
    old_plan = case.TreatmentPlans[current_plan_name]
    new_plan = case.TreatmentPlans[new_plan_name]
    new_plan.PlanOptimizations[0].ResetOptimization()
    reverse_plan(old_plan, new_plan)
