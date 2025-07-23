# Make a new plan and FFS transfer
import logging
import connect
import library.AutoPlanOperations as AutoPlanOperations
from .tbi_utils import determine_prefix
from .tbi_definitions import (
    PROTOCOL_NAME_TOMO, ORDER_NAME_FFS_TOMO, ORDER_NAME_HFS_TOMO, ORDER_NAME_HFS_KIDNEY_TOMO,
    BEAMSET_TEMPLATE_FFS_TOMO, BEAMSET_TEMPLATE_HFS_TOMO, TOMO_MACHINE, PROTOCOL_NAME_VMAT,
    HFS_PELVIS_ORDER_NAME, HFS_PELVIS_KIDNEY_ORDER_NAME, HFS_CHEST_ORDER_NAME, HFS_HEAD_ORDER_NAME,
    FFS_PELVIS_ORDER_NAME, FFS_LEGS_ORDER_NAME, FFS_FEET_ORDER_NAME, ORDER_TARGET_NAME_FFS,
    ORDER_TARGET_NAME_HFS, HFS_TOMO_PLAN_NAME, HFS_TOMO_BEAMSET_NAME, FFS_TOMO_BEAMSET_NAME,
    FFS_TOMO_PLAN_NAME, TOMO_FFS_TRANSFER_NAME, HFS_VMAT_BEAMSET_NAME, HFS_VMAT_PLAN_NAME,
    FFS_VMAT_BEAMSET_NAME, FFS_VMAT_PLAN_NAME, VMAT_FFS_TRANSFER_NAME, VMAT_MACHINE, TARGET_HFS,
    TARGET_FFS, HFS_TARGET_EVAL_NAME, FFS_TARGET_EVAL_NAME
)


def tomo_calc_iso(patient_data: object, target: str) -> str:
    """
    Creates a fiducial point (SimFiducial) if it does not exist, prompts the user to place it, calculates the coordinates of an isocenter, and creates an ROI at that location.

    Args:
        patient_data (object): RayStation object with .case and .exam attributes.
        target (str): Name of the target ROI.

    Returns:
        str: Name of the created isocenter ROI.
    """

    fiducial_point_name = 'SimFiducials'

    # Check if fiducials exist and are defined
    point_exists, point_defined = check_fiducials(
        patient_data, fiducial_name=fiducial_point_name)

    if not point_exists:
        # If fiducial point doesn't exist, create one
        AutoPlanOperations.place_fiducial(
            rso=patient_data, poi_name='SimFiducials')

        # Prompt the user to place the fiducial point in both FFS and HFS
        connect.await_user_input(
            'Place SimFiducial point in FFS, then toggle to HFS and place it '
            'there too')
        point_exists, point_defined = check_fiducials(
            patient_data, fiducial_name=fiducial_point_name)
    elif not point_defined:
        # If fiducial point exists but is not defined, prompt the user to
        # define it
        connect.await_user_input(
            'Place SimFiducial point in FFS, then toggle to HFS and place it '
            'there too')

    pm = patient_data.case.PatientModel

    # Retrieve the coordinates of the fiducial point and the center of the
    # target ROI
    sim_coordinates = pm.StructureSets[patient_data.exam.Name] \
        .LocalizationPoiGeometry.Point
    target_coordinates = pm.StructureSets[patient_data.exam.Name] \
        .RoiGeometries[target].GetCenterOfRoi()

    # Define isocenter coordinates
    iso_coord = {
        'x': 0., 'y': target_coordinates['y'], 'z': sim_coordinates['z']}

    # Get prefix
    prefix = determine_prefix(patient_data.exam)

    # Create a unique name for the new ROI
    iso_name = pm.GetUniqueRoiName(
        DesiredName=f'{prefix}_iso')

    # Create new ROI at the isocenter
    pm.CreateRoi(Name=iso_name,
                 Color='Pink',
                 Type='Control')
    iso_roi = pm.RegionsOfInterest[iso_name]

    # Define the geometry of the new ROI as a small sphere at the isocenter
    iso_roi.CreateSphereGeometry(Radius=1.0,
                                 Examination=patient_data.exam,
                                 Center=iso_coord,
                                 Representation='Voxels',
                                 VoxelSize=0.01)

    return iso_name


def get_tomo_plan_defs(rso: object, target: str, nfx: int, rx: int, optimize: bool = False,
                       kidney_sparing: bool = False) -> dict:
    """
    Generates a protocol dictionary for Tomo TBI planning based on patient orientation and options.

    Args:
        rso (object): RayStation object with .case and .exam attributes.
        target (str): Name of the target ROI.
        nfx (int): Number of fractions.
        rx (int): Radiation dose.
        optimize (bool, optional): Whether to optimize. Defaults to False.
        kidney_sparing (bool, optional): Whether to use kidney sparing protocol. Defaults to False.

    Returns:
        dict: Protocol dictionary for Tomo TBI planning.
    """
    iso_target = tomo_calc_iso(rso, target=target)
    protocol = {
        'protocol_name': PROTOCOL_NAME_TOMO,
        'planning_strategy': 'Sequential',
        'num_fx': nfx,
        'site': 'TBI_',
        'machine': TOMO_MACHINE,
        'iso': {'type': 'ROI', 'target': iso_target},
        'optimize': optimize,
        'user_prompts': False,
        'rso': None,
    }

    if rso.exam.PatientPosition == 'HFS':
        # HFS protocol declarations
        protocol['translation_map'] = {ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')}
        protocol['order_name'] = ORDER_NAME_HFS_KIDNEY_TOMO if kidney_sparing else ORDER_NAME_HFS_TOMO
        protocol['plan_name'] = HFS_TOMO_PLAN_NAME
        protocol['beamset_name'] = HFS_TOMO_BEAMSET_NAME
        protocol['beamset_template'] = BEAMSET_TEMPLATE_HFS_TOMO
        protocol['optimization_instructions'] = {'optimize_with': None,
                                                 'optimize_with_background': TOMO_FFS_TRANSFER_NAME,
                                                 'lock_dose_grid': True}
    elif rso.exam.PatientPosition == 'FFS':
        # FFS protocol declarations
        protocol['translation_map'] = {ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')}
        protocol['order_name'] = ORDER_NAME_FFS_TOMO
        protocol['plan_name'] = FFS_TOMO_PLAN_NAME
        protocol['beamset_name'] = FFS_TOMO_BEAMSET_NAME
        protocol['beamset_template'] = BEAMSET_TEMPLATE_FFS_TOMO
        protocol['optimization_instructions'] = {'optimize_with': None,
                                                 'optimize_with_background': None,
                                                 'lock_dose_grid': True}
    return protocol


def get_vmat_plan_defs(rso: object, hfs_pois: list, ffs_pois: list, nfx: int, rx: int, optimize: bool = False,
                       kidney_sparing: bool = False) -> tuple:
    """
    Generates data dictionaries for multiple VMAT plan treatments.

    Args:
        rso (object): RayStation object with .case and .exam attributes.
        hfs_pois (list): List of HFS (Head-First Supine) Points of Interest (POIs).
        ffs_pois (list): List of FFS (Feet-First Supine) POIs.
        nfx (int): Number of fractions.
        rx (int): Radiation dose.
        optimize (bool, optional): If True, optimization should be performed. Defaults to False.
        kidney_sparing (bool, optional): If True, kidney sparing is enabled. Defaults to False.

    Returns:
        tuple: Two lists of dictionaries, hfs_dict and ffs_dict, for HFS and FFS plans respectively.
    """
    # Define the structure sets for various numbers of isocenters
    hfs_data = {
        5: [
            'TBI_HFS_5Pelv',
            'TBI_HFS_4AbdI',
            'TBI_HFS_3AbdS',
            'TBI_HFS_2Chst',
            'TBI_HFS_1Head',
        ],
        4: [
            'TBI_HFS_4Pelv',
            'TBI_HFS_3Abdo',
            'TBI_HFS_2Chst',
            'TBI_HFS_1Head',
        ],
        3: [
            'TBI_HFS_3Pelv',
            'TBI_HFS_2Chst',
            'TBI_HFS_1Head',
        ],
        2: [
            'TBI_HFS_2Pelv',
            'TBI_HFS_1Head',
        ],
        1: [
            'TBI_HFS_1Pelv'],
        0: ['']}
    offset = len(hfs_pois)
    ffs_data = {
        5: [
            f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}LegS',
            f'TBI_FFS_{offset + 3}LegI',
            f'TBI_FFS_{offset + 4}Knee',
            f'TBI_FFS_{offset + 5}Feet'],
        4: [f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}LegS',
            f'TBI_FFS_{offset + 3}LegI',
            f'TBI_FFS_{offset + 4}Feet'],
        3: [
            f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}Legs',
            f'TBI_FFS_{offset + 3}Feet', ],
        2: [
            f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}Feet', ],
        1: [
            f'TBI_FFS_{offset + 1}Pelv',
        ],
        0: ['']
    }
    # Select beamset names depending on the number of POIs
    hfs_beamset_names, ffs_beamset_names = hfs_data[len(hfs_pois)], ffs_data[len(ffs_pois)]

    def create_translation_map(i: int, total_points: int, j_range: range, site: str, rx: int, offset: int) -> dict:
        """
            Creates a translation map for the given site and point in the range.

            Args:
                i (int): Current point index.
                total_points (int): Total number of points.
                j_range (range): Range object.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                rx (int): Radiation dose in rx.
                offset (int): Offset value.

            Returns:
                dict: Translation map:
                    'ROI Name in xml': ('Plan ROI Name, Dose, Dose units', e.g.
                    'OTV_iso':('OTV_iso1',800,'cGy')
            """
        if site == 'HFS_':
            prefix = 'hfs'
            translation_map = {HFS_TARGET_EVAL_NAME: (f'{HFS_TARGET_EVAL_NAME}', rx, r'cGy')}
        else:
            prefix = 'ffs'
            translation_map = {FFS_TARGET_EVAL_NAME: (f'{FFS_TARGET_EVAL_NAME}', rx, r'cGy')}
        for j in j_range:
            # Set the sup_value and inf_value keys for each point
            sup_key = f'Sup_{j}'
            inf_key = f'Inf_{j}'
            sup_value = (f'{prefix}_iso{offset + i}{offset + i + 1}_junction_{j}', rx, r'cGy')
            inf_value = (f'{prefix}_iso{offset + i + 1}{offset + i + 2}_junction_{j}', rx, r'cGy')

            # Assign the sup_value and inf_value to the translation_map
            if i == 0 or i == total_points - 1:
                key = inf_key if i == 0 else sup_key
                value = inf_value if i == 0 else sup_value
                translation_map[key] = value
            else:  # Middle points
                translation_map[sup_key] = sup_value
                translation_map[inf_key] = inf_value
            # Set the OTV mapping
            translation_map['OTV_iso'] = (f'OTV_iso{i + offset + 1}', rx, r'cGy')

        return translation_map

    def create_optimization_instructions(i: int, pois: list, site: str, prior_beamset_name: str) -> dict:
        """
            Creates optimization instructions for a given site.

            Args:
                i (int): Current index.
                pois (list): List of Points of Interest.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                prior_beamset_name (str): Name of the prior beamset that was optimized.

            Returns:
                dict: Optimization instructions.
            """
        optimization_instructions = {'optimize_with': None, 'lock_dose_grid': True}
        if site == 'HFS_':
            optimization_instructions['order'] = len(pois) - i
            optimization_instructions['optimize_with_background'] = VMAT_FFS_TRANSFER_NAME
        return optimization_instructions

    def get_xml_config(patient_position: str, n_pts: int) -> dict:
        if kidney_sparing:
            pelvis_order_name = HFS_PELVIS_KIDNEY_ORDER_NAME
        else:
            pelvis_order_name = HFS_PELVIS_ORDER_NAME
        HFS_5ISO_XML_CONFIG = {0: (pelvis_order_name, 'TBI_HFS_5Pelv'),
                               1: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_4AbdI'),
                               2: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_3AbdS'),
                               3: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_2Chst'),
                               4: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_5ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_6Pelv'),
                               1: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_7LegS'),
                               2: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_8LegI'),
                               3: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_9Knee'),
                               4: (FFS_FEET_ORDER_NAME, 'TBI_FFS_10Feet')}
        HFS_4ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_4Pelv'),
                               1: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_3Abdo'),
                               2: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_2Chst'),
                               3: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_4ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_5Pelv'),
                               1: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_6LegS'),
                               2: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_7LegI'),
                               3: (FFS_FEET_ORDER_NAME, 'TBI_FFS_8Feet')}
        HFS_3ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_3Pelv'),
                               1: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_2Chst'),
                               2: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_3ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_4Pelv'),
                               1: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_5Leg'),
                               2: (FFS_FEET_ORDER_NAME, 'TBI_FFS_6Feet')}
        HFS_2ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_2Pelv'),
                               1: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_2ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_3Pelv'),
                               1: (FFS_FEET_ORDER_NAME, 'TBI_FFS_4Feet')}
        HFS_1ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_1ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_2Pelv')}
        HFS_XML_CONFIG = {5: HFS_5ISO_XML_CONFIG,
                          4: HFS_4ISO_XML_CONFIG,
                          3: HFS_3ISO_XML_CONFIG,
                          2: HFS_2ISO_XML_CONFIG,
                          1: HFS_1ISO_XML_CONFIG}
        FFS_XML_CONFIG = {5: FFS_5ISO_XML_CONFIG,
                          4: FFS_4ISO_XML_CONFIG,
                          3: FFS_3ISO_XML_CONFIG,
                          2: FFS_2ISO_XML_CONFIG,
                          1: FFS_1ISO_XML_CONFIG}
        if patient_position == 'HFS':
            return HFS_XML_CONFIG[n_pts]
        else:
            return FFS_XML_CONFIG[n_pts]

    def create_dict(pois: list, beamset_names: list,
                    site: str, order_target_name: str, target: str, name_offset: int = 0) -> list:
        """
            Creates a dictionary of plan parameters.

            Args:
                pois (list): List of Points of Interest.
                beamset_names (list): List of beamset names.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                order_target_name (str): Name of the target for order.
                target (str): Target name.
                name_offset (int, optional): Offset value. Defaults to 0.

            Returns:
                list: List of dictionaries, each representing a plan.
        """
        dictionary = []
        prior_beamset_name = ""
        for i, n in enumerate(beamset_names):
            # Provide a range of potential number of beamsets. Max is 10
            j_range = range(1, 10, 1)
            # Based on its position in the POI list set the TPO for goals/objectives, and assign a beamset
            # template
            # USing the XML templates defined aboue determine the correct template based on the
            # number of pois and the length of the keys
            n_pts = len(pois)
            if site == "HFS_":
                target_poi = pois[len(pois) - 1 - i]
                xml_config = get_xml_config('HFS', n_pts)
                order_name = xml_config[i][0]
                template = xml_config[i][1]
                logging.debug(f'Order name is {order_name} and template is {template}')
                translation_map = create_translation_map(
                    len(pois) - 1 - i, len(pois), j_range, site, rx, name_offset)
                exam_name = "HFS"
            else:
                target_poi = pois[i]
                xml_config = get_xml_config('FFS', n_pts)
                order_name = xml_config[i][0]
                template = xml_config[i][1]
                logging.debug(f'Order name is {order_name} and template is {template}')
                translation_map = create_translation_map(i, len(pois), j_range, site, rx, name_offset)
                exam_name = "FFS"
            optimization_instructions = create_optimization_instructions(i, pois, site,
                                                                         prior_beamset_name)
            dictionary.append({
                'protocol_name': PROTOCOL_NAME_VMAT,
                'translation_map': {order_target_name: (target, rx, r'cGy'), **translation_map},
                'order_name': order_name,
                'exam': exam_name,
                'planning_strategy': 'Sequential',
                'optimization_instructions': optimization_instructions,
                'num_fx': nfx,
                'site': site,
                'plan_name': HFS_VMAT_PLAN_NAME if site == 'HFS_' else FFS_VMAT_PLAN_NAME,
                'beamset_name': HFS_VMAT_BEAMSET_NAME if site == 'HFS_' else FFS_VMAT_BEAMSET_NAME,
                'machine': VMAT_MACHINE,
                'beamset_template': template,
                'beamset_exists_skip': beamset_exists(rso, n),
                'multi_isocenter': True,
                'iso': {'type': 'POI', 'target': target_poi},
                'optimize': optimize,
                'user_prompts': True if i == 0 else False,
            })
            prior_beamset_name = n
        return dictionary

    hfs_dict = create_dict(pois=hfs_pois,
                           beamset_names=hfs_beamset_names,
                           site='HFS_',
                           order_target_name=ORDER_TARGET_NAME_HFS,
                           target=TARGET_HFS)
    ffs_dict = create_dict(pois=ffs_pois,
                           beamset_names=ffs_beamset_names,
                           site='FFS_',
                           order_target_name=ORDER_TARGET_NAME_FFS,
                           target=TARGET_FFS,
                           name_offset=len(hfs_pois))

    return hfs_dict, ffs_dict


def beamset_exists(rso: object, beamset_name: str) -> bool:
    """
    Checks if a beamset exists for the given RayStation object.

    Args:
        rso (object): RayStation object with .case attribute.
        beamset_name (str): Name of the beamset to check.

    Returns:
        bool: True if the beamset exists, False otherwise.
    """
    if get_beamset(rso, beamset_name) is None:
        return False
    else:
        return True


def get_beamset(rso: object, beamset_name: str) -> object:
    """
    Retrieves a beamset by name for the given RayStation object.

    Args:
        rso (object): RayStation object with .case attribute.
        beamset_name (str): Name of the beamset to retrieve.

    Returns:
        object: The beamset if it exists, None otherwise.
    """
    beamset = next(
        (bs for plan in rso.case.TreatmentPlans for bs in plan.BeamSets
         if bs.DicomPlanLabel == beamset_name), None
    )
    return beamset


def beamset_has_valid_segments(rso: object, beamset_name: str) -> bool:
    """
    Checks if a beamset has valid segments for the given RayStation object.

    Args:
        rso (object): RayStation object with .case attribute.
        beamset_name (str): Name of the beamset to check.

    Returns:
        bool: True if the beamset has valid segments, False otherwise.
    """
    beamset = get_beamset(rso, beamset_name)
    if not beamset:
        return False

    has_valid_segments = all(
        b.BeamMU > 0 and (b.DeliveryTechnique == 'TomoHelical' or b.HasValidSegments)
        for b in beamset.Beams
    )
    return has_valid_segments


def beamset_has_dose(rso: object, beamset_name: str) -> bool:
    """
    Checks if a beamset has dose values for the given RayStation object.

    Args:
        rso (object): RayStation object with .case attribute.
        beamset_name (str): Name of the beamset to check.

    Returns:
        bool: True if the beamset has dose values, False otherwise.
    """
    beamset = get_beamset(rso, beamset_name)
    if not beamset:
        return False
    return beamset.FractionDose.DoseValues is not None


def beamset_complete(rso: object, beamset_name: str) -> tuple:
    """
    Checks if a beamset is complete for the given RayStation object.

    Args:
        rso (object): RayStation object with .case attribute.
        beamset_name (str): Name of the beamset to check.

    Returns:
        tuple: (beamset_present: bool, does the beamset exist with the name mathing beamset_name,
                beamset_has_valid_segments: bool, does the beamset have valid segments,
                beamset_has_dose: bool, does the beamset have dose values).

    """
    # Mark that the beamset exists.
    present = beamset_exists(rso, beamset_name)

    # Validate each beam: Must have BeamMU > 0 and either be 'TomoHelical' or have valid segments.
    has_valid_segments = beamset_has_valid_segments(rso, beamset_name)

    # Check that the beamset has dose values.
    has_dose = beamset_has_dose(rso, beamset_name)

    return present, has_valid_segments, has_dose


def check_fiducials(pd: object, fiducial_name: str) -> tuple:
    """
    Checks if a fiducial point exists and is defined in all potential exams.

    Args:
        pd (object): RayStation object with .case attribute.
        fiducial_name (str): Name of the fiducial point to check.

    Returns:
        tuple: (point_exists, point_defined) where each is a bool.
    """
    # Accessing pd.case (RayStation dynamic attribute)
    # Check all potential exams to ensure the fiducial is defined
    fiducial_check = []
    pois = [p.Name for p in pd.case.PatientModel.PointsOfInterest]
    if fiducial_name not in pois:
        return False, False
    for ss in pd.case.PatientModel.StructureSets:
        if not ss.PoiGeometries[fiducial_name].Point:
            fiducial_check.append(False)
        else:
            fiducial_check.append(True)
    return True, all(fiducial_check)
