""" DICOM Export Functions

   This script is a PySide6-based GUI for exporting DICOM data from a radiation therapy treatment planning system.

    Test Patient:
        MRN VMA Large_RS Upgrade - Tested on 2025-06-20 by applying script and checking result in ARIA
            * Tested PRDR Dose Rate
            * Tested Overriding the Export Machine Name in RayStation with User selected
            * Couch position [0, 100, 0] working
            * SRS coords are working
            * RPM Gated Treatment is working
    TODO:

"""

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '0.2.0'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'

import sys
from PySide6.QtWidgets import (
    QApplication, QMessageBox, QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QGroupBox,
    QWidget, QLabel, QCheckBox, QRadioButton, QComboBox, QDialogButtonBox, QListView, QStyleFactory
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPalette, QColor
from PySide6.QtCore import Qt
import logging
import time
import math

import connect
import UserInterface
import DicomExport
import TomoExport

# Available filter options
RADIO_ON = True
RADIO_OFF = False
ENABLED = True
DISABLED = False
EXPORT_OPTIONS = {
    # Enabled in the script and defaulted to yes
    'ADJUST_ELECTRON_DOSERATE': ('Adjust Electron Dose Rate', RADIO_ON, ENABLED, ['Electrons']),
    'USE_PRDR_DOSERATE': ('Use PRDR Dose Rate', RADIO_ON, ENABLED, ['PRDR']),
    'ARIA_COMPATIBILITY_MODE': ('Apply ARIA compatibility filters (excludes dose, modifies prescription)',
                                RADIO_ON, ENABLED, []),
    'UPDATE_SETUP_BEAMS': ('Update Setup Beams', RADIO_ON, ENABLED, ['Photons', 'Electrons']),
    # Enabled in the script but defaulted to no
    'USE_GATED': ('Internal Target RPM Gated Treatment (NOT ALIGN RT)',
                  RADIO_OFF, ENABLED, ['Photons', 'Electrons']),
    'NO_REF_POINT_LOCATION': ('Reference Point has no geometric location', RADIO_OFF, ENABLED, []),
    'USE_SRS_COORDS': ('Use SRS table calculation', RADIO_OFF, ENABLED, ['Photons', 'Electrons']),
    # Filters that are currently disabled in the script
    'COPY_ELECTRON_BLOCK_NAME_TO_ID': ('Copy Electron Block Name to ID', RADIO_ON, DISABLED, ['Electrons']),
    'APPLY_BLOCK_ACCESSORY_TO_ELECTRON_FIELDS': (
        'Apply Block Accessory to Electron Fields', RADIO_ON, DISABLED, ['Electrons']),
    'CREATE_TRANSFER_PLAN': ('Create Transfer Plan', RADIO_ON, DISABLED, ['Tomo']),
    'APPLY_MACHINE_NAME_CHANGE': ('Apply Machine Name Change', RADIO_OFF, DISABLED, []),
    'ROUND_JAWS': ('Round Jaws', RADIO_ON, DISABLED, ['Photons', 'Electrons']),
    'SET_PA_AUTOMATICALLY': ('Set PA Automatically', RADIO_ON, DISABLED, ['Photons']),
    'IGNORE_MACHINE': ('Ignore machine name', RADIO_OFF, DISABLED, []),
}


def _ensure_app():
    """Ensure a QApplication exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        apply_dark_fusion_theme(app)
    return app


def WarningBox(message: str, title: str = "Warning") -> None:
    """Show a modal warning dialog with a single OK button.

    Args:
        message: The text to display in the warning.
        title:   The window title for the dialog.
    """
    _ensure_app()
    dlg = QMessageBox()
    dlg.setIcon(QMessageBox.Warning)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QMessageBox.Ok)
    dlg.exec()


def apply_dark_fusion_theme(app: QApplication):
    """Apply a true dark Fusion theme with custom colors and tooltips."""
    # 1) Switch to Fusion
    app.setStyle(QStyleFactory.create("Fusion"))

    # 2) Build a dark palette
    darkPalette = QPalette()
    darkPalette.setColor(QPalette.Window, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.WindowText, Qt.white)
    darkPalette.setColor(QPalette.Base, QColor(25, 25, 25))
    darkPalette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ToolTipBase, Qt.white)
    darkPalette.setColor(QPalette.ToolTipText, Qt.white)
    darkPalette.setColor(QPalette.Text, Qt.white)
    darkPalette.setColor(QPalette.Button, QColor(53, 53, 53))
    darkPalette.setColor(QPalette.ButtonText, Qt.white)
    darkPalette.setColor(QPalette.BrightText, Qt.red)
    darkPalette.setColor(QPalette.Link, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkPalette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(darkPalette)

    # 3) Tweak only tooltips via stylesheet
    app.setStyleSheet(
        "QToolTip { "
        "color: #ffffff; "
        "background-color: #2a82da; "
        "border: 1px solid white; "
        "}"
    )


class MultiSelectComboBox(QComboBox):
    """A QComboBox whose popup items are checkable, allowing multi-selection."""

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        # Use a QListView to render our items with checkboxes
        self.setView(QListView(self))
        # Set up a model to hold items
        model = QStandardItemModel(self)
        for text in items:
            item = QStandardItem(text)
            # Make each item user-checkable
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setData(Qt.Unchecked, Qt.CheckStateRole)
            model.appendRow(item)
        self.setModel(model)
        # Prevent popup closing on click
        self.view().pressed.connect(self._on_item_pressed)

    def _on_item_pressed(self, index):
        """Toggle the clicked item's state without closing the popup."""
        item = self.model().itemFromIndex(index)
        new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
        item.setCheckState(new_state)

    def selected_items(self) -> list[str]:
        """Return a list of texts of all checked items."""
        out = []
        mdl = self.model()
        for row in range(mdl.rowCount()):
            itm = mdl.item(row)
            if itm.checkState() == Qt.Checked:
                out.append(itm.text())
        return out


class QuestionBoxResult:
    """Simple container so callers can do `if result.yes:`."""

    def __init__(self, yes: bool):
        self.yes = yes


def QuestionBox(prompt: str, title: str = "Question") -> QuestionBoxResult:
    """Show a modal question dialog with Yes/No buttons.

    Args:
        prompt: The question text.
        title:  The window title for the dialog.

    Returns:
        QuestionBoxResult with `.yes == True` if user clicked Yes.
    """
    _ensure_app()
    ret = QMessageBox.question(
        None,
        title,
        prompt,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    return QuestionBoxResult(yes=(ret == QMessageBox.Yes))


class InputDialog(QDialog):
    """Dynamic form dialog supporting 'check' and 'combo' fields.

    Mimics UserInterface.InputDialog(inputs, datatype, options, initial, required, title)

    Args:
        inputs:   dict key: label text
        datatype: dict key: 'check' or 'combo'
        options:  dict key: list of choices
        export_options: dict of export options with keys as option names and values as tuples
        initial:  dict key: initial value (string for combo, list for check)
        required: list of keys which must be non-empty on OK
        title:    window title
    """

    def __init__(self,
                 inputs: dict,
                 datatype: dict,
                 options: dict,
                 export_options: dict,
                 initial: dict,
                 required: list,
                 title: str = "Input",
                 warning: str | None = None):
        _ensure_app()
        super().__init__(None)
        self.setWindowTitle(title)
        self.inputs = inputs
        self.datatype = datatype
        self.options = options
        self.warning = warning
        self.export_options = export_options
        self.initial = initial
        self.required = required
        self.widgets: dict[str, list] = {}
        logging.debug(f'Initializing InputDialog with inputs: {inputs}, datatype: {datatype}, '
                      f'options: {options}, export_options: {export_options}, initial: {initial}, '
                      f'required: {required}, title: {title}, warning: {warning}')

        self._build_ui()

    def _build_ui(self):
        """Construct the dialog layout, grouping all export-filter combos and radios under one warning box."""
        form = QFormLayout(self)

        # Collect filter keys and build all non-filter inputs first
        filter_keys = []
        for key, label in self.inputs.items():
            if key in self.export_options:
                filter_keys.append(key)
                continue

            dtype = self.datatype[key]
            if dtype == "check":
                # multiple select checkboxes
                container = QWidget(self)
                checks_layout = QVBoxLayout(container)
                cbs = []
                for choice in self.options[key]:
                    cb = QCheckBox(choice, container)
                    if key in self.initial and choice in self.initial[key]:
                        cb.setChecked(True)
                    checks_layout.addWidget(cb)
                    cbs.append(cb)
                self.widgets[key] = cbs
                form.addRow(label, container)

            elif dtype == "combo":
                # single select combo box
                combo = QComboBox(self)
                combo.addItems(self.options[key])
                if key in self.initial and self.initial[key] in self.options[key]:
                    combo.setCurrentIndex(self.options[key].index(self.initial[key]))
                self.widgets[key] = combo
                form.addRow(label, combo)

            elif dtype == "multicombo":
                # mulitple select combo box
                ms = MultiSelectComboBox(self.options[key], self)
                self.widgets[key] = ms
                form.addRow(label, ms)

            elif dtype == "radio":
                # non-exported radios, if any exist outside export_options
                container = QWidget(self)
                hbox = QHBoxLayout(container)
                yes_rb = QRadioButton("Yes", container)
                no_rb = QRadioButton("No", container)
                if key in self.initial and self.initial[key] == "Yes":
                    yes_rb.setChecked(True)
                else:
                    no_rb.setChecked(True)
                hbox.addWidget(yes_rb)
                hbox.addWidget(no_rb)
                self.widgets[key] = {"yes": yes_rb, "no": no_rb, "group": container}
                form.addRow(label, container)
                if key == "NO_FILTERS":
                    yes_rb.toggled.connect(lambda checked: self._on_no_filters_toggled(checked))

            else:
                raise ValueError(f"Unsupported datatype '{dtype}' for key '{key}'")

        # Now build one QGroupBox for all export-filter radios (and combos, if any)
        if filter_keys:
            # Create one GroupBox…
            gb = QGroupBox("Beamset Filters", self)
            # …but use a QFormLayout so every row lines up
            gb_layout = QFormLayout(gb)

            # 1) Warning label spans both columns
            warning_text_color = QApplication.palette().color(QPalette.BrightText).name()
            warning_label = QLabel(self.warning or "! These settings apply to *all* exported beamsets", gb)
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet(f"color: {warning_text_color}; font-weight: bold;")
            gb_layout.addRow(warning_label)

            # 2) One row per filter key: label in col 1, yes/no container in col 2
            for key in filter_keys:
                text, default_on, enabled = self.export_options[key]

                # Build the Yes/No widget container
                container = QWidget(gb)
                row_layout = QHBoxLayout(container)
                row_layout.setContentsMargins(0, 0, 0, 0)
                yes_rb = QRadioButton("Yes", container)
                no_rb = QRadioButton("No", container)
                yes_rb.setEnabled(enabled)
                no_rb.setEnabled(enabled)
                yes_rb.setChecked(default_on)
                no_rb.setChecked(not default_on)
                row_layout.addWidget(yes_rb)
                row_layout.addWidget(no_rb)
                row_layout.addStretch(1)  # push buttons left

                # Register the widgets for later
                self.widgets[key] = {"yes": yes_rb, "no": no_rb, "group": container}

                # Add a proper two-column row
                gb_layout.addRow(text, container)

            # Finally, add the whole group-box to your main form
            form.addRow(gb)

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _on_no_filters_toggled(self, checked: bool):
        """Disable all other radio widgets when NO_FILTERS is on; restore defaults when off."""
        for key, (label, default_on, enabled) in self.export_options.items():
            widget = self.widgets.get(key)
            if widget:
                widget['yes'].setEnabled(not checked)
                widget['no'].setEnabled(not checked)
                if checked:
                    widget['yes'].setChecked(False)
                    widget['no'].setChecked(True)
                else:
                    # restore original default from initial
                    if self.initial.get(key) == 'Yes':
                        widget['yes'].setChecked(True)
                        widget['no'].setChecked(False)
                    else:
                        widget['yes'].setChecked(False)
                        widget['no'].setChecked(True)

    def _on_accept(self):
        # Validate required fields
        for key in self.required:
            w = self.widgets.get(key)
            if isinstance(w, list):  # checkboxes
                if not any(cb.isChecked() for cb in w):
                    QMessageBox.warning(self, "Input Required",
                                        f"At least one of '{self.inputs[key]}' must be checked.")
                    return
            elif isinstance(w, MultiSelectComboBox):
                if not w.selected_items():
                    QMessageBox.warning(self, "Input Required",
                                        f"Please select one or more values for '{self.inputs[key]}'.")
                    return
            elif isinstance(w, dict) and 'yes' in w:  # radio buttons
                # No need to check; always one selected (unless disabled manually, which we aren't doing)
                continue
            else:  # combo
                if not w.currentText():
                    QMessageBox.warning(self, "Input Required", f"Please select a value for '{self.inputs[key]}'.")
                    return
        self.accept()

    def run(self) -> dict:
        """Display the dialog and return a dict of responses, or {} if cancelled."""
        result = self.exec()
        if result != QDialog.Accepted:
            return {}

        out = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, list):  # checkboxes
                out[key] = [cb.text() for cb in widget if cb.isChecked()]
            elif isinstance(widget, MultiSelectComboBox):
                out[key] = widget.selected_items()  # get all selected items
            elif isinstance(widget, dict) and 'yes' in widget:  # radio buttons
                out[key] = True if widget['yes'].isChecked() else False
            else:  # combo
                out[key] = widget.currentText()
        return out


def check_approval_status(patient, case, exam, plan, beamset):
    ignore = False
    if beamset is not None:
        # Plan approval check
        try:
            if hasattr(beamset, 'Review'):
                beamset_approval = True if beamset.Review.ApprovalStatus == 'Approved' else False
            else:
                logging.debug('Beamset does not have a Review attribute')
                beamset_approval = False
        except Exception as e:
            logging.debug(f'Could not check plan approval status: {e}')
            beamset_approval = False

        # TODO: Find where these are hiding in 2024a
        # if beamset_approval:
        #     try:
        #         for plan_opt in plan.PlanOptimizations:
        #             for opt_bs in plan_opt.OptimizedBeamSets:
        #                 if opt_bs.DicomPlanLabel == beamset.DicomPlanLabel:
        #                     blocked_rois = [
        #                         roi.Name
        #                         for roi in opt_bs.BeamCreationRules.RoisEnableForPlanning
        #                         if roi.OrganData.OrganType != 'Target'
        #                     ]
        #                     logging.debug(f'Attempting to include {blocked_rois}')
        #                     include_in_export(case, blocked_rois)
        #                     patient.Save()
        #                     break
        #     except AttributeError:
        #         logging.debug('Could not toggle export status of any blocked rois because plan is not approved')
        # else:
        #     approve = QuestionBox(
        #         'The selected plan is not currently approved. Would you like to approve it prior to export?',
        #         'Approve Plan'
        #     )
        #     if approve.yes:
        #         ui = connect.get_current('ui')
        #         try:
        #             ui.TitleBar.Navigation.MenuItem['Plan evaluation'].Click()
        #             ui.TitleBar.Navigation.MenuItem['Plan evaluation'].Popup.MenuItem['Plan evaluation'].Click()
        #             ui.TabControl_ToolBar.TabItem._Approval.Select()
        #         except Exception as e:
        #             logging.debug(f'Could not navigate to plan approval tab: {e}')
        #         connect.await_user_input('Approve the plan now, then continue the script')
        #     else:
        #         logging.warning('The user chose to export the plan without approval')
        #         ignore = True

        # Structure approval check
        try:
            if hasattr(beamset.DependentSubStructureSet, 'Review'):
                struct_approved = (
                        beamset.DependentSubStructureSet.Review.ApprovalStatus == 'Approved'
                )
            else:
                struct_approved = False
        except Exception:
            logging.debug('Could not check structure approval status')
            struct_approved = False

        if not struct_approved:
            approve = QuestionBox(
                'The selected structure set is not currently approved. Would you like to approve it prior to export?',
                'Approve Structure Set'
            )
            if approve.yes:
                ui = connect.get_current('ui')
                ui.TitleBar.Navigation.MenuItem['Patient modeling'].Click()
                ui.TitleBar.Navigation.MenuItem['Patient modeling'].Popup.MenuItem['Structure definition'].Click()
                ui.TabControl_ToolBar.TabItem['Approval'].Select()
                connect.await_user_input('Approve the structure set now, then continue the script')
            else:
                logging.warning('The user chose to export the structure set without approval')
                ignore = True
    return ignore


def rs_get_DicomExportProperties(beamset):
    """ Determine if the attribute exists and return the DicomExport properties for the beamset. """
    export_properties = {'ExportedTreatmentMachineName': None,
                         'UseStereotacticApplicatorTypeForPhotonCones': None, }
    if hasattr(beamset, 'DicomExportProperties'):
        if hasattr(beamset.DicomExportProperties, 'ExportedTreatmentMachineName'):
            export_properties['ExportedTreatmentMachineName'] = \
                beamset.DicomExportProperties.ExportedTreatmentMachineName
        if hasattr(beamset.DicomExportProperties, 'UseStereotacticApplicatorTypeForPhotonCones'):
            export_properties['UseStereotacticApplicatorTypeForPhotonCones'] = \
                beamset.DicomExportProperties.UseStereotacticApplicatorTypeForPhotonCones

    return export_properties


def test_get_exported_treatment_machine_name(beamset):
    """Test function to verify the exported machine name retrieval."""
    machine_name = rs_get_DicomExportProperties(beamset).get('ExportedTreatmentMachineName', None)
    if machine_name is None:
        WarningBox(
            'The exported treatment machine name could not be retrieved from the beamset DicomExportProperties.',
            'Exported Machine Name Not Found'
        )
    return machine_name


def get_exported_machine_name(beamset):
    """Return the exported machine name for the given beamset."""
    test_get_exported_treatment_machine_name(beamset)
    machine_name = rs_get_DicomExportProperties(beamset).get('ExportedTreatmentMachineName')
    return machine_name


def reorder_machine_names(beamset, machine_list, machine_name=None):
    """Given the list of possible machine names in the machine list, determein if the plan already
       has a delivery system selected, and if so, reorder the list so that the selected is first,
       if not, return the list as is."""
    if not machine_name:
        machine_name = get_exported_machine_name(beamset)
    if machine_name is not None and machine_name in machine_list:
        # Move the selected machine to the front of the list
        machine_list.remove(machine_name)
        machine_list.insert(0, machine_name)
    return machine_list


def filter_export_options_based_on_beamset(plan):
    """Filter the EXPORT_OPTIONS based on the type of beamset."""
    electron_beamset_present = False
    tomo_beamset_present = False
    vmat_3D_present = False
    prdr = False
    filtered_options = {}
    for beamset in plan.BeamSets:
        if 'Tomo' in beamset.DeliveryTechnique:
            tomo_beamset_present = True
        if 'Tomo' not in beamset.DeliveryTechnique and beamset.Modality == 'Photons':
            vmat_3D_present = True
        if beamset.Modality == 'Electrons':
            electron_beamset_present = True
        if '_PRD_' in beamset.DicomPlanLabel or '_PRD_' in plan.Name:
            prdr = True
    # Filter the EXPORT_OPTIONS based on beamset type
    for key, (label, default_on, enabled, beamset_types) in EXPORT_OPTIONS.items():
        if not beamset_types:
            filtered_options[key] = (label, default_on, enabled)
        elif electron_beamset_present and 'Electrons' in beamset_types:
            filtered_options[key] = (label, default_on, enabled)
        elif tomo_beamset_present and 'Tomo' in beamset_types:
            filtered_options[key] = (label, default_on, enabled)
        elif vmat_3D_present and 'Photons' in beamset_types:
            filtered_options[key] = (label, default_on, enabled)
        if prdr and 'PRDR' in beamset_types:
            filtered_options[key] = (label, default_on, enabled)

    return filtered_options


def main():
    # TODO: Switch filters to radio buttons and autopopulate. If user selects no filters then all filters are
    #       disabled.
    # Get current patient, case, exam, plan, and beamset
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
    except Exception:
        WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    try:
        plan = connect.get_current('Plan')
        beamset = connect.get_current('BeamSet')

        beamset_list = [b.DicomPlanLabel for b in plan.BeamSets]
        machine_list = DicomExport.machines(beamset)
        exported_machine_name = get_exported_machine_name(beamset)
        sorted_machine_list = reorder_machine_names(beamset, machine_list, exported_machine_name)

    except Exception:
        logging.debug('A plan and/or beamset is not loaded; plan export options will be disabled')
        plan = None
        beamset = None
        beamset_list = []
        exported_machine_name = None
        sorted_machine_list = []

    filtered_export_options = filter_export_options_based_on_beamset(plan)

    # Start timer
    tic = time.time()
    #
    # Initialize script status (skipping replacement for now)
    status = UserInterface.ScriptStatus(
        steps=[
            'Approve and save structures/plan',
            'Select DICOM data and destination',
            'Apply filters and export'
        ],
        docstring=__doc__,
        help=__help__
    )

    # Check if plan and/or structure set is approved
    status.next_step(
        text='Prior to export, this script will check if the plan is approved, and will ask if want to '
             'do so prior to approval if not.')
    time.sleep(1)
    patient.Save()

    # Check approval status:
    ignore = check_approval_status(patient, case, exam, plan, beamset)

    if hasattr(beamset, 'DeliveryTechnique') and "Tomo" in beamset.DeliveryTechnique:
        status.aborted()
        TomoExport.export_tomo_plan(patient=patient,
                                    exam=exam,
                                    case=case,
                                    parent_plan=plan,
                                    parent_beamset=beamset,
                                    script_status=status,
                                    rs_test_only=False)

    status.next_step(
        text='The plan and structure set approval status has been checked. If you wish to export without approval, '
             'you can do so now.'
    )

    # Prepare export dialog
    inputs = {
        'dicom_export_selections': 'Select which data elements to export:',
        'beamset_selections': 'Select which beamsets to export:',
        'destination_selections': 'Check one or more DICOM destinations to export to:',
        'ignore_warnings': 'Ignore DICOM export warnings:'
    }
    required = ['dicom_export_selections', 'destination_selections', 'ignore_warnings']
    types = {'dicom_export_selections': 'check',
             'beamset_selections': 'multicombo',
             'destination_selections': 'check',
             'ignore_warnings': 'combo'}
    options = {
        'dicom_export_selections': ['CT', 'Structures'],
        'destination_selections': DicomExport.destinations(),
        'beamset_selections': beamset_list,
        'ignore_warnings': ['Yes', 'No']
    }
    initial = {'dicom_export_selections': ['CT', 'Structures'],
               'beamset_selections': [], 'ignore_warnings': 'Yes'}
    # if ignore:
    if beamset is not None and len(DicomExport.machines(beamset)) > 0:
        options['dicom_export_selections'] += ['Beam Set(s)', 'Beam Set Dose(s)', 'Beam Dose(s)']
        # Delivery system selection
        inputs['delivery_system_selection'] = 'Select which delivery system to export as:'
        required.append('delivery_system_selection')
        types['delivery_system_selection'] = 'combo'
        options['delivery_system_selection'] = sorted_machine_list
        if len(options['delivery_system_selection']) == 1:
            initial['delivery_system_selection'] = options['delivery_system_selection'][0]
        # Add export options
        # Dynamically construct radio button export options
        for key, (label, default_on, enabled) in filtered_export_options.items():
            if enabled:
                inputs[key] = label
                types[key] = 'radio'
                options[key] = ['Yes', 'No']
                initial[key] = 'Yes' if default_on else 'No'
                required.append(key)
        # Manually add NO_FILTERS option (it's a global override, not part of EXPORT_OPTIONS)
        inputs['NO_FILTERS'] = 'Disable all export filters:'
        types['NO_FILTERS'] = 'radio'
        options['NO_FILTERS'] = ['Yes', 'No']
        initial['NO_FILTERS'] = 'No'
        required.append('NO_FILTERS')
    logging.debug(f'Made it to dialog construction with inputs: {inputs}, types: {types}, options: {options}, ')

    # Show dialog
    dialog = InputDialog(
        inputs=inputs,
        datatype=types,
        options=options,
        export_options=filtered_export_options,
        initial=initial,
        required=required,
        title='Export DICOM Data',
        warning='These settings will apply to all exported beamsets, '
                'if a filter is inappropriate for a beamset, export it separately.'
    )
    response = dialog.run()
    if response == {}:
        status.finish('DICOM export was cancelled')
        sys.exit('DICOM export was cancelled')
    else:
        logging.debug(f'User selected: {response}')
    if response.get('NO_FILTERS'):
        for key in filtered_export_options:
            response[key] = False
        logging.info("NO_FILTERS selected: all export filters disabled in response.")

    # Execute DicomExport.send() given user response
    status.next_step(text='The DICOM datasets are now being exported to a temporary directory, converted to a ' +
                          'treatment delivery system, and sent to the selected destination. Please be patient, as ' +
                          'this can take several minutes...')
    filters = []
    for key in filtered_export_options:
        if response.get(key):
            filters.append(key)

    if response['ignore_warnings'] == 'Yes':
        ignore = True
        logging.debug('User choose to ignore warnings during DICOM export')

    if beamset is not None:
        f = []

        # Disable filtering for Tomo and RayGateway
        if 'Tomo' in beamset.DeliveryTechnique:
            transfer_plan = response.get('CREATE_TRANSFER_PLAN', False)
            if transfer_plan:
                f.append('duplicate')
            else:
                f = None
            filters = ['x'] * 7
            initial_table_position = None
            response['delivery_system_selection'] = None

        else:
            # No filters if option 3 selected
            if response.get('NO_FILTERS'):
                logging.info('User selected to disable all filters in export')
                f = None
                response['delivery_system_selection'] = None
                # Set Couch
                initial_table_position = None
            else:
                if response.get('delivery_system_selection'):
                    user_machine_name = response['delivery_system_selection']
                    if user_machine_name != exported_machine_name:
                        logging.info(f'User selected {user_machine_name} as delivery system for export, overriding '
                                     f'current machine {exported_machine_name}')
                    else:
                        logging.info(f'User selected {user_machine_name} as delivery system for export, '
                                     f'matching current machine, enabling RayStation export filter')
                        response['delivery_system_selection'] = None
                # if response.get('IGNORE_MACHINE'):
                #     f.append('machine')
                #     logging.info('User will apply machine name change to exported plans')
                if response.get('USE_GATED'):
                    logging.info('User will apply Use Gated tag to RTPlan')
                else:
                    logging.info('No internal gating selected for RTPlan')
                if response.get('NO_REF_POINT_LOCATION'):
                    logging.info('User disabled reference point location definition in export')
                else:
                    logging.info('Reference point location preserved in export')
                if response.get('USE_SRS_COORDS'):
                    use_srs_coords = True
                    logging.info('User indicates SRS table coordinates should be used')
                else:
                    use_srs_coords = False
                #
                # Filters to always be applied
                # Set Couch
                initial_table_position = [0, 1000, 0]  # Default
                frameless_beamnames = ['_FSR_', '_SRS_']

                if use_srs_coords or any(a in beamset.DicomPlanLabel for a in frameless_beamnames) and \
                        'HeadFirstSupine' in beamset.PatientSetup.OfTreatmentSetup.PatientPosition:
                    user_machine_name = response['delivery_system_selection']
                    alpha, beta, gamma = DicomExport.get_table_offsets(
                        to_machine=user_machine_name,
                        from_machine=beamset.MachineReference.MachineName,
                        device_name='QFix_Brain_TBCouch_F2andF3',
                        immobilization_type='Frameless')
                    #
                    # Determine if the DICOM origin was chosen for the set-up location
                    poi_geometry = beamset.PatientSetup.PatientSetupDevice.SetupReferencePoint
                    poi_coordinates = [poi_geometry.Point.x,
                                       poi_geometry.Point.y,
                                       poi_geometry.Point.z]
                    if all(math.isclose(c, 0) for c in poi_coordinates):
                        iso_lat = beamset.Beams[0].Isocenter.Position.x
                        iso_vert = beamset.Beams[0].Isocenter.Position.y
                        iso_long = beamset.Beams[0].Isocenter.Position.z
                        initial_table_position = [
                            (alpha + iso_vert) * 10.,  # ARIA imports in mm and displays in cm
                            (beta - iso_long) * 10.,
                            (gamma - iso_lat) * 10.,
                        ]
                    else:
                        WarningBox(
                            'The set-up reference point is not at the DICOM origin. '
                            'The table position will not be updated to match the isocenter.'
                        )
                logging.debug(f'For {user_machine_name}: Table positions will be updated to {initial_table_position}')

    else:
        f = None
        initial_table_position = None
        response['delivery_system_selection'] = None

    success = DicomExport.send(case=case,
                               destination=response['destination_selections'],
                               exam=exam,
                               beamset=[b for b in plan.BeamSets if b.DicomPlanLabel in response['beamset_selections']],
                               ct='CT' in response['dicom_export_selections'],
                               structures='Structures' in response['dicom_export_selections'],
                               plan='Beam Set(s)' in response['dicom_export_selections'],
                               plan_dose='Beam Set Dose(s)' in response['dicom_export_selections'],
                               beam_dose='Beam Dose(s)' in response['dicom_export_selections'],
                               qa_plan=None,
                               ignore_warnings=response.get('ignore_warnings', 'No') == 'Yes',
                               ignore_errors=False,
                               bypass_export_check=False,
                               rename=None,
                               machine=response.get('delivery_system_selection', None),
                               table=initial_table_position,
                               pa_threshold=response.get('SET_PA_AUTOMATICALLY', False),
                               round_jaws=response.get('ROUND_JAWS', False),
                               aria_compatibility_mode=response.get('ARIA_COMPATIBILITY_MODE', False),
                               no_ref_point_location=response.get('NO_REF_POINT_LOCATION', False),
                               block_accessory=response.get('APPLY_BLOCK_ACCESSORY_TO_ELECTRON_FIELDS', False),
                               block_tray_id=response.get('COPY_ELECTRON_BLOCK_NAME_TO_ID', False),
                               prdr_dr=response.get('USE_PRDR_DOSERATE', False),
                               rpm_gating=response.get('USE_GATED', False),
                               setup_beam_filter=response.get('UPDATE_SETUP_BEAMS', False),
                               electron_dose_rate_filter=response.get('ADJUST_ELECTRON_DOSERATE', False),
                               bar=True)

    # Finish up
    if success:
        logging.info('Export script completed successfully in {:.3f} seconds'.format(time.time() - tic))
        status.finish(text='DICOM export was successful. You can now close this dialog.')

    else:
        logging.warning('Export script completed with errors in {:.3f} seconds'.format(time.time() - tic))
        status.finish(text='DICOM export finished but with errors. You can now close this dialog.')


if __name__ == '__main__':
    main()
