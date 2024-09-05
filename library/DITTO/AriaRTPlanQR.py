"""
This is a test code, meant to mostly be used with the RayStation Jupyter 
development notebook, to test the DICOM-RT RTPlan Q/R process from 
Aria.
"""

# RayStation Header
from connect import *  # type: ignore #pylint: disable=import-error

try:
    patient = get_current("Patient")  # type: ignore #pylint: disable=undefined-variable
except:
    pass

plan = None
try:
    plan = get_current("Plan")  # type: ignore #pylint: disable=undefined-variable
except:
    pass

case = None
try:
    case = get_current("Case")  # type: ignore #pylint: disable=undefined-variable
except:
    pass

# Script Header

import pydicom
import pynetdicom
import tempfile
import PySimpleGUI as sg
import sys
import pathlib
import socket

# Constants
local_aet = socket.gethostname()
aria_aet = "VMSDBD"  # Aria database daemon AE Title
aria_host = "10.151.26.250"  # Aria database daemon host name
aria_port = 108  # Aria database daemon port number
local_storage_port = (
    104  # I think this is the port that Aria will try to send to on this local AE
)


def aria_echo():
    """
    Simple function to only check the echo-ability of Aria from this local
    entity. Prints result to output.

    Returns a boolean True or False to indicate whether or not the echo
    attempt was successful.
    """
    success = False
    verify_ae = pynetdicom.AE()

    verify_ae.requested_contexts = pynetdicom.VerificationPresentationContexts
    verify_ae.ae_title = local_aet
    try:
        assoc = verify_ae.associate(aria_host, aria_port, ae_title=aria_aet)
        if assoc.is_established:
            status = assoc.send_c_echo()
            if status:
                # If the verification request succeeded this will be 0x0000
                print(
                    "C-ECHO request status from "
                    + str(aria_aet)
                    + " at host "
                    + str(aria_host)
                    + " on port "
                    + str(aria_port)
                    + ": 0x{0:04x}".format(status.Status)
                )
                if status.Status == 0x0000:
                    success = True
            else:
                print("ECHO Connection timed out, was aborted or received invalid response")
        else:
            print("ECHO Association rejected, aborted or never connected")
    except:
        print(
            "C-ECHO request to "
            + str(aria_aet)
            + " at host "
            + str(aria_host)
            + " on port "
            + str(aria_port)
            + " failed to execute."
        )
        assoc.release()
    else:
        assoc.release()

    return success


def aria_rtplan_list(verbose=False):
    """
    Returns a dict of plans available in Aria for the current patient.
    Each object in the dict will be keyed with a unique integer, 
    starting from zero,
    and the
    value will be a dict storing the relevant DICOM tags of the plan 
    for future searching: RTPlanLabel, StudyInstanceUID, SeriesInstanceUID,
    SOPClassUID, SOPInstanceUID.

    (the key used to be the RTPlanLabel, but for cases where we had multiple
    Aria plans with the exact same RTPlanLabel, this was an issue)

    Returns None if unsuccessful.
    """
    # Attempt to search Aria database for a specific patient's RTPlans
    find_ae = pynetdicom.AE()

    # pynetdicom.debug_logger()

    find_ae.add_requested_context(
        pynetdicom.sop_class.PatientRootQueryRetrieveInformationModelFind
    )  # pylint: disable=no-member
    find_ae.ae_title = local_aet

    # Create our Identifier (query) dataset
    ds = pydicom.dataset.Dataset()
    ds.PatientID = patient.PatientID
    ds.QueryRetrieveLevel = "IMAGE"
    ds.StudyInstanceUID = ""
    ds.SeriesInstanceUID = ""
    ds.RTPlanLabel = ""
    ds.SOPClassUID = pynetdicom.sop_class.RTPlanStorage  # pylint: disable=no-member
    ds.SOPInstanceUID = ""

    results = {}
    counter=0

    try:
        assoc = find_ae.associate(aria_host, aria_port, ae_title=aria_aet)
        if assoc.is_established:
            # Send the C-FIND request
            responses = assoc.send_c_find(
                ds, pynetdicom.sop_class.PatientRootQueryRetrieveInformationModelFind
            )  # pylint: disable=no-member
            for (status, identifier) in responses:
                if status:
                    if verbose:
                        print("C-FIND query status: 0x{0:04X}".format(status.Status))
                    if identifier:
                        # Here's the place where we have a valid discovery.
                        results[counter] = {
                            "RTPlanLabel": identifier.RTPlanLabel,
                            "StudyInstanceUID": identifier.StudyInstanceUID,
                            "SeriesInstanceUID": identifier.SeriesInstanceUID,
                            "SOPClassUID": identifier.SOPClassUID,
                            "SOPInstanceUID": identifier.SOPInstanceUID,
                        }
                        counter=counter+1

                        if verbose:
                            print("\tRTPlanLabel: " + str(identifier.RTPlanLabel))
                            print(
                                "\tStudyInstanceUID: "
                                + str(identifier.StudyInstanceUID)
                            )
                            print(
                                "\tSeriesInstanceUID: "
                                + str(identifier.SeriesInstanceUID)
                            )
                            print("\tSOPClassUID: " + str(identifier.SOPClassUID))
                            print("\tSOPInstanceUID: " + str(identifier.SOPInstanceUID))
                else:
                    print(
                        "Connection timed out, was aborted or received invalid response"
                    )
        else:
            print("C-FIND Association rejected, aborted or never connected")
    except:
        print(
            "C-FIND request to "
            + str(aria_aet)
            + " at host "
            + str(aria_host)
            + " on port "
            + str(aria_port)
            + " failed to execute."
        )
        assoc.release()
        results = None
    else:
        assoc.release()

    return results


def aria_get_rtplan(input_dict, file_dir=tempfile.gettempdir()):
    """
    This method takes in a dict defining the fields and values of DICOM header
    to pull out of Aria, and returns a pathname to the location where 
    the file was stored. Returns None if unsuccessful.

    aria_get_rtplan(input_dict, file_dir)

    the input dict needs to be like {'RTPlanLabel':'Some Plan Label', etc.}
    and needs to include RTPlanLabel, StudyInstanceUID, SeriesInstanceUID, 
    SOPClassUID, and SOPInstanceUID.

    file_dir: the root directory where the file will be saved.
    If not provided, then saved into tempfile.gettempdir()
    Must be a path-like object.
    """
    # Create the search dataset
    ds = pydicom.dataset.Dataset()
    ds.PatientID = patient.PatientID
    ds.QueryRetrieveLevel = "IMAGE"
    ds.StudyInstanceUID = input_dict["StudyInstanceUID"]
    ds.SeriesInstanceUID = input_dict["SeriesInstanceUID"]
    # ds.RTPlanLabel=input_dict['RTPlanLabel'] # This seems to be flaky
    ds.SOPClassUID = input_dict["SOPClassUID"]
    ds.SOPInstanceUID = input_dict["SOPInstanceUID"]

    file_location = pathlib.Path(file_dir, ("ARIA" + str(ds.SOPInstanceUID) + ".dcm"))

    # implement the handler for c_store event
    def handle_store(event):
        """Handle a C-STORE request event."""
        ds = event.dataset
        ds.file_meta = event.file_meta

        # Save the dataset using the SOP Instance UID as the filename
        ds.save_as(file_location, write_like_original=True)

        # Return a 'Success' status
        return 0x0000

    handlers = [(pynetdicom.evt.EVT_C_STORE, handle_store)]

    # Configure the storage part of this AE
    storage_ae = pynetdicom.AE()
    storage_ae.add_supported_context(
        pynetdicom.sop_class.RTPlanStorage
    )  # pylint: disable=no-member
    storage_ae.add_supported_context(
        pydicom.uid.ImplicitVRLittleEndian
    )  # pylint: disable=no-member

    # Configure the Move Request part of this AE.
    storage_ae.add_requested_context(
        pynetdicom.sop_class.PatientRootQueryRetrieveInformationModelMove
    )  # pylint: disable=no-member
    storage_ae.add_requested_context(
        pynetdicom.sop_class.RTPlanStorage
    )  # pylint: disable=no-member
    storage_ae.ae_title = local_aet

    # Spin up the storage SCP
    local_scp = storage_ae.start_server(
        ("", local_storage_port), block=False, evt_handlers=handlers
    )

    # Associate with the remote server
    try:
        assoc = storage_ae.associate(aria_host, aria_port, ae_title=aria_aet)
        if assoc.is_established:
            # Use the C-MOVE service to send the identifier
            responses = assoc.send_c_move(
                ds,
                local_aet,
                pynetdicom.sop_class.PatientRootQueryRetrieveInformationModelMove,
            )  # pylint: disable=no-member
            for (status, identifier) in responses:  # type: ignore #pylint: disable=unused-variable
                if status:
                    print("C-MOVE query status: 0x{0:04x}".format(status.Status))
                else:
                    print(
                        "MOVE Connection timed out, was aborted or received invalid response"
                    )
        else:
            print("MOVE Association rejected, aborted or never connected")
    except:
        print(
            "C-MOVE request to "
            + str(aria_aet)
            + " at host "
            + str(aria_host)
            + " on port "
            + str(aria_port)
            + " failed to execute."
        )
        assoc.release()
        file_location = None
    else:
        assoc.release()

    local_scp.shutdown()
    return file_location


def rs_beamset_list(rs_plan=plan):
    """
    This is a small function to simply return a list of beamsets in the currently
    open plan in RayStation. The plan must be sent in as an argument, but if 
    not supplied, defaults to the plan currently open in RayStation right now.

    The input plan object must be of the type returned by 
    plan = get_current("Plan") from RayStation.

    Method returns an empty list if no valid plan is sent in, or if there
    are no beamsets in this plan.

    [beamset_str_list]=rs_beamset_list(rs_plan_obj)
    """
    list_bs = []
    if rs_plan:
        for bs in rs_plan.BeamSets:
            list_bs.append(bs.DicomPlanLabel)
    return list_bs


def gui_choose_plans(list_aria, list_raystation, aria_return_type='index'):
    """
    This method takes in two lists, a list of Aria plan names and a list
    of relevant RayStation beamset names. The GUI then asks the user to
    select one of each.

    The third input is "aria_return_type" which can have values of "index"
    or "value". If the selection is "index" then the aria_return described below
    will simply be the index of the selection in the GUI drop-down. If the selection
    is "value" then the aria_return described below will be the value
    selected from the drop-down itself.

    The method returns a tuple (aria_return, RayStation beamset name)

    (aria_return, raystation_beamset_name) = gui_choose_plans(list_aria, list_raystation)
    """
    keyAria='keyAria'
    keyRS='keyRS'

    default_aria = None
    default_rs = None
    aria_index = None
    run_gui = True
    # Let's figure out if there are good default values for our drop-down boxes.
    if len(list_aria)==1 and len(list_raystation)==1 and list_aria[0].lower()==list_raystation[0].lower():
        # If there are only one option for both Aria and RayStation,
        # and those options match each other (at least lowercase match),
        # select those options and don't even bother showing the GUI.
        default_aria=list_aria[0]
        default_rs=list_raystation[0]
        run_gui=False
        aria_index=0 # the only available selection, since we won't read the combobox again later.
    elif len(list_raystation)==1:
        # If there only one RayStation beamset in the list, default to that.
        default_rs=list_raystation[0]

        # if there's a matching (lowercase match) plan in Aria for the selected RS plan, just default to that.
        aria_match = [name for name in list_aria if name.lower()==default_rs.lower()]
        if aria_match:
            default_aria=aria_match[0]
    elif len(list_aria)==1:
        # if we get here, then there is more than one RayStation plan, but there is only one Aria plan.
        # so just default to the Aria plan.
        default_aria=list_aria[0]

        # if there's a matching (lowercase match) plan in RayStation for the selected Aria plan, default to it.
        rs_match = [name for name in list_raystation if name.lower()==default_aria.lower()]
        if rs_match:
            default_rs=rs_match

    sg.theme('DefaultNoMoreNagging')
    layout =  [ [sg.Text('Choose the plans to compare:',font=('Helvetica',16,'bold'))]]
    layout += [ [sg.Column([[sg.Text('Aria Plan Name')], [sg.Combo(list_aria,key=keyAria)]]),
        sg.Column([[sg.Text('RayStation Beamset Name') ],[sg.Combo(list_raystation,key=keyRS)] ])]]
    layout += [ [sg.OK(), sg.Cancel()] ]

    # Create the Window
    window = sg.Window('Plan Selector', layout, finalize=True)

    # If there are good default values (as found above), pre-select them for the drop-downs
    if default_aria:
        # there might be more than one Aria plan with the same name. Select the LAST match.
        selected_aria = len(list_aria)-1-list_aria[::-1].index(default_aria)
        # attempt to set directly through the tkinter method
        window[keyAria].widget.current(newindex=selected_aria)
        # window[keyAria].update(list_aria[selected_aria]) # prior attempted method
    if default_rs:
        window[keyRS].update(list_raystation[list_raystation.index(default_rs)])
    guiEvent, guiValues = window.read(timeout=100)

    # Event Loop to process "events" and get the "values" of the inputs
    while run_gui:
        guiEvent, guiValues = window.read()
        if guiEvent in (sg.WIN_CLOSED,'Cancel'): # if user closes window
            guiValues = None
            break
        if guiEvent in ('OK'):
            # Need to abuse one of the underlying tkinter methods here to call this
            # thing specifically as a widget and use the current() method, which
            # should return the selected index. We'll store that in case we need it.
            aria_index = window[keyAria].widget.current()
            break
    window.close()

    if guiValues == None:
        return (None, None)
    
    # Depending on the response the user called for, we can return either selected index or value.
    if aria_return_type=='index':
        aria_return = aria_index
    elif aria_return_type=='value':
        aria_return = str(guiValues.pop(keyAria))
    else:
        raise ValueError('Input type "'+aria_return_type+'" for Aria return type not known.')
    
    rs_plan_name = str(guiValues.pop(keyRS))
    print('Selected Aria plan index: '+str(aria_return)+'\nSelected RayStation beamset name: '+str(rs_plan_name))
    return (aria_return, rs_plan_name)


def aria_qr(root_dir=None, beamset_name=None):
    """
    General outline:
    1. Echo Aria to make sure it works
    2. If Echo is successful, then get a list of the RTPlans for the current patient
    3. Get a list of the RS beamsets for the currently open plan
    4. Present the user with a choice, where user can select an Aria plan and RS beamset
    5. Ask Aria to send the plan to the new local server, which will save to a temp file.
    6. Export the RS beamset as a plan to a separate temp file.
    7. Return the path to these two temp files, along with the beamset name from RS.

    If this is successful it will return the string to the two file locations, plus
    the beamset name selected from RayStation:
    (Aria RTPlan DICOM file, RayStation RTPlan DICOM file, RayStation Beamset Name)

    If this is unsuccessful for any reason, it will return (None,None,None)

    Input: root_dir: root directory used to store the temp files written to disk
    If empty, defaults to a tempdir selected automatically.
    Should be a pathlike object.

    Input2: beamset_name:
    This is a string to auto-run this whole routine. If this string matches a 
    RayStation beamset name (the current beamset) as well as an available Aria
    plan name, then the user isn't presented with a GUI to select anything, this
    just runs.
    """
    # Key for the field we want to use as the aria plan list value
    list_key = "RTPlanLabel"

    # If you run aria_get_rtplan, clean up your tmpfile mess!
    if not root_dir:
        root_dir = tempfile.gettempdir()

    # Check for echo and fail if broken
    if not aria_echo():
        return None, None, None

    # Get the lists of valid objects and fail if there are no valid RTPlans or beamsets
    dict_aria_plans = aria_rtplan_list()
    list_rs_bs = rs_beamset_list()
    if not dict_aria_plans or not list_rs_bs:
        return None, None, None
    
    list_aria_plans = [dict_aria_plans[d][list_key] for d in dict_aria_plans]

    if beamset_name:
        if beamset_name in list_aria_plans:
            #raystation selection is still by string, beamset name key
            selected_rs = beamset_name

            #aria needs to be converted to the index position in the list
            # this is most problematic if Aria has multiple plans with the same name.
            # Not much we can do about that...just basically need to either pick the
            # first or the last occurrence of the plan in the list.

            #option 1: find the FIRST match of this in the aria list.
            # standard python method "index" returns first occurrence.
            # selected_aria = list_aria_plans.index(beamset_name)

            # option 2: find the LAST match of this in the aria list.
            selected_aria = len(list_aria_plans)-1-list_aria_plans[::-1].index(beamset_name)
        else:
            return None, None, None
    else:
        # Ask the user to select the plan and beamset of choice, and fail if not selected
        (selected_aria, selected_rs) = gui_choose_plans(list_aria_plans, list_rs_bs)
        if (selected_aria is None) or not selected_rs:
            print('Nothing selected! Cancelling.')
            return None, None, None

    # Export the Aria RTPlan file
    aria_file_location = aria_get_rtplan(dict_aria_plans[selected_aria], root_dir)
    print("Aria plan " + dict_aria_plans[selected_aria][list_key] + " saved to " + str(aria_file_location))

    # Export the RayStation beamset file
    try:
        case.ScriptableDicomExport(
            ExportFolderPath=str(root_dir),
            BeamSets=["%s:%s" % (plan.Name, selected_rs)],
            IgnorePreConditionWarnings=True,
        )
    except:
        yes_or_no = sg.popup_yes_no(
            "You must save to run the APTR tool. Do you want to save the patient?"
        )
        if yes_or_no == "Yes":
            get_current("Patient").Save()  # type: ignore #pylint: disable=undefined-variable

            case.ScriptableDicomExport(
                ExportFolderPath=str(root_dir),
                BeamSets=["%s:%s" % (plan.Name, selected_rs)],
                IgnorePreConditionWarnings=True,
            )
        else:
            sys.exit(0)

    rs_file_location = pathlib.Path(
        root_dir, ("RP" + plan.BeamSets[selected_rs].ModificationInfo.DicomUID + ".dcm")
    )
    print("RS beamset " + selected_rs + " saved to " + str(rs_file_location))

    return aria_file_location, rs_file_location, selected_rs


if __name__ == "__main__":
    # aria_qr(root_dir=pathlib.Path('H:\\RS Scratch'))
    aria_qr()
