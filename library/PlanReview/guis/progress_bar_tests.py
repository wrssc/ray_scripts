import PySimpleGUI as Sg


def display_progress_bar():
    layout = [[Sg.Text('Running tests...')],
              [Sg.ProgressBar(max_value=100, orientation='h', size=(30, 20),
                              key='progressbar')]]

    window = Sg.Window('Progress', layout, no_titlebar=True,
                       keep_on_top=True, finalize=True)

    progress_bar = window['progressbar']
    progress_bar.UpdateBar(0)

    return window, progress_bar
