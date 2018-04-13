""" Create Homogeneous Phantom
    
    This script generates a homogeneous phantom CT (0 HU) padded by empty voxels. The 
    DICOM origin is set to the top (anterior) center of the image. The image size and 
    dimensions are specified below. The resulting DICOM images are saved to the provided 
    directory using the format ct_###.dcm.
    
    This script uses the pydicom and numpy packages. For installation instructions, see 
    http://pydicom.readthedocs.io/en/stable/getting_started.html and 
    https://scipy.org/install.html, respectively. Copies of both packages are included as
    submodules within this repository. 
    
    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.1.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Create-Reference-CT'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import os
import numpy
import datetime
import logging
import pydicom
import tempfile
import shutil
import time


def main():

    # Get current date, time
    now = datetime.datetime.now()

    # If running from within RayStation, write to temp folder and import
    ray = False
    try:
        import connect
        import UserInterface

        machine_db = connect.get_current('MachineDB')
        patient_db = connect.get_current('PatientDB')
        path = tempfile.mkdtemp()
        logging.debug('Temporary folder generated at {}'.format(path))
        ray = True

        # Start script status window
        status = UserInterface.ScriptStatus(steps=['Enter Phantom Dimensions'
                                                   'Generate Temporary CT Files',
                                                   'Import Files into RayStation',
                                                   'Set Imaging Equipment',
                                                   'Create External Contour',
                                                   'Export CT (optional)'],
                                            docstring=__doc__,
                                            help=__help__)
        status.next_step(text='For this step, enter the desired phantom details\nin the displayed input box.')

        # Display input dialog and retrieve phantom size
        inputs = UserInterface.InputDialog(inputs={'a': 'Enter phantom name:',
                                                   'b': 'Enter phantom ID:',
                                                   'c': 'Enter number of voxels in IEC X,Z,Y:',
                                                   'd': 'Enter resolution in IEC X,Z,Y (mm):'},
                                           required=['a', 'b', 'c', 'd'],
                                           initial={'a': 'Water Phantom',
                                                    'b': '{0}{1:0>2}{2:0>2}'.format(now.year, now.month, now.day),
                                                    'c': '650, 400, 650',
                                                    'd': '1, 1, 1'})
        time.sleep(1)
        response = inputs.show()
        name = response['a'].strip()
        mrn = response['b'].strip()
        size = map(int, response['c'].split(','))
        res = map(int, response['d'].split(','))

        status.next_step(text='Generating temporary CT files based on provided\ndimensions...')

    except (ImportError, OSError, SystemError):
        logging.info('Running outside RayStation, will prompt user to enter folder')
        path = raw_input('Enter path to write CT to: ').strip()
        if not os.path.exists(path):
            os.mkdir(path)

        # Prompt for name, ID, image size and resolution (in mm), IEC [X,Z,Y]
        name = raw_input('Enter phantom name: ').strip()
        mrn = raw_input('Enter phantom ID: ').strip()
        size = map(int, raw_input('Enter number of voxels in IEC X,Z,Y (650, 400, 650): ').split(','))
        res = map(int, raw_input('Enter mm resolution in IEC X,Z,Y (1, 1, 1): ').split(','))

    # Pad X/Z dimensions by a voxel (will be air)
    size[0] += 2
    size[1] += 2

    # Create new dict, and add basic image attributes
    ds = pydicom.dataset.Dataset()
    ds.file_meta = pydicom.dataset.Dataset()
    ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'
    ds.file_meta.ImplementationClassUID = '1.2.40.0.13.1.1'
    ds.file_meta.ImplementationVersionName = 'dcm4che-2.0'
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
    ds.Modality = 'CT'
    ds.SOPClassUID = ds.file_meta.MediaStorageSOPClassUID
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    ds.RescaleIntercept = -1024
    ds.RescaleSlope = 1
    ds.InstanceCreationDate = '{0}{1:0>2}{2:0>2}'.format(now.year, now.month, now.day)
    ds.InstanceCreationTime = '{0:0>2}{1:0>2}{2:0>2}'.format(now.hour, now.minute, now.second)
    ds.StudyDate = '{0}{1:0>2}{2:0>2}'.format(now.year, now.month, now.day)
    ds.StudyTime = '{0:0>2}{1:0>2}{2:0>2}'.format(now.hour, now.minute, now.second)
    ds.AcquisitionDate = '{0}{1:0>2}{2:0>2}'.format(now.year, now.month, now.day)
    ds.AcquisitionTime = '{0:0>2}{1:0>2}{2:0>2}'.format(now.hour, now.minute, now.second)
    ds.ImageType = 'ORIGINAL\PRIMARY\AXIAL'
    ds.Manufacturer = 'pydicom'
    ds.ManufacturerModelName = 'CreateReferenceCT'
    ds.SoftwareVersion = '1.0'
    ds.SeriesDescription = 'Uniform Phantom'
    ds.PatientName = name
    ds.PatientID = mrn
    ds.SliceThickness = res[2]
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.FrameOfReferenceUID = pydicom.uid.generate_uid()
    ds.PatientPosition = 'HFS'
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = [-((size[0] - 1) * res[0]) / 2, -res[1] / 2, ((size[2] - 1) * res[2]) / 2]
    ds.ImagesInAcquisition = size[2]
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = 'MONOCHROME2'
    ds.Rows = size[1]
    ds.Columns = size[0]
    ds.PixelSpacing = [res[0], res[1]]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0

    # Create padded image
    img = numpy.zeros(shape=(size[1], size[0]), dtype=numpy.uint16)
    for i in range(1, size[1] - 1):
        for j in range(1, size[0] - 1):
            img[i, j] = 1024

    ds.PixelData = img.tostring()

    try:
        bar = UserInterface.ProgressBar(text='Writing CT files', steps=size[2])
    except ImportError:
        bar = False
        logging.info('Progress bar not available')

    # Loop through CT Images
    for i in range(size[2]):

        if not isinstance(bar, bool):
            bar.update('Writing image ct_{0:0>3}.dcm'.format(i + 1))

        # Generate unique IDs
        ds.file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID

        # Set position info for this image
        ds.SliceLocation = -((size[2] - 1) * res[2]) / 2 + i * res[2]
        ds.ImagePositionPatient[2] = -ds.SliceLocation
        ds.InstanceNumber = i + 1

        # Write CT image
        logging.debug('Writing image {0}ct_{1:0>3}.dcm'.format(path, i + 1))
        ds.save_as(os.path.normpath('{0}/ct_{1:0>3}.dcm'.format(path, i + 1)))

    if not isinstance(bar, bool):
        bar.close()

    # If in RayStation, import DICOM files
    if ray:

        status.next_step(text='Importing the temporary CT into RayStation...')

        patient_db.ImportPatientFromPath(Path=path,
                                         Patient={'Name': name},
                                         SeriesFilter={},
                                         ImportFilters=[])

        logging.info('Import successful')
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        examination = connect.get_current('Examination')

        # Set imaging equipment
        import clr
        clr.AddReference('System.Collections')
        import System.Collections.Generic
        ct_dict = machine_db.GetCtImagingSystemsNameAndCommissionTime()
        e = ct_dict.GetEnumerator()
        e.MoveNext()
        status.next_step('Setting imaging equipment to {}...'.format(e.Current.Key))
        logging.debug('Setting imaging equipment to {}'.format(e.Current.Key))
        examination.EquipmentInfo.SetImagingSystemReference(ImagingSystemName=e.Current.Key)

        # Create external ROI
        status.next_step(text='Generating External Contour...')
        logging.debug('Generating External Contour')
        external = case.PatientModel.CreateRoi(Name='External',
                                               Color='Blue',
                                               Type='External',
                                               TissueName='',
                                               RbeCellTypeName=None,
                                               RoiMaterial=None)
        external.CreateExternalGeometry(Examination=examination, ThresholdLevel=None)
        patient.Save()

        # Prompt user to export
        status.next_step(text='At this step, you can choose to export the \nphantom CT and structure set')
        answer = UserInterface.QuestionBox('Do you wish to export the phantom to a folder?')
        if answer.response:
            common = UserInterface.FolderBrowser('Select a folder to export to:')
            export = common.show()
            try:
                logging.debug('Exporting CT and RTSS to {}'.format(export))
                case.ScriptableDicomExport(ExportFolderPath=export,
                                           Examinations=examination.Name,
                                           RtStructureSetsForExaminations=examination.Name,
                                           DicomFilter='',
                                           IgnorePreConditionWarnings=True)

            except SystemError as error:
                logging.warning(str(error))

        # Finish up
        shutil.rmtree(path, ignore_errors=True)
        status.finish(text='Script execution successful. Note, the phantom material\nwas not set to water. If you ' +
                           'plan on running other QA scripts,\nset the external to water first.')

    logging.debug('CT generation successful')


if __name__ == '__main__':
    main()
