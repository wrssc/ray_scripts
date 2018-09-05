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

__version__ = '1.0.3'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'xxxxxxxxxxxx'

__reviewed__ = 'xxxx-xx-xx'
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

    availabletechniques = [
        'Static MLC -- 2D',
        'Static NoMLC -- 2D',
        'Static MLC -- 3D',
        'Static NoMLC -- 3D',
        'FiF MLC -- 3D',
        'Static PRDR MLC -- 3D',
        'SnS MLC -- IMRT',
        'SnS PRDR MLC -- IMRT',
        'Conformal Arc -- 3D',
        'VMAT Arc -- IMRT']
    supportedRStechniques = [
        'SMLC',
        'DynamicArc',
    ]

    dialog = UserInterface.InputDialog(inputs={'Site': 'Enter a Site name, e.g. BreL',
                                               'Technique': 'Select Treatment Technique (Billing)'},
                                       datatype={'Technique': 'combo'},
                                       initial={'Technique': 'Select'},
                                       options={'Technique': availabletechniques},
                                       required=['Site', 'Technique'])
    # Show the dialog
    print dialog.show()

    site_name = dialog.values['Site']
    inputtechnique = dialog.values['Technique']

    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        plan = connect.get_current('Plan')
        beamset = connect.get_current("BeamSet")

    except Exception:
        UserInterface.WarningBox('This script requires a Beam Set to be loaded')
        sys.exit('This script requires a Beam Set to be loaded')

    #
    # Electrons, 3D, and VMAT Arcs are all that are supported.  Reject plans that aren't
    technique = beamset.DeliveryTechnique
    #
    # Oddly enough, Electrons are DeliveryTechnique = 'SMLC'
    if technique not in supportedRStechniques:
        raise IOError("Technique unsupported, manually name beams according to clinical convention.")

    # While loop variable definitions
    beamsinrange = True
    beam_index = 0
    patient_position = beamset.PatientPosition
    #
    # HFS Beam Naming
    # Loop through all beams and except when there are no more (beamsinrange = False)
    if patient_position == 'HeadFirstSupine':
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
                                        ' ' + inputtechnique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + inputtechnique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif gantry_angle > 180 and gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif gantry_angle > 270 and gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif gantry_angle > 0 and gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif gantry_angle > 90 and gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occured in setting names of beams')
                sys.exit('Error occurred in setting names of beams')
        connect.await_user_input(
            'Please go to Plan Design>Plan Setup and use Copy Setup to ensure there are 4 Setup beams')
        #
        # Set-Up Fields
        try:
            #
            # AP set-up field
            beamset.PatientSetup.SetupBeams[0].Name = "SetUp AP"
            beamset.PatientSetup.SetupBeams[0].Description = "SetUp AP"
            beamset.PatientSetup.SetupBeams[0].GantryAngle = "0.0"
            beamset.PatientSetup.SetupBeams[0].Segments[0].DoseRate = "5"

            #
            # Rt Lateral set-up field
            beamset.PatientSetup.SetupBeams[1].Name = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].Description = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].GantryAngle = "270.0"
            beamset.PatientSetup.SetupBeams[1].Segments[0].DoseRate = "5"

            #
            # Lt Lateral set-up field
            beamset.PatientSetup.SetupBeams[2].Name = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].Description = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].GantryAngle = "90.0"
            beamset.PatientSetup.SetupBeams[2].Segments[0].DoseRate = "5"
            #
            # Cone-Beam CT set-up field
            try:
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
            except:
                await_user_input(
                    'Pretty Please go to Plan Design>Plan Setup and copy any Setup Beam then continue script')
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
        except:
            raise IOError('Please select Create Set Up Beams in Edit Plan and Rerun script')

            # Address the Head-first prone position
    # Loop through all beams and except when there are no more (beamsinrange = False)
    elif patient_position == 'HeadFirstProne':
        for b in beamset.Beams:
            try:
                GantryAngle = int(b.GantryAngle)
                CouchAngle = int(b.CouchAngle)
                GantryAngleString = str(int(GantryAngle))
                CouchAngleString = str(int(CouchAngle))
                # 
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'
                    if CouchAngle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_Arc_' + site_name +
                                            '_' + arc_direction_string)
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_Arc_' + site_name +
                                            '_' + arc_direction_string + '_c' + CouchAngleString.zfill(1))
                else:
                    if CouchAngle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_g'
                                            + GantryAngleString.zfill(2) + 'c' + CouchAngleString.zfill(2))
                    elif GantryAngle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif GantryAngle > 180 and GantryAngle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif GantryAngle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif GantryAngle > 270 and GantryAngle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif GantryAngle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif GantryAngle > 0 and GantryAngle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif GantryAngle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif GantryAngle > 90 and GantryAngle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    b.Name = standard_beam_name
                beam_index += 1
            except:
                beamsinrange = False
        await_user_input('Please go to Plan Design>Plan Setup and use Copy Setup to ensure there are 4 Setup beams')
        #
        # Set-Up fields
        try:
            #
            # PA set-up field
            beamset.PatientSetup.SetupBeams[0].Name = "SetUp PA"
            beamset.PatientSetup.SetupBeams[0].Description = "SetUp PA"
            beamset.PatientSetup.SetupBeams[0].GantryAngle = "0.0"
            beamset.PatientSetup.SetupBeams[0].Segments[0].DoseRate = "5"

            #
            # Rt Lateral set-up field
            beamset.PatientSetup.SetupBeams[1].Name = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].Description = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].GantryAngle = "90.0"
            beamset.PatientSetup.SetupBeams[1].Segments[0].DoseRate = "5"

            #
            # Lt Lateral set-up field
            beamset.PatientSetup.SetupBeams[2].Name = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].Description = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].GantryAngle = "270.0"
            beamset.PatientSetup.SetupBeams[2].Segments[0].DoseRate = "5"

            #
            # Cone-Beam CT set-up field
            try:
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
            except:
                await_user_input(
                    'Pretty Please go to Plan Design>Plan Setup and copy any Setup Beam then continue script')
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
        except:
            raise IOError('Please select Create Set Up Beams in Edit Plan and Rerun script')
            # Address the Feet-first supine position
    # Loop through all beams and except when there are no more (beamsinrange = False)
    elif patient_position == 'FeetFirstSupine':
        for b in beamset.Beams:
            try:
                GantryAngle = int(b.GantryAngle)
                CouchAngle = int(b.CouchAngle)
                GantryAngleString = str(int(GantryAngle))
                CouchAngleString = str(int(CouchAngle))

                # 
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'
                    if CouchAngle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_Arc_' + site_name +
                                            '_' + arc_direction_string)
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_Arc_' + site_name +
                                            '_' + arc_direction_string + '_c' + CouchAngleString.zfill(1))
                else:
                    if CouchAngle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_g'
                                            + GantryAngleString.zfill(2) + 'c' + CouchAngleString.zfill(2))
                    elif GantryAngle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif GantryAngle > 180 and GantryAngle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif GantryAngle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif GantryAngle > 270 and GantryAngle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif GantryAngle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif GantryAngle > 0 and GantryAngle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif GantryAngle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif GantryAngle > 90 and GantryAngle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    b.Name = standard_beam_name
                beam_index += 1
            except:
                beamsinrange = False
        await_user_input('Please go to Plan Design>Plan Setup and use Copy Setup to ensure there are 4 Setup beams')
        #
        # Set-Up Fields
        try:
            # AP set-up field
            beamset.PatientSetup.SetupBeams[0].Name = "SetUp AP"
            beamset.PatientSetup.SetupBeams[0].Description = "SetUp AP"
            beamset.PatientSetup.SetupBeams[0].GantryAngle = "0.0"
            beamset.PatientSetup.SetupBeams[0].Segments[0].DoseRate = "5"

            # Rt Lateral set-up field
            beamset.PatientSetup.SetupBeams[1].Name = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].Description = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].GantryAngle = "90.0"
            beamset.PatientSetup.SetupBeams[1].Segments[0].DoseRate = "5"

            # Lt Lateral set-up field
            beamset.PatientSetup.SetupBeams[2].Name = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].Description = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].GantryAngle = "270.0"
            beamset.PatientSetup.SetupBeams[2].Segments[0].DoseRate = "5"

            #
            # Cone-Beam CT set-up field
            try:
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
            except:
                await_user_input(
                    'Pretty Please go to Plan Design>Plan Setup and copy any Setup Beam then continue script')
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
        except:
            raise IOError('Please select Create Set Up Beams in Edit Plan and Rerun script')

            # Address the Feet-first prone position
    # Loop through all beams and except when there are no more (beamsinrange = False)
    elif patient_position == 'FeetFirstProne':
        for b in beamset.Beams:
            try:
                GantryAngle = int(b.GantryAngle)
                CouchAngle = int(b.CouchAngle)
                GantryAngleString = str(int(GantryAngle))
                CouchAngleString = str(int(CouchAngle))
                # 
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'
                    if CouchAngle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_Arc_' + site_name +
                                            '_' + arc_direction_string)
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_Arc_' + site_name +
                                            '_' + arc_direction_string + '_c' + CouchAngleString.zfill(1))
                else:
                    if CouchAngle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_g'
                                            + GantryAngleString.zfill(2) + 'c' + CouchAngleString.zfill(2))
                    elif GantryAngle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif GantryAngle > 180 and GantryAngle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif GantryAngle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif GantryAngle > 270 and GantryAngle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif GantryAngle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif GantryAngle > 0 and GantryAngle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif GantryAngle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif GantryAngle > 90 and GantryAngle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    b.Name = standard_beam_name
                beam_index += 1
            except:
                beamsinrange = False
        await_user_input('Please go to Plan Design>Plan Setup and use Copy Setup to ensure there are 4 Setup beams')
        try:
            # PA set-up field
            beamset.PatientSetup.SetupBeams[0].Name = "SetUp PA"
            beamset.PatientSetup.SetupBeams[0].Description = "SetUp PA"
            beamset.PatientSetup.SetupBeams[0].GantryAngle = "0.0"
            beamset.PatientSetup.SetupBeams[0].Segments[0].DoseRate = "5"

            # Rt Lateral set-up field
            beamset.PatientSetup.SetupBeams[1].Name = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].Description = "SetUp RtLat"
            beamset.PatientSetup.SetupBeams[1].GantryAngle = "270.0"
            beamset.PatientSetup.SetupBeams[1].Segments[0].DoseRate = "5"

            # Lt Lateral set-up field
            beamset.PatientSetup.SetupBeams[2].Name = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].Description = "SetUp LtLat"
            beamset.PatientSetup.SetupBeams[2].GantryAngle = "90.0"
            beamset.PatientSetup.SetupBeams[2].Segments[0].DoseRate = "5"
            #
            # Cone-Beam CT set-up field
            try:
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
            except:
                await_user_input(
                    'Pretty Please go to Plan Design>Plan Setup and copy any Setup Beam then continue script')
                beamset.PatientSetup.SetupBeams[3].Name = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].Description = "SetUp CBCT"
                beamset.PatientSetup.SetupBeams[3].GantryAngle = "0.0"
                beamset.PatientSetup.SetupBeams[3].Segments[0].DoseRate = "5"
        except:
            raise IOError('Please select Create Set Up Beams in Edit Plan and Rerun script')
    else:
        raise IOError("Patient Orientation Unsupported.. Manual Beam Naming Required")


if __name__ == '__main__':
    main()
