import numpy as np


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
