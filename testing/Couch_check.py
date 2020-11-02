""" Check Couch Position
    
    -Check for a patient
    -Load patient
    -Check for s frame
    -Load targets and check sup/inf extent of targets
    -If within boundaries of couch edge check beam angles
    -If angles posterior write out patient MRN

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
__date__ = '2018-Mar-28'
__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '6.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import sys
import os
import csv
import logging
import connect

def main():
    # configs
    roi_name = 'S-frame'
    shift_to_couch_edge = 21.17
    db = connect.get_current('PatientDB')
    male_patients = db.QueryPatientInfo(Filter={'Gender':'Male'})
    female_patients = db.QueryPatientInfo(Filter={'Gender':'Female'})
    all_patients = male_patients + female_patients
    failed_patient_open =[]
    for p in all_patients:
        if p['PatientId'] != '0664526':
            continue
        try:
            patient = db.LoadPatient(PatientInfo = p)
        except:
            failed_patient_open.append(p)

        # Look at all cases
        for c in patient.Cases:
            try:
                c.PatientModel.RegionsOfInterest[roi_name]
                case_name = c.CaseName
            except SystemError:
                # Go on to next case
                continue
            # case_name has an instance of the structure we are looking for
            # now find the examination
            for s in c.PatientModel.StructureSets:
                try:
                    if s.RoiGeometries[roi_name].HasContours():
                        # Get the center of the roi in question in Dicom Coordinates.
                        center_roi = s.RoiGeometries[roi_name].GetCenterOfRoi()
                        exam = s.OnExamination
                    else:
                        continue
                except SystemError:
                    # roi_name is not in this exam
                    continue
                c.PatientModel.CreatePoi(Examination=exam, 
                                         Point={'x':center_roi.x,
                                                'y':center_roi.y,
                                                'z':center_roi.z},
                                         Name='Bob')
                shifted = center_roi + shift_to_couch_edge 
                c.PatientModel.CreatePoi(Examination=exam, 
                                         Point={'x':center_roi.x,
                                                'y':shifted,
                                                'z':center_roi.z},
                                         Name='Bob2')


if __name__ == '__main__':
    main()
