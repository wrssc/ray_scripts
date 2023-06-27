def subtract_roi_sources(rso, name, roi_A, roi_B):
    name = rso.case.PatientModel.GetUniqueRoiName(DesiredName=name)
    wall_intersection = rso.case.PatientModel.CreateRoi(
        Name=name,
        Color="255, 080, 225",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    try:
        rso.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
            ExpressionA={
                "Operation": 'Union',
                "SourceRoiNames": [roi_A],
                "MarginSettings": margins,
            },
            ExpressionB={
                "Operation": 'Union',
                "SourceRoiNames": [roi_B],
                "MarginSettings": margins,
            },
            ResultOperation='Subtraction',
            ResultMarginSettings=margins,
        )
        rso.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
            Examination=rso.exam, Algorithm="Auto"
        )
        return name
    except:
        return None
