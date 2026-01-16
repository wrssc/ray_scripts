def get_machine(machine_name):
    from library.api.api_rs import import_raystation_api
    rs = import_raystation_api()
    """Finds the current machine name from the list of currently commissioned machines
    :param: machine_name (name of the machine in raystation,
    usually this is machine_name = beamset.MachineReference.MachineName
    return: machine (RS object)"""
    machine_db = rs.get_current("MachineDB")
    machine = machine_db.GetTreatmentMachine(machineName=machine_name, lockMode=None)
    return machine
