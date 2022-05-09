""" Output Bladder info

    -Check for a patient
    -Load patient

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

import logging
import connect
import pandas as pd
import re
import matplotlib
import datetime


def get_roi_list(case, exam_name=None):
    """
    Get a list of all rois
    Args:
        case: RS case object

    Returns:
        roi_list: [str1,str2,...]: a list of roi names
    """
    roi_list = []
    if exam_name:
        structure_sets = [case.PatientModel.StructureSets[exam_name]]
    else:
        structure_sets = [s for s in case.PatientModel.StructureSets]

    for s in structure_sets:
        for r in s.RoiGeometries:
            if r.OfRoi.Name not in roi_list:
                roi_list.append(r.OfRoi.Name)
    return roi_list


def match_roi_name(roi_names, roi_list):
    """
    Match the structures in case witht
    Args:
        roi_names: [str1, str2, ...]: list of names to search for
        roi_list: [str1, str2, ...]: list of current rois

    Returns:
        matches: [str1, str2, ...]: list of matching rois
    """
    matches = []
    for r_n in roi_names:
        exp_r_n = r_n
        for m in roi_list:
            if re.search(exp_r_n, m, re.IGNORECASE):
                matches.append(m)
    return matches


def get_roi_geometries(case, exam_name, roi_names):
    all_geometries = get_roi_list(case, exam_name)
    matches = match_roi_name(roi_names, all_geometries)
    matching_geometries = []
    ss = case.PatientModel.StructureSets[exam_name]
    for m in matches:
        if ss.RoiGeometries[m].HasContours():
            matching_geometries.append(ss.RoiGeometries[m])
    return matching_geometries


def get_volumes(geometries):
    vols = {g.OfRoi.Name: g.GetRoiVolume() for g in geometries}
    return vols


def main():
    # configs
    roi_name = 'Bladder'
    now = datetime.datetime.now()
    dt_string = now.strftime("%m%d%Y_%H%M%S")

    # Distance from s-frame center to couch edge
    db = connect.get_current('PatientDB')
    # male_patients = db.QueryPatientInfo(Filter={'Gender':'Male'})
    # female_patients = db.QueryPatientInfo(Filter={'Gender':'Female'})
    # all_patients = male_patients + female_patients
    roi_names = ["Bladder"]
    plan_name = "Pros"
    prostates = db.QueryPatientInfo(Filter={'BodySite': 'Prostate'})
    found_patients = []
    found_structures = []
    for infos in prostates:
        try:
            db.LoadPatient(PatientInfo=infos, AllowPatientUpgrade=False)
            patient = connect.get_current("Patient")
            for case in patient.Cases:
                for p in case.TreatmentPlans:
                    for b in p.BeamSets:
                        if plan_name in b.DicomPlanLabel:
                            # roi_list = get_roi_list(case,exam_name="DIBH")
                            matches = get_roi_geometries(case, "CT 1", roi_names)
                            if matches:
                                found_structures.append(get_volumes(matches))
                                found_patients.append(infos)
        except Exception as e:
            if "is locked by" in e.Message:
                logging.debug('patient locked')
                pass
            else:
                logging.debug(e.Message)
    df = pd.DataFrame(found_structures)
    df.to_pickle(output_file)
    df['Bladder'].plot.hist(bins=10, alpha=1)
    matplotlib.plt.axvline(df['Bladder'].mean(), color='r', linestyle='dashed', linewidth=2)


if __name__ == '__main__':
    main()
