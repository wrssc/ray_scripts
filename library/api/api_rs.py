from library.api.dispatcher import APIDispatcher

dispatcher = APIDispatcher()  # Create an instance of the dispatcher

def import_raystation_api_v12():
    # Version 12 specific code
    import connect
    return connect

def import_raystation_api_v15():
    # Version 15 specific code
    import connect as rs
    return rs

def import_raystation_api_v17():
    # Version 17 specific code
    import raystation as rs
    return rs

# Register these functions with the dispatcher
dispatcher.register('import_raystation_api', 12, import_raystation_api_v12)
dispatcher.register('import_raystation_api', 15, import_raystation_api_v15)
dispatcher.register('import_raystation_api', 17, import_raystation_api_v17)

@dispatcher.dispatch('import_raystation_api')
def import_raystation_api():
    """Return the RayStation scripting API module for the current environment.

        This is dispatched by APIDispatcher based on RayStation version.
        """
    raise RuntimeError(
        "APIDispatcher did not resolve an implementation for import_raystation_api."
    )