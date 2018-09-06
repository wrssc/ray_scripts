'''Generate Goal Templates
This function is a stub for what will eventually be all goals relevant to
standard TPO's
'''
import sys
import os
import xml.etree.ElementTree
import connect
import Goals

def main():
    protocol = r'../protocols/SampleGoal.xml'
    #protocol_file = r'SampleGoal.xml'
    protocol_name = os.path.join(os.path.dirname(__file__), protocol)

    tree = xml.etree.ElementTree.parse(protocol_name)
    for g in tree.findall('//goals/roi'):
        print 'Adding goal ' + Goals.print_goal(g, 'xml')
        Goals.add_goal(g, connect.get_current('Plan'))
    ui = connect.get_current('ui')
    ui.TitleBar.MenuItem['Plan Optimization'].Click()
    ui.TitleBar.MenuItem['Plan Optimization'].Popup.MenuItem['Plan Optimization'].Click()
    ui.Workspace.TabControl['DVH'].TabItem['Clinical Goals'].Select()
    #ui.ToolPanel.TabItem._Scripting.Select()

if __name__ ==  'main':
    main()
