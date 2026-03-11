from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def get_rigid_registrations_v12(case):
    # Version 12 specific code
    return case.Registrations


def get_rigid_registrations_v15(case):
    # Version 15 specific code
    return case.RigidRegistrations


def compute_gray_level_based_rigid_registration_v15(
        case,
        floating_examination,
        reference_examination,
        use_only_translation,
        high_weight_on_bones,
        initialize_images,
        focus_rois_names,
        registration_name,
        focus_volume_of_interest
):

    if focus_volume_of_interest is not None:
        raise ValueError("FocusVolumeOfInterest parameter is not supported in RayStation 15 or earlier.")
    case.ComputeGrayLevelBasedRigidRegistration(
        FloatingExaminationName=floating_examination.Name,
        ReferenceExaminationName=reference_examination.Name,
        UseOnlyTranslations=use_only_translation,
        HighWeightOnBones=high_weight_on_bones,
        InitializeImages=initialize_images,
        FocusRoisNames=focus_rois_names,
        RegistrationName=registration_name)


def compute_gray_level_based_rigid_registration_v17(
        case,
        floating_examination,
        reference_examination,
        use_only_translation,
        high_weight_on_bones,
        initialize_images,
        focus_rois_names,
        registration_name,
        focus_volume_of_interest
):
    case.ComputeGrayLevelBasedRigidRegistration(
        FloatingExamination=floating_examination,
        ReferenceExamination=reference_examination,
        UseOnlyTranslations=use_only_translation,
        HighWeightOnBones=high_weight_on_bones,
        InitializeImages=initialize_images,
        FocusRoisNames=focus_rois_names,
        RegistrationName=registration_name,
    FocusVolumeOfInterest=focus_volume_of_interest)


# Register these functions with the dispatcher
dispatcher.register('get_rigid_registrations', 12, get_rigid_registrations_v12)
dispatcher.register('get_rigid_registrations', 15, get_rigid_registrations_v15)
dispatcher.register('get_rigid_registrations', 17, get_rigid_registrations_v15)

dispatcher.register('compute_gray_level_based_rigid_registration',
                    12, compute_gray_level_based_rigid_registration_v15)
dispatcher.register('compute_gray_level_based_rigid_registration',
                    15, compute_gray_level_based_rigid_registration_v15)
dispatcher.register('compute_gray_level_based_rigid_registration',
                    17, compute_gray_level_based_rigid_registration_v17)



@dispatcher.dispatch('get_rigid_registrations')
def get_rigid_registrations(case):
    pass

@dispatcher.dispatch('compute_gray_level_based_rigid_registration')
def compute_gray_level_based_rigid_registration(
        case,
        floating_examination,
        reference_examination,
        use_only_translation,
        high_weight_on_bones,
        initialize_images,
        focus_rois_names,
        registration_name,
        focus_volume_of_interest
):
    pass



