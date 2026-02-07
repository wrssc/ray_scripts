""" Final Dose

    Script does multiple operations critical to finishing a plan that are often forgotten
    before the plan is locked and export. The functionality is different for treatment
    techniques. Essentially, the critical components are establishing a dose grid,
    establishing dose specification points (DSPs), renaming beams, adding set-up
    fields, and checking parameters within the plan.

    Version History:

    1.0.4 Currently this simply is a wrapper for the rename_beams function. In future versions
        gantry angles, collimator angles, and couch angles may be slightly rounded to create
        an exact match to ARIA.

    1.0.5 Added rounding for jaw positions, MU, checks on overlap of external, dose grid,
        control point spacing, and sim fiducial point

    1.1.0 Added RS10 support and updated to python 3.6

    1.2.0 Update to python 3.8 and RS 3.8

    2.0.0 Added integration of the review script in to replace some of the checks performed in
          FinalDose steps

    2.0.1 Reformatted import of FinalDose to move the launching function to OldPlanReview
    2.0.2 Eliminated jaw rounding and MU rounding since they are default in 2024A
    2.0.3 Updated to version 17 with new compute dose call


    Validation Notes:
    Test Patient:
        -VMAT: Pros_VMA: VMAT Prostate test
        -SNS+emc: ChwL_3DC: 3D photon case with electron boost
        -THI: Anal
        MR# ZZUWQA_ScTest_06Jan2021, Name: Script_testing^Final Dose
    Test Patient: MR# ZZUWQA_ScTest_09Jun2022_FinalDose,
                  Name: Script_testing^Final Dose

    TODO:
        -Move the selection of the machine to the main raystation scripts


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
__date__ = '2025-Jan-30'

__version__ = '2.0.3'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2025-Jan-30'
__raystation__ = '2025'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = None
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'

import logging
import sys
import UserInterface
import BeamOperations
import GeneralOperations
from GeneralOperations import logcrit as logcrit
from PlanOperations import find_beamset
import StructureOperations
import clr
import re

clr.AddReference("System.Xml")
import os
from library.api.api_beamsets import adjust_emc_calculation, compute_beamset_dose
from api.api_ui import ui_click_plan_optimization

sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../library/OldPlanReview'))

# Pattern for a beamset name of form 'XXXX_YYY_R#A#'
_SUFFIX_PATTERN = re.compile(r'^[A-Za-z0-9]{4}_[A-Za-z0-9]{3}_R\d+A\d+$')


def format_prescription_description(element_name, beamset_name):
    return f'{element_name}:{beamset_name}'


def determine_prescription_type(prescription_dose_reference):
    """Determines the prescription type based on the prescription dose reference.

    Args:
        prescription_dose_reference (PrescriptionDoseReference): The prescription dose reference to check.

    Returns:
        str: The prescription type.
    """
    if hasattr(prescription_dose_reference, 'OnStructure'):
        return 'Roi-based', prescription_dose_reference.OnStructure.Name
    elif hasattr(prescription_dose_reference, 'OnDoseSpecificationPoint') and \
            prescription_dose_reference.OnDoseSpecificationPoint is not None:
        return 'Dsp-based', prescription_dose_reference.OnDoseSpecificationPoint.Name
    elif hasattr(prescription_dose_reference, 'PrescriptionType') and \
            prescription_dose_reference.PrescriptionType == 'DoseAtPoint':
        return 'Site-based', prescription_dose_reference.Description
    else:
        return 'Unknown', None


def fix_description_suffix(description: str, beamset_name: str) -> str:
    """Ensure prescription description ends with the current beamset name.

    If `description` contains ':' and the text after the last colon matches
    an old beamset-name pattern (4 chars + '_' + 3 chars + '_R#A#), replace
    that suffix with `beamset_name`. Otherwise, return `description` unchanged.

    Args:
        description: Existing prescription description string.
        beamset_name: Current DicomPlanLabel of the beamset (e.g. 'PROS_VMA_R1A1').

    Returns:
        The corrected description string.
    """
    # Only consider strings containing at least one ':' and longer than beamset_name
    logging.debug(f'Checking description: {description} for beamset name: {beamset_name}')
    if ":" in description and len(description) > len(beamset_name):
        logging.debug(f'Fixing description suffix for {description} with beamset name {beamset_name}')
        head, sep, tail = description.rpartition(":")
        # If the old suffix looks like a beamset name, swap it out
        if _SUFFIX_PATTERN.match(tail):
            logging.debug(f'Replacing old beamset name suffix in description: {tail}')
            return f"{head}{sep}{beamset_name}"
    return f"{description}:{beamset_name}"


def review_target_history(beamset):
    """ Review the target history for this beamset and prior beamsets using this contour's UID
    1. Does it have the same Geometry as any othert beamset's target
    2. Do the dose levels match
    """
    pass


def check_description_unique(patient, proposed_description, adapted=False):
    # Scan the cases to see if this description is already used
    for case in patient.Cases:
        for plan in case.TreatmentPlans:
            for beamset in plan.BeamSets:
                if hasattr(beamset, 'Review') and \
                        hasattr(beamset.Review, 'ApprovalStatus') and \
                        beamset.Review.ApprovalStatus == 'Approved':
                    if hasattr(beamset.Prescription, 'PrescriptionDoseReferences'):
                        prescription_dose_references = beamset.Prescription.PrescriptionDoseReferences
                        for pdr in prescription_dose_references:
                            # TODO: match on first 8 characters of the description, if adapted set to prior ref
                            #       if not, match on the full description
                            if pdr.Description == proposed_description:
                                logging.warning(f'Proposed description {proposed_description} already exists in '
                                                f'beamset {beamset.DicomPlanLabel}')
                                return False
    return True


def set_prescription_description(patient, beamset):
    """Sets the prescription description for the beamset.
    V0. Set Description to <beamset name 13 chars>|D1, |D2, etc...
    V1. Set Description to <beamset name> of primary only
    * Checked:
       - Roi-based prescription types
       - Background dose use

    Args:
        patient (Patient): The RS patient object for the current patient.
        beamset (BeamSet): The beamset to set the prescription description for.
    """
    beamset_name = beamset.DicomPlanLabel

    if hasattr(beamset.Prescription, 'PrimaryPrescriptionDoseReference'):
        prescription_dose_references = [beamset.Prescription.PrimaryPrescriptionDoseReference]
    elif hasattr(beamset.Prescription, 'PrescriptionDoseReferences'):
        prescription_dose_references = [beamset.Prescription.PrescriptionDoseReferences[0]]
    else:
        logging.warning(f'Beamset {beamset_name} does not have any prescription dose references')
        return
    for pdr in prescription_dose_references:
        rx_type, name_of_pdr = determine_prescription_type(pdr)
        logging.info(f'Processing primary prescription dose reference of type: {rx_type} for beamset: {beamset_name},'
                     f' with name: {name_of_pdr}')
        proposed_description = f'{beamset_name}'
        if not check_description_unique(patient, proposed_description):
            raise ValueError('This beamset {beamset_name} name is already defined for this patient in another '
                             f' plan, please revise the beamset name to be unique')
        if rx_type == 'Site-based':
            # Make sure this has not already been named
            pdr.Description = proposed_description  # fix_description_suffix(pdr.Description, beamset_name)
        elif rx_type == 'Unknown':
            logging.warning(
                f'Beamset {beamset_name} has an unknown prescription type for primary dose reference: {pdr}')
            pdr.Description = proposed_description
        else:
            pdr.Description = proposed_description  # format_prescription_description(name_of_pdr, beamset_name)
            logging.debug(f'Description set to {pdr.Description} for beamset {beamset_name}')


def compute_dose(beamset, dose_algorithm):
    # Computes the dose if necessary and returns success message or
    # failure
    try:
        compute_beamset_dose(beamset=beamset, compute_beam_doses=True,
                             dose_algorithm=dose_algorithm, force_recompute=False)
        _ = 'Recomputed Dose, finding DSP'
    except Exception as e:
        logging.debug(f'Message is {e}')
        try:
            if 'Dose has already been computed with the current parameters' in str(e):
                message = 'Dose re-computation unnecessary'
                logging.info(f'Beamset {beamset.DicomPlanLabel} did not need to be recomputed')
            else:
                logging.exception(f'{e}')
                sys.exit(f'{e}')
        except Exception as m:
            logging.exception(f'{m}')
            sys.exit(f'{m}')
        return message


def find_prescription_rois(case, rois=None):
    """
    Finds the rois which are being used for a prescription.
    :param case: (object): The RS case
    :param rois: (list): List of strings containing ROIS already set for inclusion
    :return rois_for_rx: (list): rois + any belonging to an RS prescription
    """
    if rois:
        rois_for_rx = rois
    else:
        rois_for_rx = []
    for tp in case.TreatmentPlans:
        for bs in tp.BeamSets:
            # Search primary prescription
            try:
                roi_name = bs.Prescription.PrimaryPrescriptionDoseReference.OnStructure.Name
                if roi_name not in rois_for_rx:
                    rois_for_rx.append(roi_name)
            except Exception as e:
                logging.debug(f'Reviewing primary prescription type for {bs.DicomPlanLabel} '
                              f'prescription type does not have all attributes for '
                              f'checking structure-dependent prescription '
                              f'error message: {e}')
            try:
                for pdr in bs.Prescription.PrescriptionDoseReferences:
                    roi_name = pdr.OnStructure.Name
                    if roi_name not in rois_for_rx:
                        rois_for_rx.append(roi_name)
            except Exception as e:
                logging.debug(f'Reviewing secondary prescription type for {bs.DicomPlanLabel} '
                              f'prescription type does not have all attributes for '
                              f'checking structure-dependent prescription '
                              f'error message: {e}')

    return rois_for_rx


def process_rois_for_export(plan, case):
    """Exports regions of interest (ROIs) based on specified criteria.

    Args:
        plan (Plan): The RS plan object containing treatment information.
        case (Case): The RS case object containing patient information.

    Testing:
    Validation/Test_Scripting^Rois_For_Export: MR
    """
    # Gather ROIs with a clinical goal
    rois_for_review = [ef.ForRegionOfInterest.Name for ef in plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions]

    # Add GTVs, CTVs, and PTVs
    rois_for_review.extend(StructureOperations.find_types(case, 'Gtv'))
    rois_for_review.extend(StructureOperations.find_types(case, 'Ctv'))
    rois_for_review.extend(StructureOperations.find_types(case, 'Ptv'))

    # Define exclusion reg-ex patterns and exclude them from export
    exclude_patterns = [
        "^OTV", "^sOTV",
        "^opt", "^sPTV",
        "_EZ_", "^ring",
        "_PTV[0-9]", "^Ring",
        "^Normal", "^OAR_PTV",
        "^InnerAir",
        "z_derived", "Uniform",
        "^UnderDose", "Air",
        "FieldOfView", "^PTV[0-9]_Eval", "_junction_",
        r"_iso\d{2}"
    ]
    rois_for_export = []
    for r in rois_for_review:
        if not StructureOperations.any_regex_match(exclude_patterns, r):
            rois_for_export.append(r)

    # Include in export:
    #   * ROIs containing "block" to the export list
    #   * any ROIs labeled Fiducials
    #   * External_PRV10 object used in TBI

    include_patterns = [r'(?i)\b\w*block\w*\b', r'(?i)\b\w*fiducial\w*\b', r'^BONE_IGRT$',
                        r'(?i)\b\w*External_FB\w*\b', r'(?i)\b\w*External_DIBH\w*\b',
                        r'(?i)\b\w*External_PRV10\w*\b', r'(?i)\b\w*Ext_AlignRT_SU\w*\b']
    for r in case.PatientModel.RegionsOfInterest:
        if StructureOperations.any_regex_match(include_patterns, r.Name):
            rois_for_export.append(r.Name)
            logging.debug(f'Including {r.Name} in the export list')

    # Get any rois included in a prescription
    rois_for_export = find_prescription_rois(case, rois_for_export)

    # Add support, external, and bolus structures
    rois_for_export.extend(StructureOperations.find_types(case, 'Bolus'))
    rois_for_export.extend(StructureOperations.find_types(case, 'Support'))
    rois_for_export.extend(StructureOperations.find_types(case, 'Fixation'))
    rois_for_export.extend(StructureOperations.find_types(case, 'External'))

    # Remove duplicates and prepare lists for successful inclusion/exclusion
    rois_for_export = list(set(rois_for_export))
    successful_inclusion = []
    successful_exclusion = []

    # Include or exclude ROIs based on the export list
    for r in case.PatientModel.RegionsOfInterest:
        logging.debug(f'addressing roi {r.Name}')
        if r.Name in rois_for_export:
            StructureOperations.include_in_export(case, [r.Name])
            successful_inclusion.append(r.Name)
        else:
            StructureOperations.exclude_from_export(case, [r.Name])
            successful_exclusion.append(r.Name)

    logging.info(f'For Export Structures Included: {successful_inclusion}')
    logging.debug(f'For Export Structures Excluded: {successful_exclusion}')


def final_dose_v15(site=None, technique=None, rso=None, beamset_name=None):
    """Final Dose
    Args:
        site (str): The site name
        technique (str): The treatment technique
        rso (object): The RS object
        beamset_name (str): The beamset name
    """
    ui = GeneralOperations.find_scope(level='ui')
    # Get current patient, case, exam, and plan
    if not rso:
        patient = GeneralOperations.find_scope(level='Patient')
        case = GeneralOperations.find_scope(level='Case')
        exam = GeneralOperations.find_scope(level='Examination')
        plan = GeneralOperations.find_scope(level='Plan')
        beamset = GeneralOperations.find_scope(level='BeamSet')
    else:
        patient = rso.patient
        case = rso.case
        exam = rso.exam
        plan = rso.plan
        beamset = rso.beamset
    if beamset_name:
        beamset = find_beamset(plan=plan, beamset_name=beamset_name)
        patient.Save()
        beamset.SetCurrent()

    # Change the viewing windows to Plan Optimization
    ui_click_plan_optimization(ui)

    # Institution specific plan names and dose grid settings
    rename_beams = True
    # Let the statements below change as needed
    check_lateral_pa = False
    # Set up the workflow steps.
    steps = ['Exclude irrelevant rois from export',
             'Modify Prescription Description',
             'Rename Beams',
             'Compute Dose if necessary',
             'Set DSP',
             ]
    if 'Tomo' not in beamset.DeliveryTechnique and beamset.Modality != 'Electrons':
        if check_lateral_pa:
            steps.append('Check Laterality')
        steps.append('Recompute Dose')

    status = UserInterface.ScriptStatus(steps=steps,
                                        docstring=__doc__,
                                        help=__help__)
    status.next_step('Checking beam names')

    # Exclude irrelevant rois from export
    process_rois_for_export(plan, case)

    set_prescription_description(patient, beamset)

    if rename_beams:
        # Rename the beams
        BeamOperations.rename_beams(site_name=site, input_technique=technique,
                                    beamset_name=beamset.DicomPlanLabel)
        status.next_step('Renamed Beams, checking external integrity')

    if beamset.Modality == 'Photons':
        dose_algorithm = 'CCDose'
        if 'Tomo' in beamset.DeliveryTechnique:
            # TODO: Better exception handling here.
            message = compute_dose(beamset, dose_algorithm=dose_algorithm)
            status.next_step(message)
            # Set the DSP for the plan and recompute dose to force an update of the DSP
            BeamOperations.set_dsp(plan=plan,
                                   beam_set=beamset)
            BeamOperations.delete_unused_dsps(plan=plan)
            BeamOperations.change_dsp_visualization_diameter(plan=plan)
            compute_beamset_dose(beamset=beamset, compute_beam_doses=True,
                                 dose_algorithm=dose_algorithm,
                                 force_recompute=True)
            status.next_step('DSP set and minimized. Script complete')
        else:
            # Compute dose in case it hasn't been done yet
            _ = compute_beamset_dose(beamset=beamset, dose_algorithm=dose_algorithm)

            status.next_step('Setting DSP')

            # Recompute dose if needed
            _ = compute_beamset_dose(beamset=beamset, dose_algorithm=dose_algorithm)

            # Set the DSP for the plan
            BeamOperations.set_dsp(plan=plan, beam_set=beamset)
            status.next_step('Set DSP, Checking Dose Computation')

            # Recompute dose
            status.next_step('Recomputing Dose if needed')
            # Compute Dose with new DSP, and recommended history settings (mainly to force a DSP update)
            try:
                compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                                     force_recompute=True)
            except Exception as e:
                logging.debug(f' error type is {type(e)}, with e = {e}')
            status.next_step('Script Complete')

    if beamset.Modality == 'Electrons':
        dose_algorithm = 'ElectronMonteCarlo'
        # TODO: Better exception handling here.
        try:
            # Try a quick run
            if not beamset.FractionDose.DoseValues.IsClinical:
                beamset.AccurateDoseAlgorithm.MonteCarloHistoriesPerAreaFluence = 10000
                status.next_step('Computing dose with small number of histories')
                compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                                     force_recompute=False)
        except Exception as e:
            status.next_step('Dose was clinical, no need for recompute')
            logging.info(f'Beamset {beamset.DicomPlanLabel} did not need to be recomputed: {e}')
        # Set the DSP and TODO: add rx surface
        BeamOperations.set_dsp(plan=plan, beam_set=beamset, percent_rx=98., method='Centroid')
        BeamOperations.delete_unused_dsps(plan=plan)
        BeamOperations.change_dsp_visualization_diameter(plan=plan)
        status.next_step('DSP set and minimized, checking statistics')
        mc_histories = 1e6  # RS 11 Cannot exceed 1e6 without long computation times
        # Make sure electron monte carlo statistical uncertainty is clinical
        emc_result = BeamOperations.check_emc(beamset, stat_limit=0.005, histories=mc_histories)
        # If the test returns an insufficient uncertainty, change the number of histories
        if emc_result.ok is False:
            adjust_emc_calculation(beamset, histories=emc_result.hist, uncertainty=0.005)
            compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                                 force_recompute=True)
        # Compute Dose with new DSP, and recommended history settings (mainly to force a DSP update)
        compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                             force_recompute=True)
        status.next_step('Script Complete')

    logcrit('Final Dose Script Run Successfully')


def final_dose_v12(site=None, technique=None, rso=None, beamset_name=None):
    """Final Dose
    Args:
        site (str): The site name
        technique (str): The treatment technique
        rso (object): The RS object
        beamset_name (str): The beamset name
    """
    ui = GeneralOperations.find_scope(level='ui')
    # Get current patient, case, exam, and plan
    if not rso:
        patient = GeneralOperations.find_scope(level='Patient')
        case = GeneralOperations.find_scope(level='Case')
        exam = GeneralOperations.find_scope(level='Examination')
        plan = GeneralOperations.find_scope(level='Plan')
        beamset = GeneralOperations.find_scope(level='BeamSet')
    else:
        patient = rso.patient
        case = rso.case
        exam = rso.exam
        plan = rso.plan
        beamset = rso.beamset
    if beamset_name:
        beamset = find_beamset(plan=plan, beamset_name=beamset_name)
        patient.Save()
        beamset.SetCurrent()

    # Change the viewing windows to Plan Optimization
    ui_click_plan_optimization(ui)

    # Institution specific plan names and dose grid settings
    rename_beams = True
    # Let the statements below change as needed
    # Set up the workflow steps.
    steps = ['Exclude irrelevant rois from export']
    if 'Tomo' not in beamset.DeliveryTechnique and beamset.Modality != 'Electrons':
        steps.append('Rename Beams')
        steps.append('Compute Dose if necessary')
        steps.append('Round MU')
        steps.append('Round Jaws')
        steps.append('Set DSP')
        steps.append('Recompute Dose')

    if 'Tomo' in beamset.DeliveryTechnique:
        steps.append('Rename Beams')
        steps.append('Compute Dose if necessary')
        steps.append('Set DSP')

    if beamset.Modality == 'Electrons':
        steps.append('Rename Beams')
        steps.append('Compute Dose if necessary')
        steps.append('Set DSP')

    status = UserInterface.ScriptStatus(steps=steps,
                                        docstring=__doc__,
                                        help=__help__)
    status.next_step('Checking beam names')

    # Exclude irrelevant rois from export
    process_rois_for_export(plan, case)

    if rename_beams:
        # Rename the beams
        BeamOperations.rename_beams(site_name=site, input_technique=technique,
                                    beamset_name=beamset.DicomPlanLabel)
        status.next_step('Renamed Beams, checking dose recomputation')

    if beamset.Modality == 'Photons':
        dose_algorithm = 'CCDose'
        if 'Tomo' in beamset.DeliveryTechnique:
            # TODO: Better exception handling here.
            message = compute_dose(beamset, dose_algorithm=dose_algorithm)
            status.next_step(message)
            # Set the DSP for the plan and recompute dose to force an update of the DSP
            BeamOperations.set_dsp(plan=plan,
                                   beam_set=beamset)
            compute_beamset_dose(beamset=beamset, compute_beam_doses=True,
                                 dose_algorithm=dose_algorithm,
                                 force_recompute=True)
            status.next_step('DSP set. Script complete')
        else:
            # Compute dose in case it hasn't been done yet
            _ = compute_dose(beamset=beamset, dose_algorithm=dose_algorithm)

            # Round MU
            beamset.SetAutoScaleToPrimaryPrescription(AutoScale=False)
            BeamOperations.round_mu(beamset)
            status.next_step('Rounded MU, Rounding jaws')

            # Round jaws to nearest mm
            logging.debug('Checking for jaw rounding')
            BeamOperations.round_jaws(beamset=beamset)
            status.next_step('Setting DSP')

            # Recompute dose if needed
            _ = compute_dose(beamset=beamset, dose_algorithm=dose_algorithm)

            # Set the DSP for the plan
            BeamOperations.set_dsp(plan=plan, beam_set=beamset)
            status.next_step('Set DSP, Checking Dose Computation')

            # Recompute dose
            status.next_step('Recomputing Dose if needed')
            # Compute Dose with new DSP, and recommended history settings (mainly to force a DSP update)
            try:
                compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                                     force_recompute=True)
            except Exception as e:
                logging.debug(f' error type is {type(e)}, with e = {e}')
            status.next_step('Script Complete')

    if beamset.Modality == 'Electrons':
        dose_algorithm = 'ElectronMonteCarlo'
        # TODO: Better exception handling here.
        try:
            # Try a quick run
            if not beamset.FractionDose.DoseValues.IsClinical:
                beamset.AccurateDoseAlgorithm.MonteCarloHistoriesPerAreaFluence = 10000
                status.next_step('Computing dose with small number of histories')
                compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                                     force_recompute=False)
        except Exception as e:
            status.next_step('Dose was clinical, no need for recompute')
            logging.info(f'Beamset {beamset.DicomPlanLabel} did not need to be recomputed: {e}')
        # Set the DSP and TODO: add rx surface
        BeamOperations.set_dsp(plan=plan, beam_set=beamset, percent_rx=98., method='Centroid')
        status.next_step('DSP set, checking statistics')
        mc_histories = 1e6  # RS 11 Cannot exceed 1e6 without long computation times
        # Make sure electron monte carlo statistical uncertainty is clinical
        emc_result = BeamOperations.check_emc(beamset, stat_limit=0.005, histories=mc_histories)
        # If the test returns an insufficient uncertainty, change the number of histories
        if emc_result.ok is False:
            adjust_emc_calculation(beamset, histories=emc_result.hist, uncertainty=0.005)
            compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                                 force_recompute=True)
        # Autoscale must be turned off to round the MU.
        # Round MU
        beamset.SetAutoScaleToPrimaryPrescription(AutoScale=False)
        BeamOperations.round_mu(beamset)
        status.next_step('Rounded MU, recomputing doses')
        # Compute Dose with new DSP, and recommended history settings (mainly to force a DSP update)
        compute_beamset_dose(beamset=beamset, compute_beam_doses=True, dose_algorithm=dose_algorithm,
                             force_recompute=True)
        status.next_step('Script Complete')

    logcrit('Final Dose Script Run Successfully')
