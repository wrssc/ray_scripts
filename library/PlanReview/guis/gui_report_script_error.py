import PySimpleGUI as Sg
from PlanReview.utils import get_user_name
from PlanReview.utils.email_results import email_report, save_report, capture_screen


def report_script_error(rso):
    # Define the layout of the error report dialog
    user_name = get_user_name()

    error_report_layout = [
        [Sg.Text('Patient ID'), Sg.Input(default_text=rso.patient.PatientID,
                                         key='patient_id')],
        [Sg.Text('Beamset Name:'),
         Sg.Input(default_text=rso.beamset.DicomPlanLabel,
                  key='beamset_name')],
        [Sg.Text('User Name:'),
         Sg.Input(default_text=user_name, key='user_name')],
        [Sg.Text('Description:')],
        [Sg.Multiline(key='description', size=(50, 10))],
        [Sg.Button("Capture",
                   tooltip='Capture a screenshot with Snipping Tool: select '
                           '"New",'
                           + ' capture your screen, and press "Ctrl-C" to '
                             'save to clipboard.'),
         Sg.Button("Finish")],
    ]

    # Create the dialog window
    error_report_window = Sg.Window('Error Report', error_report_layout)
    img_data = None
    # Event loop for the dialog window
    while True:
        event, values = error_report_window.read()
        if event == Sg.WIN_CLOSED:
            break
        elif event == 'Capture':
            # Take a screenshot
            img_data = capture_screen(error_report_window)
            if img_data:
                Sg.popup_ok('Screenshot captured!')
            else:
                Sg.popup_ok(
                    'Oops I missed it. Try hitting Ctrl-C after you capture')
                img_data = capture_screen(error_report_window)
        elif event == 'Finish':
            # Save the report and close the window
            patient_id = values['patient_id']
            beamset_name = values["beamset_name"]
            description = values["description"]
            screenshot = img_data if img_data else None
            file_path = save_report('error_report', patient_id=patient_id, beamset_name=beamset_name,
                                    user_name=user_name, report_text=description, screenshot=screenshot)
            email_report(file_path, 'error_report', source='manual')
            error_report_window.close()
            break
