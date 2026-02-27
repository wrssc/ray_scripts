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


def copy_geometries_v15(case, source_examination, source_roi_names, target_examination,
                        image_registration_name, use_added_rigid_registration_if_one_exists, poi_names=None):
    # Ignore poi_names for version 15 since it's not supported
    if poi_names is not None:
        raise Exception(f'poi_names is not a supported argument with Raystation version <17.')
    # Version <15 specific code to copy ROI geometry
    if isinstance(source_roi_names, str):
        source_roi_names = [source_roi_names]  # Ensure it's a list
    for source_roi_name in source_roi_names:
        case.PatientModel.CopyRoiGeometry(
            SourceExamination=source_examination,
            TargetExamination=target_examination,
            RoiName=source_roi_name,
            ImageRegistrationName=image_registration_name,
            UseAddedRigidRegistrationIfOneExists=use_added_rigid_registration_if_one_exists
        )


def copy_geometries_v17(case, source_examination, source_roi_names, target_examination,
                        image_registration_name, use_added_rigid_registration_if_one_exists, poi_names=None):
    # Version 17 specific code to copy ROI geometry
    if isinstance(source_roi_names, str):
        source_roi_names = [source_roi_names]  # Ensure it's a list
    if poi_names is not None and isinstance(poi_names, list):
        poi_names = [poi_names]  # Ensure it's a list if provided
    else:
        poi_names = []  # Default to an empty list if not provided

    case.PatientModel.CopyGeometries(
        SourceExamination=source_examination,
        TargetExamination=target_examination,
        RoiNames=source_roi_names,
        PoiNames=poi_names,
        ImageRegistrationName=image_registration_name,
        UseAddedRigidRegistrationIfOneExists=use_added_rigid_registration_if_one_exists
    )


def map_poi_geometries_rigidly_v15(case, poi_geometry_names,
                                   create_new_pois, reference_examination, target_examinations,
                                   transformations):
    # Version 15 specific code to map POI geometries rigidly
    case.MapPoiGeometriesRigidly(
        PoiGeometryNames=poi_geometry_names,
        CreateNewPois=create_new_pois,
        ReferenceExaminationName=reference_examination.Name,
        TargetExaminationNames=[t .Name for t in target_examinations],
        Transformations=transformations)


def map_poi_geometries_rigidly_v17(case, poi_geometry_names,
                                   create_new_pois, reference_examination, target_examinations,
                                   transformations):
    # Version 17 specific code to map POI geometries rigidly
    case.PatientModel.MapPoiGeometriesRigidly(
        PoiGeometryNames=poi_geometry_names,
        CreateNewPois=create_new_pois,
        ReferenceExamination=reference_examination,
        TargetExaminations=target_examinations,
        Transformations=transformations)


def map_roi_geometries_rigidly_v15(case, roi_geometry_names,
                                   create_new_rois, reference_examination, target_examinations,
                                   transformations):
    # Version 15 specific code to map ROI geometries rigidly
    case.MapRoiGeometriesRigidly(
        RoiGeometryNames=roi_geometry_names,
        CreateNewRois=create_new_rois,
        ReferenceExaminationName=reference_examination.Name,
        TargetExaminationNames=[t.Name for t in target_examinations],
        Transformations=transformations)

def map_roi_geometries_rigidly_v17(case, roi_geometry_names,
                                   create_new_rois, reference_examination, target_examinations,
                                   transformations):
    # Version 17 specific code to map ROI geometries rigidly
    case.PatientModel.MapRoiGeometriesRigidly(
        RoiGeometryNames=roi_geometry_names,
        CreateNewRois=create_new_rois,
        ReferenceExamination=reference_examination,
        TargetExaminations=target_examinations,
        Transformations=transformations)


# Register these functions with the dispatcher
dispatcher.register('delete_geometry', 12, delete_geometry_v12)
dispatcher.register('delete_geometry', 15, delete_geometry_v15)
dispatcher.register('delete_geometry', 17, delete_geometry_v15)

# Register the function to get registrations
dispatcher.register('get_rigid_registrations', 12, get_rigid_registrations_v12)
dispatcher.register('get_rigid_registrations', 15, get_rigid_registrations_v15)
dispatcher.register('get_rigid_registrations', 17, get_rigid_registrations_v15)

# Register the function to copy ROI geometry
dispatcher.register('copy_geometries', 12, copy_geometries_v15)
dispatcher.register('copy_geometries', 15, copy_geometries_v15)
dispatcher.register('copy_geometries', 17, copy_geometries_v17)

# Register the function to map POI geometries rigidly
dispatcher.register('map_poi_geometries_rigidly', 12, map_poi_geometries_rigidly_v15)
dispatcher.register('map_poi_geometries_rigidly', 15, map_poi_geometries_rigidly_v15)
dispatcher.register('map_poi_geometries_rigidly', 17, map_poi_geometries_rigidly_v17)

# Register the function to map ROI geometries rigidly
dispatcher.register('map_roi_geometries_rigidly', 12, map_roi_geometries_rigidly_v15)
dispatcher.register('map_roi_geometries_rigidly', 15, map_roi_geometries_rigidly_v15)
dispatcher.register('map_roi_geometries_rigidly', 17, map_roi_geometries_rigidly_v17)

@dispatcher.dispatch('delete_geometry')
def delete_geometry(case, exam, roi_name):
    pass


@dispatcher.dispatch('get_rigid_registrations')
def get_rigid_registrations(case):
    pass


@dispatcher.dispatch('copy_geometries')
def copy_geometries(case, source_examination, source_roi_names, target_examination,
                      image_registration_name, use_added_rigid_registration_if_one_exists):
    pass

@dispatcher.dispatch('map_poi_geometries_rigidly')
def map_poi_geometries_rigidly(case, poi_geometry_names,
                                   create_new_pois, reference_examination, target_examinations,
                                   transformations):
    pass

@dispatcher.dispatch('map_roi_geometries_rigidly')
def map_roi_geometries_rigidly(case, roi_geometry_names,
                                   create_new_rois, reference_examination, target_examinations,
                                   transformations):
    pass
