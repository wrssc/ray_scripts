""" Restore Beam Templates from csv files 
  
    A RayStation-based script to restore all beam templates to a given patient plan.  
    Note:

        -RayStation does not support automatic creation of beam templates, this is an 
         unscriptable action. This script simply creates the plan elements which will 
         be saved to the beam list templates

        -RayStation Limits the number of characters on beamset names to 16, thus all template
         names are placed by the script in the Beam Set comments accessed in the Edit Plan 
         Menu.
       
        -The orientation of each beam template is saved from the patient orientation of the 
         dataset in which the template was created. Thus to have FFS beamtemplates successfully
         import from the csv file, you must have a FFS examination open

    Inputs:
        - A ".csv" file with the following format:
          PlanName,BeamSetName,TemplateName,TreatmentTechnique,PatientPosition,BeamName...
             ...,BeamDescription,ArcStart,ArcStop,ArcDirection,CollimatorAngle,CouchAngle
          Note that the first row is assumed to be a header and will be skipped

    Usage:
        The user will need to have a patient open in the orientation they want to use for the templates.  
        (The script uses get_current method from the RayStation console to find the current examination).
    
        Launch the script from the RayStation window. Select the csv file to build the templates
        Wait until the script completes. Under each beamset from the constructed plans 
        find and copy the beamset comments. Save each template with the title of the beamset comments


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
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


def main CreateTemplateBeamSets():

    # Import packages
    import connect 
    import sys
    import csv
    import UserInterface
    from collections import namedtuple

    # Set the current scope of RayStation to the open patient.
    try:
         patient = connect.get_current("Patient")
    except SystemError:
         raise IOError("No Patient loaded. Load patient case and plan.")

    try:
         case = connect.get_current("Case")
    except SystemError:
         raise IOError("No Case loaded. Load patient case and plan.")

    try:
         examination = connect.get_current("Examination")
    except SystemError:
         raise IOError("No Examination loaded. Load patient case and plan.")

    # Open the folder_browser method from the CommonDialog class and prompt the user to select the csv
    common = UserInterface.CommonDialog()
    path = common.folder_browser('Select a folder containing the beam template .csv file')
    filename = common.open_file('Select the beam template csv')
 
    # The container for each line of the csv is the Row class listed below
    Row = namedtuple('Row',('PlanName','BeamSetName','TemplateName','TreatmentTechnique','PatientPosition','BeamName','BeamDescription','GantryStart','GantryStop','ArcDirection','CollimatorAngle','CouchAngle'))
    # Open the csv delimited file containing the list beam templates to be loaded
    # Ensure that the first row is a header for the columns
    filecsv = filename
    with open(filecsv,'r') as f:
        r = csv.reader(f, delimiter=',')
        r.next() # Skip header
        beams = [Row(*l) for l in r]

    IsoPosition = { 'x': 7.0, 'y': -25.0, 'z': -70.0 }
    currentplan = ""
    currentbeamset = ""
    for beam in beams:
        if beam.PlanName != currentplan:
            try: 
                plan = case.AddNewPlan(PlanName=beam.PlanName, PlannedBy="", Comment="",
                                       ExaminationName=examination.Name, AllowDuplicateNames=False)
                currentplan = beam.PlanName
            except SystemError:
                RaiseError = "Unable to load Plan: %s" % beam.PlanName
                raise IOError(RaiseError)
        if beam.BeamSetName != currentbeamset:
            try: 
                if beam.TreatmentTechnique == 'VMAT':
                    beamset = plan.AddNewBeamSet(Name=beam.BeamSetName, ExaminationName=examination.Name,
                                                 MachineName="TrueBeam", Modality="Photons", TreatmentTechnique=beam.TreatmentTechnique,
                                                 PatientPosition=beam.PatientPosition, NumberOfFractions=999, CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False, Comment=beam.TemplateName,
                                                 RbeModelReference=None, EnableDynamicTrackingForVero=False,
                                                 NewDoseSpecificationPointNames=[], NewDoseSpecificationPoints=[],
                                                 RespiratoryMotionCompensationTechnique="Disabled", RespiratorySignalSource="Disabled")
                elif beam.TreatmentTechnique == 'Conformal' or 'SMLC':
                    beamset = plan.AddNewBeamSet(Name=beam.BeamSetName, ExaminationName=examination.Name,
                                                 MachineName="TrueBeam", Modality="Photons", TreatmentTechnique=beam.TreatmentTechnique,
                                                 PatientPosition=beam.PatientPosition, NumberOfFractions=999, CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False, Comment=beam.TemplateName,
                                                 RbeModelReference=None, EnableDynamicTrackingForVero=False,
                                                 NewDoseSpecificationPointNames=[], NewDoseSpecificationPoints=[],
                                                 RespiratoryMotionCompensationTechnique="Disabled", RespiratorySignalSource="Disabled")
                # Set an rather arbritrary isocenter position
                IsoParams = beamset.CreateDefaultIsocenterData(Position = IsoPosition)
                IsoParams['Name'] = "iso_"+beam.BeamSetName
                IsoParams['NameOfIsocenterToRef'] = "iso_"+beam.BeamSetName
                currentbeamset = beam.BeamSetName
            except SystemError:
                raise IOError("No plan or beamset managed to load.")
        # Create a new arc beam - note this will need to be changed for accepting 3D plans types.
        try:
            if beam.TreatmentTechnique == 'VMAT':
                beamset.CreateArcBeam(ArcStopGantryAngle=beam.GantryStop, ArcRotationDirection=beam.ArcDirection,
                                      Energy=6, IsocenterData=IsoParams, Name=beam.BeamName, Description=beam.BeamDescription,
                                      GantryAngle=beam.GantryStart, CouchAngle=beam.CouchAngle,
                                      CollimatorAngle=beam.CollimatorAngle)
            elif beam.TreatmentTechnique == 'Conformal' or 'SMLC':
                beamset.CreatePhotonBeam(Energy = 6, IsocenterData=IsoParams, Name=beam.BeamName,Description=beam.BeamDescription,
                                         GantryAngle=beam.GantryStart, CouchAngle=beam.CouchAngle,
                                         CollimatorAngle=beam.CollimatorAngle)
        except SystemError:
            RaiseError = "Unable to load Beam: %s" % beam.BeamName
            raise IOError(RaiseError)
    patient.Save()
