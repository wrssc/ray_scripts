"""
Output file formats for saving xml-based information from current parameters
"""
import os
import logging

from xml.etree import ElementTree
from xml.dom import minidom

# TODO: Is this an attribute we can pull from the logging module?
log_dir = r'\\uwhis.hosp.wisc.edu\ufs\UWHealth\RadOnc\ShareAll\RayScripts\dev_logs'



def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def save_structure_map():
    pat_id = 'TPL_045_DAPD'
    m_logs_dir = os.path.join(log_dir, pat_id)
    filename = pat_id+'structure_map.xml'

    import xml.etree.ElementTree as ET
    # from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment
    from datetime import datetime, date
    from xml.dom import minidom


    top = ET.Element('StructureMap')

    d = datetime.now()
    comment = ET.Comment(d.isoformat())
    top.append(comment)

    protocol = ET.SubElement(top, 'protocol_structure')
    protocol.text = 'OTV4_4000'

    local_name = ET.SubElement(top, 'local_name')
    local_name.text = 'PTV1_MD'

    local_dose = ET.SubElement(top, 'local_dose')#, units='Gy')
    local_dose.text = '40'
    local_dose.set('units','Gy')

    print prettify(top)
    xmlstr = minidom.parseString(ET.tostring(top)).toprettyxml(indent="   ")
    full_path_filename = os.path.normpath('{}/{}'.format(m_logs_dir, filename))
    with open(full_path_filename, "w") as f:
        f.write(xmlstr)
    # ElementTree(top).write(os.path.normpath('{}/{}'.format(m_logs_dir, filename)))


def main():
    save_structure_map()


if __name__ == '__main__':
    main()
