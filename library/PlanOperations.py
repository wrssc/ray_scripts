import connect
import logging


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
