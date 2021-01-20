import os
import pydicom
from pydicom.tag import Tag

# extract dicom file and gantry period from directory files
filepath = 'W:\\rsconvert\\'
hlist = os.listdir(filepath)
flist = filter(lambda x: '.dcm' in x, hlist)
filename = flist[0]
GPlist = filter(lambda x: '.txt' in x, hlist)
GPval = GPlist[0][3:8]+' '

# format and set tag to change
t1 = Tag('300d1040')

# read file
ds = pydicom.read_file(filepath+filename)

# add attribute to beam sequence
ds.BeamSequence[0].add_new(t1, 'UN', GPval)

# output file
ds.save_as(filepath+'new_'+filename, write_like_original=True)
