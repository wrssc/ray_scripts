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
import StructureOperations

def main():
    # configs
    roi_name = 'S-frame'
    # Distance from s-frame center to couch edge
    shift_to_couch_edge_s_frame = 17.38
    tolerance = 2
    db = connect.get_current('PatientDB')
    male_patients = db.QueryPatientInfo(Filter={'Gender':'Male'})
    female_patients = db.QueryPatientInfo(Filter={'Gender':'Female'})
    all_patients = male_patients + female_patients
    failed_patient_open =[]
    for p in all_patients:
        if p['PatientID'] != 'TPL_000':
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
                min_extent = 1000
                max_extent = -1000
                for r in c.PatientModel.RegionsOfInterest:
                   if r.Type == 'Support':
                       if s.RoiGeometries[r.Name].HasContours():
                           support = True
                           b = s.RoiGeometries[r.Name].GetBoundingBox()
                           logging.debug('Support {} has min/max [{}, {}]'.format(r.Name,b[0].z,b[1].z))
                           min_extent = min(min_extent,b[0].z)
                           max_extent = max(max_extent,b[1].z)
                if not support:
                    connect.await_user_input('No support structures found, declare a support and continue')
                else:
                    logging.debug('Support type has min position {} and max position {}'.format(min_extent, max_extent))
                # S-frame loop
                try:
                    if s.RoiGeometries[roi_name].HasContours():
                        # Get the center of the roi in question in Dicom Coordinates.
                        # exam = s.OnExamination
                        center_roi = s.RoiGeometries[roi_name].GetCenterOfRoi()
                        couch_edge = center_roi.z + shift_to_couch_edge_s_frame
                    #else:
                    #    continue
                except SystemError:
                    logging.debug('No structure called {} found'.format(roi_name))
                    # roi_name is not in this exam
                    # continue
                
                target_list = StructureOperations.find_targets(c)
                if target_list and support:
                    problem_targets = []
                    for t in target_list:
                        if s.RoiGeometries[t].HasContours():
                            b_t = s.RoiGeometries[t].GetBoundingBox()
                            if b_t[0].z < min_extent:
                                logging.debug('Target {name}: [max, min]=[{x}, {n}] exceeds support [{sx}, {sn}]'.format(
                                                                                                    name=t,
                                                                                                    n=b_t[0].z,
                                                                                                    x=b_t[1].z,
                                                                                                    sx=min_extent,
                                                                                                    sn=max_extent))
                                connect.await_user_input('Target {} exists past the end of {}'.format(t, min_extent))
                            if b_t[1].z > max_extent:
                                logging.debug('Target {name}: [max, min]=[{x}, {n}] exceeds support [{sx}, {sn}]'.format(
                                                                                                    name=t,
                                                                                                    n=b_t[0].z,
                                                                                                    x=b_t[1].z,
                                                                                                    sx=min_extent,
                                                                                                    sn=max_extent))
                                connect.await_user_input('Target {} exists past the end of {}'.format(t, max_extent))
                            if (b_t[0].z < couch_edge - tolerance) and (b_t[1].z > couch_edge + tolerance):
                                logging.debug('Target {t}: Couch edge at {e} cm, min at {n}, max at {x}'.format(
                                                                                                    t=t,
                                                                                                    e=couch_edge,
                                                                                                    n=couch_edge-tolerance,
                                                                                                    x=couch_edge+tolerance))
                                connect.await_user_input('Structure {} appears to traverse the s-frame/table edge')
                # c.PatientModel.CreatePoi(Examination=exam,
                #                          Point={'x':center_roi.x,
                #                                 'y':center_roi.y,
                #                                 'z':center_roi.z},
                #                          Name='CouchPt')
                # c.PatientModel.CreatePoi(Examination=exam,
                #                          Point={'x':center_roi.x,
                #                                 'y':center_roi.y,
                #                                 'z':shifted},
                #                          Name='Couchpt2')


if __name__ == '__main__':
    main()
