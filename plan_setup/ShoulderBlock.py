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
        protocol = 'UW Head and Neck'
        beam_elements = Beams.select_element(set_type='beamset',
                                                  set_element='beam',
                                                  protocol=protocol)
        for et_beamsets in beam_elements:
            beams = et_beamsets.findall('./objectives/roi')
            for b in beams:
                b_n = b.find('name').text
                b_t = b.find('type').text
                beams = b.findall('./objectives/roi')
            logging.debug('Success {}'.format(beams.))




if __name__ == '__main__':
        main()