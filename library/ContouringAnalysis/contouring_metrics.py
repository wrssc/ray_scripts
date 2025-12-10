import re
import pandas as pd
import numpy as np
from library.api.api_rs import import_raystation_api
connect = import_raystation_api()
from collections import namedtuple
import matplotlib.pyplot as plt
import time
import pickle

Pd = namedtuple('Pd', ['error', 'patient_db', 'machine_db', 'ui', 'case', 'patient', 'exam', 'plan', 'beamset'])


def init_rso(patient, case, exam, patient_db, machine_db, ui, plan, beamset):
    # Get current patient, case, exam
    rso = Pd(error=[],
             patient=patient,
             case=case,
             exam=exam,
             patient_db=patient_db,
             machine_db=machine_db,
             ui=ui,
             plan=plan,
             beamset=beamset)
    return rso

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


def re_init_rso(rso, patient, case_name):
    case_names = [c.CaseName for c in patient.Cases]
    for c in patient.Cases:
        c_name = c.CaseName
        if c_name == case_name:
            c.SetCurrent()
            connect.get_current("Case")
            new_exam = c.Examinations[0]
            new_rso = Pd(error=[],
                         patient=patient,
                         case=c,
                         exam=new_exam,
                         patient_db=rso.patient_db,
                         machine_db=rso.machine_db,
                         ui=rso.ui,
                         plan=rso.plan,
                         beamset=rso.beamset)
            return new_rso


def rename_existing(rso, prefix, add=True, contour_list=[]):
    reo_prefix = re.compile("^" + prefix)
    renamed = []
    # Rename the MD-drawn contours
    if not contour_list:
        contour_list = [r.Name for r in rso.case.PatientModel.RegionsOfInterest]
    for c in contour_list:
        r = rso.case.PatientModel.RegionsOfInterest[c]
        if not re.match(reo_prefix, c):
            if add:
                r.Name = re.sub("^", prefix, c)
                renamed.append(r.Name)
        else:
            if not add:
                r.Name = re.sub(reo_prefix, "", c)
                renamed.append(r.Name)
    return renamed


# Record the time
def add_ml_contours(rso, ml_prefix):
    rois_to_include = ["Brain", "Brainstem", "Cochlea_L", "Cochlea_R",
                       "Esophagus", "Eye_L", "Eye_R", "Glnd_Lacrimal_L",
                       "Glnd_Lacrimal_R", "Glottis", "Larynx_SG", "Lens_L",
                       "Lens_R", "Lips", "Lung_L", "Lung_R", "Bone_Mandible",
                       "Nasolacrimal_Duct_L", "Nasolacrimal_Duct_R", "OpticChiasm",
                       "OpticNrv_L", "OpticNrv_R", "Cavity_Oral", "Parotid_L",
                       "Parotid_R", "Pituitary", "Fossa_Posterior", "SpinalCanal",
                       "SpinalCord", "Glnd_Submand_L", "Glnd_Submand_R", "Joint_TM_L",
                       "Joint_TM_R", "Glnd_Thyroid", "Tongue_Base", "Trachea"]
    examinations = {e.Name: None for e in rso.case.Examinations}
    for e in rso.case.Examinations:
        e.RunOarSegmentation(ModelName="RSL Head and Neck CT",
                             ExaminationsAndRegistrations={e.Name: None},
                             RoisToInclude=rois_to_include)
    renamed = rename_existing(rso, ml_prefix, add=True, contour_list=rois_to_include)
    return renamed
def find_matches(rso, md_pref, ml_pref, md_contours, ml_contours):
    # Using prefixes md_pref and ml_pref, find the matches in md_contours and ml_contours
    # return matches as a tuple and unmated as a list
    matched = []
    unmatched = [m for m in md_contours] + [m for m in ml_contours]

    re_md_pref = re.compile("^" + md_pref)
    re_ml_pref = re.compile("^" + ml_pref)
    for r in md_contours:
        if re.match(re_md_pref, r):
            n_ml = re.sub(re_md_pref, ml_pref, r)
            for c in ml_contours:
                if c == n_ml and 'Brain' not in c:
                    matched.append((c, r))
                    unmatched.remove(c)
                    unmatched.remove(r)
                    break
    return matched, unmatched


def compute_dice_sp_sn_dta(rso, exam_name, target, reference, eval_distance):
    comp_dict = {}
    ss = rso.case.PatientModel.StructureSets[exam_name]
    comp_keys = ['DiceSimilarityCoefficient', 'Precision',
                 'Sensitivity', 'Specificity',
                 'MeanDistanceToAgreement', 'MaxDistanceToAgreement']
    # Get DSC/JAQ/SP/SN
    if ss.RoiGeometries[reference].HasContours() and ss.RoiGeometries[target].HasContours() \
            and ss.RoiGeometries[target].GetRoiVolume() >= 0.01:
        try:
            comp = ss.ComparisonOfRoiGeometries(RoiA=target,
                                                RoiB=reference,
                                                ComputeDistanceToAgreementMeasures=False)
            for k, v in comp.items():
                comp_dict[k] = v

            if comp['Sensitivity'] != 1.0 and eval_distance:
                # RS Crash if DTA is computed with totally overlapping ROIS
                comp = ss.ComparisonOfRoiGeometries(RoiA=target,
                                                    RoiB=reference,
                                                    ComputeDistanceToAgreementMeasures=eval_distance)
                for k, v in comp.items():
                    comp_dict[k] = v
            else:
                comp_dict['Specificity'] = np.NAN
                comp_dict['MeanDistanceToAgreement'] = np.NAN
                comp_dict['MaxDistanceToAgreement'] = np.NAN
        except:
            print(f'Unable to evaluate {target}: {reference}')
            for k in comp_keys:
                comp_dict[k] = np.NAN

    else:
        for k in comp_keys:
            comp_dict[k] = np.NAN
    return comp_dict


def compute_surface_to_surface(rso, exam_name, target, reference):
    ss = rso.case.PatientModel.StructureSets[exam_name]
    surf_dict = {}
    surf_prefix = 'SurfaceToSurface'
    surf_keys = ['Average', 'Max', 'Min']
    if ss.RoiGeometries[target].HasContours() and ss.RoiGeometries[reference].HasContours() \
            and ss.RoiGeometries[target].GetRoiVolume() >= 0.01:
        surf = ss.RoiSurfaceToSurfaceDistanceBasedOnDT(ReferenceRoiName=reference,
                                                       TargetRoiName=target)
        for k, v in surf.items():
            surf_dict[surf_prefix + k] = v

    else:
        print(f'Unable to compute SurfToSurf for {target}:{reference}')
        for s in surf_keys:
            surf_dict[surf_prefix + s] = np.NAN
    return surf_dict


def compute_surface_dice(rso, exam_name, target, reference, expansion=[0.2]):
    # Make an roi with a 2 mm tolerance
    # Make an roi on the ML roi with a 2 mm tolerance
    # Compute dice
    ss = rso.case.PatientModel.StructureSets[exam_name]
    sdice_dict = {}
    for e in expansion:
        key = str(int(e * 10.)) + 'mm SurfaceDiceCoefficient'
        sdice_dict[key] = np.NAN
        if ss.RoiGeometries[target].HasContours() and ss.RoiGeometries[reference].HasContours():
            sources = []
            try:
                wall_target = target + "_Wall"
                make_wall(rso, exam_name, wall_target, target, exp=[e] * 6)
                sources.append(wall_target)
                wall_reference = reference + "_Wall"
                make_wall(rso, exam_name, wall_reference, reference, exp=[e] * 6)
                sources.append(wall_reference)
                comp = ss.ComparisonOfRoiGeometries(RoiA=wall_target,
                                                    RoiB=wall_reference,
                                                    ComputeDistanceToAgreementMeasures=False)
                sdice_dict[key] = comp['DiceSimilarityCoefficient']
                for s in sources:
                    rso.case.PatientModel.RegionsOfInterest[s].DeleteRoi()
            except:
                print(f'Unable to make {wall_target}')
                continue

    return sdice_dict


def compute_params(rso, case_name, matches, ml_prefix, md_prefix, expansion=[0.2], dist=False):
    roi_list = []
    re_ml_prefix = re.compile("^" + ml_prefix)
    comp_keys = ['DiceSimilarityCoefficient', 'Precision',
                 'Sensitivity', 'Specificity',
                 'MeanDistanceToAgreement', 'MaxDistanceToAgreement']
    surf_prefix = 'SurfaceToSurface'
    surf_keys = ['Average', 'Max', 'Min']
    for m in matches:
        for e in rso.case.Examinations:
            print(f'Processing {m} On {e.Name}')
            ss = rso.case.PatientModel.StructureSets[e.Name]
            roi_dict = {}
            organ = re.sub(re_ml_prefix, "", m[0])
            roi_dict['Organ'] = organ
            roi_dict['Case'] = case_name
            roi_dict['keV'] = e.Name
            roi_dict['Compare'] = ml_prefix.replace("_", "_To_") + md_prefix.replace("_", "")
            key = re.sub(re_ml_prefix, "", m[0])
            # Get DSC/JAQ/SP/SN

            comp = compute_dice_sp_sn_dta(rso, e.Name,
                                          target=m[0],
                                          reference=m[1],
                                          eval_distance=dist)
            for k, v in comp.items():
                roi_dict[k] = v

            # Get RoiSurfaceToSurfaceDistanceBasedOn distance transform
            surf = compute_surface_to_surface(rso, e.Name, target=m[0], reference=m[1])
            for k, v in surf.items():
                roi_dict[k] = v
            # Compute Surface Dice
            sdice = compute_surface_dice(rso, e.Name, target=m[0],
                                         reference=m[1],
                                         expansion=expansion)
            for k, v in sdice.items():
                roi_dict[k] = v
                print(f'{k} = {v}')

            # Get contour color
            col = rso.case.PatientModel.RegionsOfInterest[md_prefix + organ].Color
            roi_dict['Color'] = rgb_to_hex((col.R, col.G, col.B))
            roi_list.append(roi_dict)
    return roi_list


def contour_list(rso, prefix=None):
    if not prefix:
        reo_prefix = re.compile(".*")  # Match anything
    else:
        reo_prefix = re.compile("^" + prefix)  # Match beginning of word
    return [r.Name for r in rso.case.PatientModel.RegionsOfInterest if re.match(reo_prefix, r.Name)]


def contour_list_nomatch(rso, prefix):
    reo_prefix = ("^" + prefix)
    return [r.Name for r in rso.case.PatientModel.RegionsOfInterest if not re.match(reo_prefix, r.Name)]


def make_contour_list(rso, existing_prefixes=None, prefix=None):
    # Find all contours matching prefix or not matching existing_prefixes (list)
    contour_list = [r.Name for r in rso.case.PatientModel.RegionsOfInterest]
    matches = []
    #
    if prefix:
        re_prefix = re.compile("^" + prefix)
        for c in contour_list:
            if re.match(re_prefix, c):
                matches.append(c)
    else:
        for c in contour_list:
            matched = False
            for ep in existing_prefixes:
                rep_prefix = re.compile("^C" + ep)
                if re.match(rep_prefix, c):
                    matched = True
            if not matched:
                matches.append(c)
    return matches


def delete_ml_contours(rso, prefix):
    contours = contour_list(rso)
    for c in contours:
        if re.match("^" + prefix, c):
            rso.case.PatientModel.RegionsOfInterest[c].DeleteRoi()


def make_wall(rso, exam_name, name, source, exp):
    fov_wall = rso.case.PatientModel.CreateRoi(
        Name=name,
        Color="192, 192, 192",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    margins = {
        "Type": 'Expand',
        "Superior": exp[0],
        "Inferior": exp[1],
        "Anterior": exp[2],
        "Posterior": exp[3],
        "Right": exp[4],
        "Left": exp[5],
    }
    rso.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
        ExpressionA={
            "Operation": 'Union',
            "SourceRoiNames": [source],
            "MarginSettings": margins,
        },
        ExpressionB={
            "Operation": 'Union',
            "SourceRoiNames": [source],
            "MarginSettings": {'Type': 'Contract',
                               'Superior': exp[0],
                               'Inferior': exp[1],
                               'Anterior': exp[2],
                               'Posterior': exp[3],
                               'Right': exp[4],
                               'Left': exp[5],
                               }
        },
        ResultOperation='Subtraction',
        ResultMarginSettings=margins,
    )
    rso.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
        Examination=rso.case.Examinations[exam_name], Algorithm="Auto"
    )


def intersect_sources(rso, exam_name, name, sources):
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    intersect = rso.case.PatientModel.CreateRoi(
        Name=name,
        Color="0, 0, 192",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    rso.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
        ExpressionA={
            "Operation": 'Intersection',
            "SourceRoiNames": sources,
            "MarginSettings": margins,
        },
        ExpressionB={
            "Operation": 'Union',
            "SourceRoiNames": [],
            "MarginSettings": margins,
        },
        ResultOperation='None',
        ResultMarginSettings=margins,
    )
    rso.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
        Examination=rso.case.Examinations[exam_name], Algorithm="Auto"
    )
