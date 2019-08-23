import connect
import logging


def check_localization(case, create=False, confirm=False):
    # Look for the sim point, if not create a point
    # Capture the current list of POI's to avoid a crash
    pois = case.PatientModel.PointsOfInterest
    sim_point_found = any(poi.Name == 'SimFiducials' for poi in pois)

    if sim_point_found:
        if confirm:
            logging.info("POI SimFiducials Exists")
            connect.await_user_input('Ensure Correct placement of the SimFiducials Point and continue script.')
        else:
            return True
    else:
        if create:
            case.PatientModel.CreatePoi(Examination=examination,
                                        Point={'x': 0,
                                               'y': 0,
                                               'z': 0},
                                        Volume=0,
                                        Name="SimFiducials",
                                        Color="Green",
                                        Type="LocalizationPoint")
            connect.await_user_input('Ensure Correct placement of the SimFiducials Point and continue script.')
        else:
            return False
