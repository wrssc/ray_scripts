from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def get_rigid_registrations_v12(case):
    # Version 12 specific code
    return case.Registrations


def get_rigid_registrations_v15(case):
    # Version 15 specific code
    return case.RigidRegistrations


# Register these functions with the dispatcher
dispatcher.register('get_rigid_registrations', 12, get_rigid_registrations_v12)
dispatcher.register('get_rigid_registrations', 15, get_rigid_registrations_v15)


@dispatcher.dispatch('get_rigid_registrations')
def get_rigid_registrations(case):
    pass



