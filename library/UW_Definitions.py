TOMO_DATA = {'MACHINES': ['HDA0488'],
             'PLAN_TR_SUFFIX': r'_Tr',
             'LATERAL_ISO_MARGIN': 2.,  # cm
             'SUPPORTS': ['TomoCouch', 'QFix_Board_Only'],
             'DIAMETER': 85.0,  # cm cover diameter
             'COLLISION_TOLERANCE': 2.0,  # cm distance tolerance for shifting
             }

TRUEBEAM_DATA = {'MACHINES': ['TrueBeam', 'TrueBeamSTx'],
                 'SUPPORTS': ['TrueBeamCouch', 'CivcoBaseShell_Cork', 'CivcoInclineShell_Wax',
                              'QFix_H&N_TBCouch_F2andF3', 'QFix_Brain_TBCouch_H2andH2','Baseplate_Override_PMMA'],
                 'DIAMETER': 85.0,  # cm cover diameter
                 'COLLISION_TOLERANCE': 2.0,  # cm distance tolerance for shifting
                 }

