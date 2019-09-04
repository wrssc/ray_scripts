import connect
import logging
import sys


def check_localization(case, exam, create=False, confirm=False):
    # Look for the sim point, if not create a point
    # Capture the current list of POI's to avoid a crash
    pois = case.PatientModel.PointsOfInterest
    sim_point_found = any(poi.Type == 'LocalizationPoint' for poi in pois)

    if sim_point_found:
        if confirm:
            logging.info("POI SimFiducials Exists")
            connect.await_user_input('Ensure Correct placement of the SimFiducials Point and continue script.')
            return True
        else:
            return True
    else:
        if create and not sim_point_found:
            case.PatientModel.CreatePoi(Examination=exam,
                                        Point={'x': 0,
                                               'y': 0,
                                               'z': 0},
                                        Volume=0,
                                        Name="SimFiducials",
                                        Color="Green",
                                        Type="LocalizationPoint")
            connect.await_user_input('Ensure Correct placement of the SimFiducials Point and continue script.')
            return True
        else:
            return False


def find_optimization_index(plan, beamset):
    # Find current Beamset Number and determine plan optimization
    opt_index = 0
    index_not_found = True
    # In RS, OptimizedBeamSets objects are keyed using the DicomPlanLabel, or Beam Set name.
    # Because the key to the OptimizedBeamSets presupposes the user knows the PlanOptimizations index
    # this while loop looks for the PlanOptimizations index needed below by searching for a key
    # that matches the BeamSet DicomPlanLabel
    # This can likely be replaced with a list comprehension
    while index_not_found:
        try:
            opt_name = plan.PlanOptimizations[opt_index].OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            index_not_found = False
        except Exception:
            index_not_found = True
            opt_index += 1
    if index_not_found:
        logging.warning("Beamset optimization for {} could not be found.".format(beamset.DicomPlanLabel))
        return None
    else:
        # Found our index.  We will use a shorthand for the remainder of the code
        plan_optimization = plan.PlanOptimizations[opt_index]
        logging.info(
            'Optimization found, proceeding with plan.PlanOptimization[{}] for beamset {}'.format(
                opt_index, plan_optimization.OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            ))
        return opt_index

