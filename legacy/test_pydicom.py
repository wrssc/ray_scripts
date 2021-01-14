""" Testing the loading of pydicom

"""

import pydicom
import pynetdicom3

ae = pynetdicom3.AE(scu_sop_class=['1.2.840.10008.1.1'],
                                ae_title=local_AET,
                                port=local_port)
