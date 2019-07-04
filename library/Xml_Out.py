"""
Output file formats for saving xml-based information from current parameters
"""
import os

from xml.etree import ElementTree
from xml.dom import minidom

log_dir = r'\\uwhis.hosp.wisc.edu\ufs\UWHealth\RadOnc\ShareAll\RayScripts\dev_logs'


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def save_stucture_map():
    pat_id = 'TPL_045_DAPD'
    m_logs_dir = os.path.join(log_dir, pat_id)
    filename = 'Structure_map'+pat_id+'.xml'
    from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment
    from datetime import datetime, date

    top = Element('StructureMap')

    d = datetime.now()
    comment = Comment(d.isoformat())
    top.append(comment)

    protocol = SubElement(top, 'protocol_structure')
    protocol.text = 'OTV4_4000'

    local_name = SubElement(top, 'local_name')
    local_name.text = 'PTV1_MD'

    local_dose = SubElement(top, 'local_dose', units='Gy')
    local_dose.text = '40'

    print prettify(top)
    ElementTree.write(os.path.normpath('{}/{}'.format(m_logs_dir, filename)))


def main():
    save_stucture_map()


if __name__ == '__main__':
    main()
