""" Rename Rois Delete Empty
    Rename Rois with a Prefix or Suffix. Delete Empties
"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '19-Oct-2020'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2020, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/wrssc/ray_scripts'
__credits__ = []
import sys
import PySimpleGUI as sg
import connect
import re


def rename_gui(case):
    """
    Simple gui to copy message to clipboard
    :return: None but copies string message to clipboard
    """
    dialog_name = 'Rename or Append Suffix'
    layout = [[sg.Combo(['Prefix', 'Suffix','None'], key='NAME_LOC'),
               sg.Text('Text to Append/PrePend', size=(15, 1)),
               sg.InputText(key='NAME')], [sg.Checkbox('Delete Empty', key='DELETE')],
              [sg.Button('Quit'), sg.Button('Submit')]]
    window = sg.Window('Rename Contours',
                       layout,
                       default_element_size=(40, 2), grab_anywhere=True)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Quit':
            break
        elif event == "Submit":
            selections = values
            break
    window.close()
    return values


def main():
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')

    except Exception:
        connect.await_user_input('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')
    #
    prefix = False
    delete_empty = False
    rename = True
    user_prompt = rename_gui(case)
    if user_prompt['NAME_LOC'] == 'Prefix':
        prefix = True
    elif user_prompt['NAME_LOC'] == 'NONE':
        rename=True

    if user_prompt['DELETE']:
        delete_empty = True

    contour_list = [r.Name for r in case.PatientModel.RegionsOfInterest]
    if delete_empty:
        deletes = []
        for c in contour_list:
            r = case.PatientModel.RegionsOfInterest[c]
            if not case.PatientModel.RegionsOfInterest[exam.Name].RoiGeometries[r].HasContours():
                deletes.append(c)
        if deletes:
            for d in deletes:
                case.PatientModel.RegionsOfInterest[d].DeleteRoi()

    if rename:
        contour_list = [r.Name for r in case.PatientModel.RegionsOfInterest]
        for c in contour_list:
            r = case.PatientModel.RegionsOfInterest[c]
            if prefix:
                r.Name = re.sub("^", user_prompt['NAME'], c)
            else:
                r.Name = re.sub("$", user_prompt['NAME'], c)


if __name__ == '__main__':
    main()
