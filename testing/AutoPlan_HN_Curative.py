""" AutoPlan_HN_Curative
    
    Automatic generation of a curative Head and Neck Plan.  
    -Loads planning structures
    -Loads Beams (or templates)
    -Loads clinical goals
    -Loads plan optimization templates
    -Runs an optimization script
    -Saves the plan for future comparisons

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2018-Mar-28'
__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '6.0.0'
__maintainer__ = 'One maintainer'
__email__ =  'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import StructureOperations


def main():
    # Define planning structures
    dialog1_response = {'number_of_targets': 3,
                        'generate_underdose': False,
                        'generate_uniformdose': True,
                        'generate_inner_air': False}
    dialog2_response = {'PTV_6300': 6300, 'PTV_6000': 6000, 'PTV_5400': 5400}
    dialog3_response = {'structures': ['Bone_Mandible', 'Larynx', 'Esophagus'],
                        'standoff': 0.4}
    dialog4_response = {'structures': ['Bone_Mandible', 'Larynx', 'Esophagus'],
                        'standoff': 0.4}
    dialog5_response = {'target_skin': False,
                        'ring_hd': True,
                        'target_rings': True,
                        'thick_hd_ring': 2,
                        'thick_ld_ring': 5,
                        'ring_standoff': 0.2,
                        'otv_standoff': 0.4}
    StructureOperations.planning_structures(
        generate_ptvs=True,
        generate_ptv_evals = True,
        generate_otvs = True,
        generate_skin = True,
        generate_inner_air = True,
        generate_field_of_view = True,
        generate_ring_hd = True,
        generate_ring_ld = True,
        generate_normal_2cm = True,
        generate_combined_ptv = True,
        skin_contraction = 0.3,
        run_status=False,
        dialog1_response = dialog1_response,
        dialog2_response = dialog2_response,
        dialog3_response = dialog3_response,
        dialog4_response = dialog4_response,
        dialog5_response = dialog5_response
    )


if __name__ == '__main__':
    main()