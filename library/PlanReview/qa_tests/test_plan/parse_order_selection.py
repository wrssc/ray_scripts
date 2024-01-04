import re
from PlanReview.review_definitions import ALERT, PASS


def parse_order_selection(beamset_name, messages, dialog_key):
    """
    Using the beamset name and the log file, use regex to find a phrase
    identifying the
    template name used in the treatment planning order for this beamset.
    Args:
        beamset_name: <str> name of current beamset
        messages: a dictionary of log data. See retrieve_logs.py
         Keys are: 'Date', 'Time', 'Log_Level', 'Message', 'Deepest_Context',
            'Case', 'Exam', 'Plan', 'Beamset', 'PlanID', 'BeamsetID', 'Source'
        dialog_key: key to be used for top level entry in the tree

    Returns:


    """
    # Parse the dialogs for specific key phrases related to the beamset dialog
    beamset_template_searches = {
        'Dialog': re.compile(r'(Treatment Planning Order selected:\s?)(.*)$')}
    template_data = {dialog_key: (ALERT,
                                  f'Treatment Planning for Beamset '
                                  f'{beamset_name} goals manually defined')}
    for m in messages:
        template_search = re.search(beamset_template_searches['Dialog'], m['Message'])
        if template_search and beamset_name in m['Beamset']:
            # Found the TPO Dialog. Lets display it
            # Note that it is a little sloppy, since this will always grab
            # the last match in the log file
            k, template_name = template_search.groups()
            template_data[dialog_key] = (PASS, template_name)
    return template_data
