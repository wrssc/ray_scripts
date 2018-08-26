import xml.etree.ElementTree
import connect
import Goals

tree = xml.etree.ElementTree.parse('SampleGoal.xml')
for g in tree.findall('//goals/roi'):
    print 'Adding goal ' + Goals.print_goal(g, 'xml')
    Goals.add_goal(g, connect.get_current('Plan'))