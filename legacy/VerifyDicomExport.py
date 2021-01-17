""" Verification of DICOM Export

    You must have TPL_000 open for this to work as this iterates through all
    patient orientations

    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are
           passed to the function as an argument

    Example Usage:

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
__date__ = '2018-Apr-10'
__version__ = '1.0.2'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '7.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/xxxxx'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import connect
import xml.etree.ElementTree

# Define the protocol XML directory
protocol_folder = r'../protocols'

tree = xml.etree.ElementTree.parse('dicom_verification.xml')
case = connect.get_current("Case")
for p in tree.findall('//plan'):
    plan_name = p.find('plan_name')
    plan_comment = p.find('plan_comment')
    examination_name = p.find('examination_name')
    patient_position = p.find('patient_position')
    plan = case.AddNewPlan(PlanName=plan_name,
                    PlannedBy="",
                    Comment=plan_comment,
                    ExaminationName=examination_name,
                    AllowDuplicateNames=False)
    for b in tree.findall('//plan/beam_set'):
        beam_set_name = b.find('beam_set_name')
        machine_name = b.find('machine_name')
        modality = b.find ('modality')
        treatment_technique = b.find ('treatment_technique')
        patient_position = b.find('patient_position')
        number_of_fractions = b.find('number_of_fractions')
        beam_set_comment = b.find('beam_set_comment')
        plan.AddNewBeamSet(
            Name=beam_set_name,
            ExaminationName=examination_name,
            MachineName=machine_name,
            Modality=modality,
            TreatmentTechnique=treatment_technique,
            PatientPosition=patient_position,
            NumberOfFractions=number_of_fractions,
            CreateSetupBeams=True,
            UseLocalizationPointAsSetupIsocenter=False,
            Comment=beam_set_comment,
            RbeModelReference=None,
            EnableDynamicTrackingForVero=False,
            NewDoseSpecificationPointNames=[],
            NewDoseSpecificationPoints=[],
            RespiratoryMotionCompensationTechnique="Disabled",
            RespiratorySignalSource="Disabled")


patient.Save()
#plan = case.TreatmentPlans[plan_name]
#plan.SetCurrent()
#connect.get_current('Plan')

#plan.SetDefaultDoseGrid(VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2})

#retval_1.AddDosePrescriptionToRoi(RoiName="PTV1", DoseVolume=95, PrescriptionType="DoseAtVolume", DoseValue=2500,
#                                  RelativePrescriptionLevel=1, AutoScaleDose=True)

