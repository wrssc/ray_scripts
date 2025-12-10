from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def delete_geometry_v12(case, exam, roi_name):
    # Version 12 specific code
    rg = case.PatientModel.StructureSets[exam.Name].RoiGeometries[roi_name]
    rg.DeleteGeometry()


def delete_geometry_v15(case, exam, roi_name):
    # Version 15 specific code
    rg = case.PatientModel.StructureSets[exam.Name].RoiGeometries[roi_name]
    rg.DeleteRoiGeometry()


def get_rigid_registrations_v12(case):
    # Version 12 specific code to get registrations
    if hasattr(case.PatientModel, 'Registrations'):
        return [r for r in case.PatientModel.Registrations]
    return []


def get_rigid_registrations_v15(case):
    # Version 15 specific code to get registrations
    if not hasattr(case.PatientModel, 'RigidRegistrations'):
        return []
    return [r for r in case.PatientModel.RigidRegistrations]


# Register these functions with the dispatcher
dispatcher.register('delete_geometry', 12, delete_geometry_v12)
dispatcher.register('delete_geometry', 15, delete_geometry_v15)
dispatcher.register('delete_geometry', 17, delete_geometry_v15)

# Register the function to get registrations
dispatcher.register('get_rigid_registrations', 12, get_rigid_registrations_v12)
dispatcher.register('get_rigid_registrations', 15, get_rigid_registrations_v15)
dispatcher.register('get_rigid_registrations', 17, get_rigid_registrations_v15)



@dispatcher.dispatch('delete_geometry')
def delete_geometry(case, exam, roi_name):
    pass

@dispatcher.dispatch('get_rigid_registrations')
def get_rigid_registrations(case):
    pass



