import connect
import logging


def is_attrib(obj, attr_name):
    """
       Test if an attribute exists for an object
       :param obj: RS object
       :param attr_name: str: Attribute name
       :return: bool: True if attribute exists, False if not
       """
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        return None


def detect_api_version():
    ui = connect.get_current('ui')
    if is_attrib(ui, 'GetApplicationVersion'):
        _version = ui.GetApplicationVersion().split('.')
        version = int(_version[0]) if int(_version[1]) != 99 else int(_version[0]) + 1
        subversion = int(_version[1])
        return version, subversion
    else:
        logging.error("Unable to get RS version")


def find_scope(level=None):
    """
    Find the current available scope in RS at the level of level.
        If level is used, and the level is not in the current scope, produce
        a faultdatetime A combination of a date and a time.
    If find_scope is used, go as deep as possible and return a dictionary of all levels
            with None used for those not in current scope.
    :param level: if specified, return the RS object at level if it exists
     else if level is not specified return a dict of the available scopes
    :return: if level is specified the RS object is returned.
        If find_scope, then a dict of plan variables is used
    """

    # Find the deepest available scope and return a dict with available names
    scope = {}
    scope_levels = ["ui", "PatientDB", "Patient", "Case", "Examination", "Plan", "BeamSet"]

    for l in scope_levels:
        try:
            rs_obj = connect.get_current(l)
        except Exception as error:
            if hasattr(error, "Message"):
                no_current = "Invalid objectHandle"
                if no_current in error.Message:
                    rs_obj = None
                else:
                    logging.error("{}".format(error))
        if l == level:
            if rs_obj is None:
                raise IOError("No {} loaded, load {}".format(l, l))
            else:
                return rs_obj
        else:
            scope[l] = rs_obj
    if level is not None:
        logging.warning("Supplied level {} was not found".format(level))
    else:
        return scope


def get_machine(machine_name):
    """Finds the current machine name from the list of currently commissioned machines
    :param: machine_name (name of the machine in raystation,
    usually this is machine_name = beamset.MachineReference.MachineName
    return: machine (RS object)"""
    machine_db = connect.get_current("MachineDB")
    machine = machine_db.GetTreatmentMachine(machineName=machine_name, lockMode=None)
    return machine


def get_all_commissioned(machine_type=None):
    """Find all machines that have the status commissioned and are not deprecated.
        return: machine_names: List of machine names"""
    machine_db = connect.get_current("MachineDB")
    mm = machine_db.QueryCommissionedMachineInfo(Filter={'IsCommissioned':True, 'IsDeprecated':False})
    machine_names = []
    if machine_type:
        for m in mm:
            test_machine = get_machine(machine_name = m['Name'])
            if machine_type == 'Tomo':
                try:
                    test_machine.TomoBeamQualities._0
                    machine_names.append(m['Name'])
                except AttributeError:
                    pass
            elif machine_type == 'VMAT':
                try:
                    test_machine.ArcProperties.MaxGantryAngleSpeed
                    machine_names.append(m['Name'])
                except AttributeError:
                    pass
    else:
        machine_names = [m['Name'] for m in mm]

    return machine_names