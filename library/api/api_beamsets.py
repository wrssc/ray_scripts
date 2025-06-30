from library.api.dispatcher import APIDispatcher

dispatcher = APIDispatcher()  # Create an instance of the dispatcher


#
# Beamset and Plan UID calls
def get_unique_id_beamset_v12(beamset):
    # Version 12 specific code
    if beamset:
        return beamset.UniqueId
    else:
        return None


def get_unique_id_beamset_v15(beamset):
    # Version 15 specific code - use the DICOM UID
    if beamset:
        return beamset.GetRadiationSetUuid()
    else:
        return None


def get_unique_id_plan_v12(plan):
    # Version 12 specific code
    if plan:
        return plan.UniqueId
    else:
        return None


def get_unique_id_plan_v15(plan):
    # Version 15 specific code - use the DICOM UID
    if plan:
        return plan.GetPlanUuid()
    else:
        return None


# Treat and Protect ROI functions
def set_treat_or_protect_roi_all_beams_v12(beamset, roi_name):
    # Version 12 specific code
    beamset.SelectToUseROIasTreatOrProtectForAllBeams(RoiName=roi_name)


def set_treat_or_protect_roi_all_beams_v15(beamset, roi_name):
    # Version 15 specific code
    beamset.SetTreatOrProtectRoiAllBeams(RoiName=roi_name)


def set_treat_or_protect_margins_v12(beam, roi_name, margins):
    # Version 12 specific code
    beam.SetTreatAndProtectMarginsForBeam(
        TopMargin=margins['Y2'],
        BottomMargin=margins['Y1'],
        LeftMargin=margins['X1'],
        RightMargin=margins['X2'],
        Roi=roi_name
    )


def set_treat_or_protect_margins_v15(beam, roi_name, margins):
    # Version 15 specific code
    beam.SetTreatOrProtectRoi(
        TopMargin=margins['Y2'],
        BottomMargin=margins['Y1'],
        LeftMargin=margins['X1'],
        RightMargin=margins['X2'],
        RoiName=roi_name
    )


# Source to Surface Distance functions
def get_source_to_surface_distance_v12(beam):
    # Version 12 specific code
    return beam.GetSSD()


def get_source_to_surface_distance_v15(beam):
    # Version 15 specific code
    return beam.GetSourceToSurfaceDistance()


# Dose Prescription to ROI functions
def add_dose_prescription_to_roi_v11(beamset, roi_name, dose_volume, prescription_type,
                                     dose_value, relative_dose_prescription_value,
                                     auto_scale_dose=False):
    # Version for RS Version 10
    beamset.AddDosePrescriptionToRoi(RoiName=roi_name,
                                     DoseVolume=dose_volume,
                                     PrescriptionType=prescription_type,
                                     DoseValue=dose_value,
                                     RelativePrescriptionLevel=relative_dose_prescription_value,
                                     AutoScaleDose=auto_scale_dose)


def add_dose_prescription_to_roi_v12(beamset, roi_name, dose_volume, prescription_type,
                                     dose_value, relative_dose_prescription_value,
                                     auto_scale_dose=False):
    beamset.AddRoiPrescriptionDoseReference(RoiName=roi_name,
                                            DoseVolume=dose_volume,
                                            PrescriptionType=prescription_type,
                                            DoseValue=dose_value,
                                            RelativePrescriptionLevel=relative_dose_prescription_value)


def add_dose_prescription_to_roi_v15(beamset, roi_name, dose_volume, prescription_type,
                                     dose_value, relative_dose_prescription_value,
                                     auto_scale_dose=False):
    beamset.AddRoiPrescriptionDoseReference(RoiName=roi_name,
                                            DoseVolume=dose_volume,
                                            PrescriptionType=prescription_type,
                                            DoseValue=dose_value,
                                            RelativePrescriptionLevel=relative_dose_prescription_value)


def get_number_of_emc_histories_v12(beamset):
    return beamset.FractionDose.DoseValues.AlgorithmProperties.MonteCarloHistoriesPerAreaFluence


def get_number_of_emc_histories_v15(beamset):
    return beamset.FractionDose.DoseValues.MCTotalNumberOfHistories


def adjust_emc_calculation_v12(beamset, histories=1e6, uncertainty=0.005):
    beamset.AccurateDoseAlgorithm.MonteCarloHistoriesPerAreaFluence = histories


def adjust_emc_calculation_v15(beamset, histories=1e6, uncertainty=0.005):
    beamset.AccurateDoseAlgorithm.MCStatisticalUncertaintyForFinalDose = uncertainty


def create_electron_qa_plan_v12(beamset, phantom_name, phantom_id, qa_plan_name,
                                isocenter, dose_grid, gantry_angle,
                                collimator_angle, couch_rotation_angle,
                                compute_dose, number_histories, uncertainty):
    # Version 12 specific code to create an electron QA plan
    beamset.CreateQAPlan(
        PhantomName=phantom_name,
        PhantomId=phantom_id,
        QAPlanName=qa_plan_name,
        IsoCenter=isocenter,
        DoseGrid=dose_grid,
        GantryAngle=gantry_angle,
        CollimatorAngle=collimator_angle,
        CouchRotationAngle=couch_rotation_angle,
        ComputeDoseWhenPlanIsCreated=compute_dose,
        NumberOfMonteCarloHistories=number_histories)


def create_electron_qa_plan_v15(beamset, phantom_name, phantom_id, qa_plan_name,
                                isocenter, dose_grid, gantry_angle,
                                collimator_angle, couch_rotation_angle,
                                compute_dose, number_histories, uncertainty):
    # Version 15 specific code to create an electron QA plan
    beamset.CreateQAPlan(
        PhantomName=phantom_name,
        PhantomId=phantom_id,
        QAPlanName=qa_plan_name,
        IsoCenter=isocenter,
        DoseGrid=dose_grid,
        GantryAngle=gantry_angle,
        CollimatorAngle=collimator_angle,
        CouchRotationAngle=couch_rotation_angle,
        ComputeDoseWhenPlanIsCreated=compute_dose,
        DesiredStatisticalUncertaintyForElectrons=uncertainty
    )


# Register these functions with the dispatcher
dispatcher.register('get_unique_id_beamset', 12, get_unique_id_beamset_v12)
dispatcher.register('get_unique_id_beamset', 15, get_unique_id_beamset_v15)

dispatcher.register('get_unique_id_plan', 12, get_unique_id_plan_v12)
dispatcher.register('get_unique_id_plan', 15, get_unique_id_plan_v15)

dispatcher.register('set_treat_or_protect_roi_all_beams', 12, set_treat_or_protect_roi_all_beams_v12)
dispatcher.register('set_treat_or_protect_roi_all_beams', 15, set_treat_or_protect_roi_all_beams_v15)

dispatcher.register('set_treat_or_protect_margins', 12, set_treat_or_protect_margins_v12)
dispatcher.register('set_treat_or_protect_margins', 15, set_treat_or_protect_margins_v15)

dispatcher.register('get_source_to_surface_distance', 12, get_source_to_surface_distance_v12)
dispatcher.register('get_source_to_surface_distance', 15, get_source_to_surface_distance_v15)

dispatcher.register('add_dose_prescription_to_roi', 11, add_dose_prescription_to_roi_v11)
dispatcher.register('add_dose_prescription_to_roi', 12, add_dose_prescription_to_roi_v12)
dispatcher.register('add_dose_prescription_to_roi', 15, add_dose_prescription_to_roi_v15)

dispatcher.register('get_number_of_emc_histories', 12, get_number_of_emc_histories_v12)
dispatcher.register('get_number_of_emc_histories', 15, get_number_of_emc_histories_v15)

dispatcher.register('adjust_emc_calculation', 12, adjust_emc_calculation_v12)
dispatcher.register('adjust_emc_calculation', 15, adjust_emc_calculation_v15)

dispatcher.register('create_electron_qa_plan', 12, create_electron_qa_plan_v12)
dispatcher.register('create_electron_qa_plan', 15, create_electron_qa_plan_v15)


@dispatcher.dispatch('get_unique_id_beamset')
def get_unique_id_beamset(beamset):
    pass


@dispatcher.dispatch('get_unique_id_plan')
def get_unique_id_plan(plan):
    pass


@dispatcher.dispatch('set_treat_or_protect_roi_all_beams')
def set_treat_or_protect_roi_all_beams(beamset, roi_name):
    pass


@dispatcher.dispatch('set_treat_or_protect_margins')
def set_treat_or_protect_margins(beam, roi_name, margins):
    pass


@dispatcher.dispatch('get_source_to_surface_distance')
def get_source_to_surface_distance(beam):
    pass


@dispatcher.dispatch('add_dose_prescription_to_roi')
def add_dose_prescription_to_roi(beamset, roi_name, dose_volume, prescription_type,
                                 dose_value, relative_dose_prescription_value,
                                 auto_scale_dose=False):
    pass


@dispatcher.dispatch('get_number_of_emc_histories')
def get_number_of_emc_histories(beamset):
    pass


@dispatcher.dispatch('adjust_emc_calculation')
def adjust_emc_calculation(beamset, histories=1e6, uncertainty=0.005):
    pass


@dispatcher.dispatch('create_electron_qa_plan')
def create_electron_qa_plan(beamset, phantom_name, phantom_id, qa_plan_name,
                            isocenter, dose_grid, gantry_angle,
                            collimator_angle, couch_rotation_angle,
                            compute_dose, number_histories, uncertainty):
    pass
