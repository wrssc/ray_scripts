from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def get_source_to_surface_distance_v12(beam):
    # Version 12 specific code
    return beam.GetSSD()


def get_source_to_surface_distance_v15(beam):
    # Version 15 specific code
    return beam.GetSourceToSurfaceDistance()


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
    beamset.AddDosePrescriptionToRoi(RoiName=roi_name,
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

# Version for RS Version 10


# Register these functions with the dispatcher
dispatcher.register('get_source_to_surface_distance', 12, get_source_to_surface_distance_v12)
dispatcher.register('get_source_to_surface_distance', 15, get_source_to_surface_distance_v15)

dispatcher.register('add_dose_prescription_to_roi', 11, add_dose_prescription_to_roi_v11)
dispatcher.register('add_dose_prescription_to_roi', 12, add_dose_prescription_to_roi_v12)
dispatcher.register('add_dose_prescription_to_roi', 15, add_dose_prescription_to_roi_v15)


@dispatcher.dispatch('get_source_to_surface_distance')
def get_source_to_surface_distance(beam):
    pass


@dispatcher.dispatch('add_dose_prescription_to_roi')
def add_dose_prescription_to_roi(beamset, roi_name, dose_volume, prescription_type,
                                 dose_value, relative_dose_prescription_value,
                                 auto_scale_dose=False):
    pass