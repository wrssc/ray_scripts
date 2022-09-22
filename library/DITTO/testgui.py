import sys
import os
import PySimpleGUI as sg

treedata = sg.TreeData()

treedata.Insert(">", '_A_', 'A', [1, 2, 3])
treedata.Insert(">", '_B_', 'B', [4, 5, 6])
treedata.Insert("_A_", '_A1_', 'A1', ['can', 'be', 'anything'])

layout = [
    [sg.Tree(
        data=treedata,
        headings=['Size', ],
        auto_size_columns=True,
        num_rows=20,
        col0_width=40,
        key='-TREE-',
        show_expanded=False,
        enable_events=True),
    ],
    [sg.Button('Ok'), sg.Button('Cancel')]
]

window = sg.Window('Tree Element Test', layout)

while True:  # Event Loop
    event, values = window.read()
    if event in (sg.WIN_CLOSED, 'Cancel'):
        break
    print(event, values)
window.close()
