from library.api.dispatcher import APIDispatcher

dispatcher = APIDispatcher()  # Create an instance of the dispatcher


# Plan Optimization Level
def add_optimization_function_v12(plan_optimization, function_type, roi_name,
                                  restricted_to_beamset=None, is_constraint=False,
                                  is_robust=False, use_rbe_dose=False,
                                  restrict_to_beams=[]):
    if restrict_to_beams:
        is_restricted_to_beam = True
    else:
        is_restricted_to_beam = False
    o = plan_optimization.AddOptimizationFunction(FunctionType=function_type,
                                                  RoiName=roi_name,
                                                  IsConstraint=is_constraint,
                                                  RestrictAllBeamsIndividually=is_restricted_to_beam,
                                                  IsRobust=is_robust,
                                                  RestrictToBeamSet=restricted_to_beamset,
                                                  UseRbeDose=use_rbe_dose)
    return o


def add_optimization_function_v15(plan_optimization, function_type, roi_name,
                                  restricted_to_beamset=None, is_constraint=False,
                                  is_robust=False, use_rbe_dose=False,
                                  restrict_to_beams=[]):
    if restrict_to_beams:
        is_restricted_to_beam = True
    else:
        is_restricted_to_beam = False
    o = plan_optimization.AddOptimizationFunction(
        FunctionType=function_type,
        RoiName=roi_name,
        IsConstraint=is_constraint,
        RestrictAllBeamsIndividually=is_restricted_to_beam,
        RestrictToBeams=restrict_to_beams,  # plural
        IsRobust=is_robust,
        RestrictToBeamSet=restricted_to_beamset,
        UseRbeDose=use_rbe_dose)
    return o


dispatcher.register('add_optimization_function', 12, add_optimization_function_v12)
dispatcher.register('add_optimization_function', 15, add_optimization_function_v15)
dispatcher.register('add_optimization_function', 17, add_optimization_function_v15)


@dispatcher.dispatch('add_optimization_function')
def add_optimization_function(plan_optimization, function_type, roi_name,
                              restricted_to_beamset=None, is_constraint=False,
                              is_robust=False, use_rbe_dose=False,
                              restrict_to_beams=[]):
    pass