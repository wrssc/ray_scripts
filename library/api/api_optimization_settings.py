from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def edit_beam_optimization_settings_v12(beam_settings, jaw_motion,
                                        left_jaw, right_jaw, top_jaw, bottom_jaw,
                                        select_collimator_angle,
                                        allow_beam_split,
                                        optimization_types):
    """
    Edit the beam optimization settings for a beam
    Args:
        beam_settings: RS PlanOptimizations.OptimizationParameters\
                          .TreatmentSetupSettings.BeamSettings object
        jaw_motion: str: can be the following strings:
            ('Undefined' | 'Fixed' | 'Lock to limits' |
             'Use limits as max' | 'Automatic')
        left_jaw: float: left jaw position
        right_jaw: float: right jaw position
        top_jaw: float: top jaw position
        bottom_jaw: float: bottom jaw position
        select_collimator_angle: str: can be 'True' or 'False'
        allow_beam_split: str: can be 'True' or 'False'
        optimization_types: list: ['SegmentMU' | 'SegmentOpt']

    Returns:

    """
    if jaw_motion == 'UseLimitsAsMax':
        jaw_motion = 'Use limits as max'
    elif jaw_motion == 'LockToLimits':
        jaw_motion = 'Lock to limits'
    beam_settings.EditBeamOptimizationSettings(
        JawMotion=jaw_motion,
        LeftJaw=left_jaw,
        RightJaw=right_jaw,
        TopJaw=top_jaw,
        BottomJaw=bottom_jaw,
        SelectCollimatorAngle=select_collimator_angle,
        AllowBeamSplit=allow_beam_split,
        OptimizationTypes=optimization_types)


def edit_beam_optimization_settings_v15(beam_settings, jaw_motion,
                                        left_jaw, right_jaw, top_jaw, bottom_jaw,
                                        select_collimator_angle,
                                        allow_beam_split,
                                        optimization_types):
    if jaw_motion == 'Use limits as max':
        jaw_motion = 'UseLimitsAsMax'
    elif jaw_motion == 'Lock to limits':
        jaw_motion = 'LockToLimits'
    beam_settings.EditBeamOptimizationSettings(
        JawMotion=jaw_motion,
        LeftJaw=left_jaw,
        RightJaw=right_jaw,
        TopJaw=top_jaw,
        BottomJaw=bottom_jaw,
        SelectCollimatorAngle=select_collimator_angle,
        AllowBeamSplit=allow_beam_split,
        OptimizationTypes=optimization_types)


dispatcher.register('edit_beam_optimization_settings', 12, edit_beam_optimization_settings_v12)
dispatcher.register('edit_beam_optimization_settings', 15, edit_beam_optimization_settings_v15)


@dispatcher.dispatch('edit_beam_optimization_settings')
def edit_beam_optimization_settings(beam_settings, jaw_motion,
                                    left_jaw, right_jaw, top_jaw, bottom_jaw,
                                    select_collimator_angle,
                                    allow_beam_split,
                                    optimization_types):
    pass