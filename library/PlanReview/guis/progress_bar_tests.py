try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg


def display_progress_bar(title_text='Progress on tests', progress_bar_text='Running tests...'):
    layout = [[Sg.Text(progress_bar_text, key='progress_text')],
              [Sg.ProgressBar(max_value=100, orientation='h', size=(30, 20),
                              key='progressbar')]]

    window = Sg.Window(title_text, layout, no_titlebar=True,
                       keep_on_top=True, finalize=True)

    progress_bar = window['progressbar']
    progress_text = window['progress_text']
    progress_bar.UpdateBar(0)

    return window, progress_bar, progress_text
