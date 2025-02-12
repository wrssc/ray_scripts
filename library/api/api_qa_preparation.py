from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


#
# Beamset and Plan UID calls
def create_dqa_plan_v12(beamset, phantom_name, qa_plan_name, phantom_id, iso, dose_grid, couch_rotation):
    """
    Create a QA plan for a beamset in RayStation 12
    """
    # Version 12 specific code
    try:
        beamset.CreateQAPlan(
            PhantomName=phantom_name,
            PhantomId=phantom_id,
            QAPlanName=qa_plan_name,
            IsoCenter=iso,
            DoseGrid=dose_grid,
            GantryAngle=None,
            CollimatorAngle=None,
            CouchRotationAngle=couch_rotation,
            ComputeDoseWhenPlanIsCreated=True,
            NumberOfMonteCarloHistories=None,
            MotionSynchronizationTechniqueSettings=None,
            RemoveCompensators=False,
            EnableDynamicTracking=False)
        return "success"
    except Exception as e:
        return str(e.Message)


def create_dqa_plan_v15(beamset, phantom_name, qa_plan_name, phantom_id, iso, dose_grid, couch_rotation):
    """
    Create a QA plan for a beamset in RayStation 15
    """
    # Version 15 specific code
    try:
        beamset.CreateQAPlan(
            PhantomName=phantom_name,
            PhantomId=phantom_id,
            QAPlanName=qa_plan_name,
            IsoCenter=iso,
            DoseGrid=dose_grid,
            GantryAngle=None,
            CollimatorAngle=None,
            CouchRotationAngle=couch_rotation,
            ComputeDoseWhenPlanIsCreated=True,
            DesiredStatisticalUncertaintyForElectrons=None,
            MotionSynchronizationTechniqueSettings=None,
            RemoveCompensators=False,
            EnableDynamicTracking=False,
            SetupBeamsSettings={
                'UseSetupBeams': False,
                'UseLocalizationPointAsSetupIsocenter': False,
                'UseUserSelectedIsocenterAsSetupIsocenter': False,
            })
        return "success"
    except Exception as e:
        return str(e.Message)


# Register these functions with the dispatcher
dispatcher.register('create_dqa_plan', 12, create_dqa_plan_v12)
dispatcher.register('create_dqa_plan', 15, create_dqa_plan_v15)


@dispatcher.dispatch('create_dqa_plan')
def create_dqa_plan(beamset, phantom_name, qa_plan_name, phantom_id, iso, dose_grid, couch_rotation):
    """
    Create a QA plan for a beamset in RayStation
    :param beamset: The beamset to create the QA plan for
    :param phantom_name: The name of the phantom stored in the RayStation phantom library
    :param qa_plan_name: The name of the QA plan to create
    :param phantom_id: The ID of the phantom stored in the RayStation phantom library
    :param iso: The isocenter of the qa plan
    :param dose_grid: The dose grid resolution of the qa plan
    :param couch_rotation: The couch rotation of the qa plan
    :return: bool or str: True if the QA plan was created successfully, otherwise an error message
    """
    pass
