beamset=beam_set
parent_plan = 'Pros_THI_R0A0:Pros_THI_R0A0'
ignore_warnings=False
beamset.SendTransferredPlanToRayGateway(
RayGatewayTitle='RAYGATEWAY',
PreviousBeamSet=parent_plan,
OriginalBeamSet=parent_plan,
IgnorePreConditionWarnings=ignore_warnings)