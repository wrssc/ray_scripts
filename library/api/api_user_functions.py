from library.api.dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def final_dose_check_v12(site, technique, rso, beamset_name):
    # Version 12 specific code
    from library.FinalDose import final_dose_v12 as final_dose
    return final_dose(site, technique, rso, beamset_name)


def final_dose_check_v15(site, technique, rso, beamset_name):
    # Version 15 specific code
    from library.FinalDose import final_dose_v15 as final_dose
    return final_dose(site, technique, rso, beamset_name)


# Register these functions with the dispatcher
dispatcher.register('final_dose', 12, final_dose_check_v12)
dispatcher.register('final_dose', 15, final_dose_check_v15)


@dispatcher.dispatch('final_dose')
def final_dose(site, technique, rso, beamset_name):
    pass