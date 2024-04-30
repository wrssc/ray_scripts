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


# Register these functions with the dispatcher
dispatcher.register('delete_geometry', 12, delete_geometry_v12)
dispatcher.register('delete_geometry', 15, delete_geometry_v15)


@dispatcher.dispatch('delete_geometry')
def delete_geometry(case, exam, roi_name):
    pass



