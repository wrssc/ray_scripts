"""Add Shoulder Blocking VMAT Beams
Script to add shoulder blocking using user driven info
"""

import sys
import os
import logging
import Objectives
import connect
import UserInterface
import Goals
import Beams


def main():
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = r'beamsets'
    file = 'UWVMAT_Beamsets.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder,
                                  beamset_folder)
    beamset_name = '2 Arc VMAT'

    beam_elements = Beams.select_element(set_type='beamset',
                                         set_elements='beam',
                                         set_name=beamset_name,
                                         filename=file,
                                         folder=path_protocols)
    #                                     order_name=order_name)
    for et_beamsets in beam_elements:
        beams = et_beamsets.findall('./objectives/roi')
        for b in beams:
            b_n = b.find('name').text
            b_t = b.find('type').text
            beams = b.findall('./objectives/roi')
            logging.debug('Success {}'.format(b_n))


if __name__ == '__main__':
    main()
