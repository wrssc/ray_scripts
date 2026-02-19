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
    try:
        import raystation as rs
    except ImportError:
        import connect as rs
    ui = rs.get_current('ui')
    if is_attrib(ui, 'GetApplicationVersion'):
        _version = ui.GetApplicationVersion().split('.')
        version = int(_version[0]) if int(_version[1]) != 99 else int(_version[0]) + 1
        subversion = int(_version[1])
        return version, subversion
    else:
        logging.error("Unable to get RS version")
