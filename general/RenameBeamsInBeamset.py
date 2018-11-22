""" Rename Beams In Current Beam Set
    
    Automatically label beams in Raystation according to UW Standard

    Determines the primary site of the Beam set by prompting the user
    The user identifies the site using the 4 letter pre-fix from the plan name
    If the user supplies more than 4 chars, the name is cropped
    The script will test the orientation of the patient and rename the beams accordingly
    If the beamset contains a couch kick the beams are named using the gXXCyy convention
    
    Versions: 
    01.00.00 Original submission
    01.00.01 PH reviewed, suggested eliminating an unused variable, changing integer
             floating point comparison, and embedding set-up beam creation as a 
             "try" to prevent a script failure if set-up beams were not selected
    01.00.02 PH Reviewed, correct FFP positioning issue.  Changed Beamset failure to 
             load to read the same as other IO-Faults
    01.00.03 RAB Modified for new naming convention on plans and to add support for the
             field descriptions to be used for billing.
    01.00.04 RAB Modified to include isocenter renaming.
    01.00.05 RAB Modified to automatically add the 4th set-up field and clean up creation

    Known Issues:

    Multi-isocenter treatment will be incorrect in the naming conventions for set up
    fields. The script will rename the first four fields regardless of which isocenter
    to which they belong.

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
__date__ = '2018-09-05'

__version__ = '1.0.4'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2018-Sep-05'
__raystation__ = '7.0.0.19'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


def main():
    import UserInterface
    import connect
    import logging
    import sys

    # These are the techniques associated with billing codes in the clinic
    # they will be imported
    available_techniques = [
        'Static MLC -- 2D',
        'Static NoMLC -- 2D',
        'Electron -- 2D',
        'Static MLC -- 3D',
        'Static NoMLC -- 3D',
        'Electron -- 3D',
        'FiF MLC -- 3D',
        'Static PRDR MLC -- 3D',
        'SnS MLC -- IMRT',
        'SnS PRDR MLC -- IMRT',
        'Conformal Arc -- 3D',
        'VMAT Arc -- IMRT']
    supported_rs_techniques = [
        'SMLC',
        'DynamicArc']


    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        plan = connect.get_current('Plan')
        beamset = connect.get_current("BeamSet")

    except Exception:
        UserInterface.WarningBox('This script requires a Beam Set to be loaded')
        sys.exit('This script requires a Beam Set to be loaded')

    initial_sitename = beamset.DicomPlanLabel[:4]
    # Prompt the user for Site Name and Billing technique
    dialog = UserInterface.InputDialog(inputs={'Site': 'Enter a Site name, e.g. BreL',
                                               'Technique': 'Select Treatment Technique (Billing)'},
                                       datatype={'Technique': 'combo'},
                                       initial={'Technique': 'Select',
                                                'Site': initial_sitename},
                                       options={'Technique': available_techniques},
                                       required=['Site', 'Technique'])
    # Show the dialog
    print dialog.show()

    site_name = dialog.values['Site']
    input_technique = dialog.values['Technique']
    #
    # Electrons, 3D, and VMAT Arcs are all that are supported.  Reject plans that aren't
    technique = beamset.DeliveryTechnique
    #
    # Oddly enough, Electrons are DeliveryTechnique = 'SMLC'
    if technique not in supported_rs_techniques:
        logging.warning('Technique: {} unsupported in renaming script'.format(technique))
        raise IOError("Technique unsupported, manually name beams according to clinical convention.")

    # While loop variable definitions
    beam_index = 0
    patient_position = beamset.PatientPosition
    # Turn on set-up fields
    beamset.PatientSetup.UseSetupBeams = True
    logging.debug('Renaming and adding set up fields to Beam Set with name {}, patient position {}, technique {}'.
                  format(beamset.DicomPlanLabel, beamset.PatientPosition, beamset.DeliveryTechnique))
    # Rename isocenters
    for b in beamset.Beams:
        iso_n = int(b.Isocenter.IsocenterNumber)
        b.Isocenter.Annotation.Name = 'Iso_' + beamset.DicomPlanLabel + '_' + str(iso_n + 1)
    #
    # HFS
    if patient_position == 'HeadFirstSupine':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                # 
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

    # Set-Up Fields
        # HFS Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp AP', 'SetUp AP', 0.0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 270.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # HFLDR
    elif patient_position == 'HeadFirstDecubitusRight':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

    # Set-Up Fields
        # HFLDR Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp LtLat', 'SetUp LtLat', 0.0, '5'],
                  1: ['SetUp AP', 'SetUp AP', 270.0, '5'],
                  2: ['SetUp PA', 'SetUp PA', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # HFLDL
    elif patient_position == 'HeadFirstDecubitusLeft':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up Fields
        # HFLDL Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp RtLat', 'SetUp RtLat', 0.0, '5'],
                  1: ['SetUp PA', 'SetUp PA', 270.0, '5'],
                  2: ['SetUp AP', 'SetUp AP', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # HFP
    elif patient_position == 'HeadFirstProne':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')
        #
        # Set-Up fields
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp PA', 'SetUp PA', 0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 90.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 270.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # FFS
    elif patient_position == 'FeetFirstSupine':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occured in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up fields
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp AP', 'SetUp AP', 0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 90.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 270.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]

            # Address the Feet-first prone position
    # FFLDR
    elif patient_position == 'FeetFirstDecubitusRight':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up Fields
        # FFLDR Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp RtLat', 'SetUp RtLat', 0.0, '5'],
                  1: ['SetUp PA', 'SetUp PA', 270.0, '5'],
                  2: ['SetUp AP', 'SetUp AP', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # FFLDL
    elif patient_position == 'FeetFirstDecubitusLeft':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up Fields
        # FFLDL Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp RtLat', 'SetUp RtLat', 0.0, '5'],
                  1: ['SetUp AP', 'SetUp AP', 270.0, '5'],
                  2: ['SetUp PA', 'SetUp PA', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # FFP
    elif patient_position == 'FeetFirstProne':
        for b in beamset.Beams:
            standard_beam_name = 'Naming Error'
            try:
                gantry_angle = int(b.GantryAngle)
                couch_angle = int(b.CouchAngle)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')
        # FFP: Set-Up fields
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp PA', 'SetUp PA', 0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 270.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    else:
        raise IOError("Patient Orientation Unsupported.. Manual Beam Naming Required")


if __name__ == '__main__':
    main()
