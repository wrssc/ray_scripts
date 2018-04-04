""" Import and Re-calculate DICOM RT Plans
    
    This script imports all DICOM data from a selected directory into the current patient,
    updates the dose grid, re-calculates, and finally exports the plan and beam doses for
    each plan to a destination directory. This script is useful when you have a large group
    of patient specific RT Plans (created from QA Preparation, for example) that you would
    like to quickly re-compute and re-export for analysis. If the import directory is empty
    (user clicked Cancel), the script will still update and re-calculate all existing plans.
    If the export directory is empty, the script will import and re-calculate but not export
    the files.

    In this version, the DICOM data is not checked first to verify that each file is
    associated with that patient. Therefore, the function will crash. I expected to add
    this feature in the next version (once pydicom is installed).
    
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
__date__ = '2018-03-16'

__version__ = '1.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'N/A'

__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '6.1.1.2'
__maintainer__ = 'Mark Geurts'

__email__ =  'mark.w.geurts@gmail.com'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify import statements
from connect import *
from logging import warning
import clr
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import FolderBrowserDialog, DialogResult, MessageBox, \
    MessageBoxButtons

# Define path to search for RT PLANS
dialog = FolderBrowserDialog()
dialog.Description = 'Select the path containing DICOM RT Plans to import:'
if (dialog.ShowDialog() == DialogResult.OK):
    ipath = dialog.SelectedPath
else:
    warning('Folder not selected, import will be skipped')
    ipath = ''

# Define path to export RT PLAN/DOSE to
dialog = FolderBrowserDialog()
dialog.Description = 'Select the path to export dose to (cancel to skip export):'
dialog.ShowNewFolderButton = True
if (dialog.ShowDialog() == DialogResult.OK):
    epath = dialog.SelectedPath
    
    # Ask user if they wish to export beams
    if (MessageBox.Show('Export beam doses? Beamset doses are always exported', 'Export Beam Dose', \
            MessageBoxButtons.YesNo) == DialogResult.Yes):
        beams = True
    else:
        warning('Beam dose export disabled')
        beams = False

else:
    warning('Folder not selected, export will be skipped')
    epath = ''
    beams = False
    
# Get current patient and case
patient = get_current('Patient')
case = get_current('Case')

# Import plan
if ipath != '':
    patient.ImportDicomDataFromPath(CaseName = case.CaseName, Path = ipath, \
        SeriesFilter = {}, ImportFilters = [])
    patient.Save()

# Loop through plans, update calc grid, and export
for plan in case.TreatmentPlans:

    # Load plan
    plans = case.QueryPlanInfo(Filter = {'Name': plan.Name})
    plan = case.LoadPlan(PlanInfo = plans[0])

    # Set dose grid to 2 mm
    plan.SetDefaultDoseGrid(VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2})
    patient.Save()

    # Calculate plan
    beamset = plan.BeamSets[0];
    beamset.SetCurrent();
    try:
        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
        patient.Save()

    except SystemError as error:
        warning(str(error))

    # Export plan
    if epath != '':
        try:
            if beams:
                case.ScriptableDicomExport(ExportFolderPath=epath, \
                    BeamSets=[beamset.BeamSetIdentifier()], \
                    BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                    BeamDosesForBeamSets=[beamset.BeamSetIdentifier()], \
                    DicomFilter='', IgnorePreConditionWarnings=True)
            else:
                case.ScriptableDicomExport(ExportFolderPath=epath, \
                    BeamSets=[beamset.BeamSetIdentifier()], \
                    BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                    DicomFilter='', IgnorePreConditionWarnings=True)
    
        except SystemError as error:
            warning(str(error))
