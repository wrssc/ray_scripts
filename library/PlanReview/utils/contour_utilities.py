import numpy as np
import logging


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


def roi_has_contours(rso, roi_name):
    """
    Check if an ROI has contours.

    Args:
        rso: RayStation object containing beamset information.
        roi_name (str): Name of the ROI to check for contours.

    Returns:
        bool: True if the ROI has contours, otherwise False.
    """
    try:
        return rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name].HasContours()
    except Exception as e:
        logging.warning(f"An error occurred while checking for contours in {roi_name}: {e}")
        return False


def unique_roi_name(rso, desired_name):
    """
    Generate a unique ROI name by appending a number to the desired name.

    Args:
        rso: RayStation object containing beamset information.
        desired_name (str): The desired name for the ROI.

    Returns:
        str: A unique ROI name.
    """
    try:
        return rso.case.PatientModel.GetUniqueRoiName(DesiredName=desired_name)
    except Exception as e:
        return None


def create_roi(rso, roi_name, roi_type='Undefined', color="192, 192, 192",
               tissue_name=None, rbe_cell_type_name=None, roi_material=None):
    """
    Create an ROI in RayStation.

    Args:
        rso: NamedTuple of ScriptObjects in RayStation [case, exam, plan, beamset, db].
        roi_name (str): Name of the ROI to create.
        roi_type (str): Type of the ROI to create.
        color (str): Color of the ROI.

    Returns:
        bool: True if the ROI is successfully created, otherwise False.
    """
    try:
        rso.case.PatientModel.CreateRoi(
            Name=roi_name,
            Color=color,
            Type=roi_type,
            TissueName=tissue_name,
            RbeCellTypeName=rbe_cell_type_name,
            RoiMaterial=roi_material,
        )
        return True
    except Exception as e:
        logging.warning(f"An error occurred while creating the ROI {roi_name}: {e}")
        return False


def copy_roi(rso, source_roi_name, suffix='', representation='Contours'):
    """
     Try to copy the geometry of an roi
     Args:
         rso:
         source_roi_name:
            suffix: string to append to the new roi name
            representation: 'Contours' 'Voxels' or 'Triangle Mesh'

     Returns:

     """
    copied_roi = unique_roi_name(rso, source_roi_name + suffix)
    roi_created = create_roi(rso, copied_roi, roi_type='Undefined', color="192, 192, 192")
    if not roi_created:
        return None
    # Make copy using algebra
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    try:
        rso.case.PatientModel.RegionsOfInterest[copied_roi].SetAlgebraExpression(
            ExpressionA={
                "Operation": 'Union',
                "SourceRoiNames": [source_roi_name],
                "MarginSettings": margins,
            },
            ExpressionB={'Operation': 'Union',
                         'SourceRoiNames': [],
                         'MarginSettings': margins,
                         },
            ResultOperation='None',
            ResultMarginSettings=margins,
        )
        rso.case.PatientModel.RegionsOfInterest[copied_roi].UpdateDerivedGeometry(
            Examination=rso.exam, Algorithm="Auto"
        )
    except Exception as e:
        logging.warning(f"An error occurred while copying the geometry of {source_roi_name}: {e}")
        return None
    # Delete derived geometry
    try:
        rso.case.PatientModel.RegionsOfInterest[copied_roi].DeleteExpression()
    except Exception as e:
        logging.warning(f"An error occurred while deleting the derived geometry of {copied_roi}: {e}")
        return None
    # Set representation
    try:
        rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[copied_roi]\
            .SetRepresentation(Representation=representation)
    except Exception as e:
        logging.warning(f"An error occurred while setting the representation of {copied_roi}: {e}")
        return None

    return copied_roi
