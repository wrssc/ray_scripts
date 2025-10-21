""" Check Beamset Clearance
    Visualize and audit gantry‑to‑patient/support clearance about the isocenter for TrueBeam and Tomo plans.
    Uses the same analytic cylinder model and ROI voxelization pipeline as
    `PlanReview.qa_tests.test_beamset.check_isocenter_clearance`.
    Produces per‑beam angle summaries (PASS/ALERT/FAIL) and optional plots of blocked gantry ranges.

    Version:
    0.0 Prototype using analytic cylinder model and grouped beam evaluation
    1.0 Release


    Inputs:
      - rso: RayStation ScriptObjects (NamedTuple of [case, exam, plan, beamset, db])
      - tolerance overrides (optional): collision/alert, and optional head diameter override
      - plotting options (optional): show/save path, downsampling thresholds, labels
      - testing (optional): enable synthetic gantry sweeps

    Outputs:
      - PASS/ALERT/FAIL status and a concise message summarizing blocked ranges
      - Optional figures per beam‑group (couch, isocenter) showing blocked gantry angles
      - Optional CSV/JSON summary of per‑beam blocked angle ranges

    Methods and Key Ideas:
      - Clearance geometry for TrueBeam is modeled as a finite cylinder (head length and cover diameter),
        positioned along the beam central axis at each gantry angle with offsets set by collision/alert tolerances.
      - ROIs (External, Support, Fixation) are converted to voxel coordinates and transformed into an
        isocentric room frame (patient orientation + couch rotation).
      - Beams are grouped by [couch angle, isocenter] to avoid redundant computations across beams
        sharing the same geometry; unique gantry angles are evaluated once per group.
      - Collisions are determined vectorially by testing whether any ROI voxel lies inside the cylinder
        for each angle; angles are then mapped back to individual beams and collapsed into contiguous ranges.

    Coordinate Conventions:
      - Points are shifted to isocenter, then transformed from patient to room frame using patient position
        via `get_orientation_transform(orientation)`.
      - A couch rotation about +Y (DICOM sign convention) is applied.
      - Varian IEC gantry angles are converted to standard cylindrical math for axis vectors:
          phi = rad((360 - (angle - 90)) % 360)
          d = \[cos(phi), sin(phi), 0\]

    Pseudocode:
      1. Resolve machine clearance parameters:
         clearance = get_clearance_roi_name_and_diameter(
             rso,
             collision_tolerance=override_collision,
             alert_tolerance=override_alert,
             head_length=None,
             head_diameter=head_diameter_override
         )
      2. Identify ROIs to check:
         external, supports = find_externals_and_supports(rso)
         rois = \[external\] + supports
         if rois empty -> return ALERT ("No Supports or External found")
      3. Voxelize ROIs:
         rois_checked = extract_voxel_representation(rso, rois)
         if empty -> return ALERT ("No valid ROIs")
      4. If Tomo plan (clearance['roi_name'] contains "Tomo"):
         - beam_name = first beam
         - pts_iso = shift_to_isocenter_and_couch_rotate_points(rso, roi_pts, beam_name, 'Points', couch_angle=0)
         - fail_mask, alert_mask = filter_in_bore_clearing_points_tomo(
               pts_iso,
               fail_diameter = clearance['diameter'] - 2 * clearance['collision_tolerance'],
               alert_diameter = clearance['diameter'] - 2 * clearance['alert_tolerance']
           )
         - Classify PASS/ALERT/FAIL based on any mask hits per ROI
         - Plot optional XY bore circle and flagged points along Z within couch travel
         - Return status and summary text
      5. Else (TrueBeam/VMAT/SMLC):
         - Group beams: groups = build_beam_groups(rso.beamset)
         - For each group (couch, iso):
             angles = sorted(unique angles in group)
             For each ROI:
               pts_iso = shift_to_isocenter_and_couch_rotate_points(rso, roi_pts, representative_beam, 'Points')
               h_fail  = clearance['diameter']/2 - clearance['collision_tolerance']
               h_alert = clearance['diameter']/2 - clearance['alert_tolerance']
               fail_masks, alert_masks = get_head_collision_masks(
                   points=pts_iso,
                   diameter=clearance['COVER_DIAMETER'],
                   head_length=clearance['head_length'],
                   offset_fail=h_fail,
                   offset_alert=h_alert,
                   gantry_angles=angles
               )
               fail_angles  = \{ ang for ang, mask in fail_masks.items()  if any(mask) \}
               alert_angles = \{ ang for ang, mask in alert_masks.items() if any(mask) \}
               Map angles back to per‑beam sweeps, collapse via group_overlapping_angles
         - Aggregate `bad_gantry_fail` and `bad_gantry_alert` across groups
         - Message = format_beam_collisions(bad_gantry_fail or bad_gantry_alert)
         - Status = FAIL if any fail ranges, else ALERT if any alert ranges, else PASS
         - Optional polar plot per group:
             • Draw alert/fail radial envelopes at isocenter
             • Overlay blocked angle arcs per beam (CW/CCW annotated)
             • Optionally scatter downsampled ROI points near collisions
      6. Return (status, message) and optionally save/export artifacts

    Performance Considerations:
      - Use `downsample_points` for large ROIs to accelerate plotting and masking.
      - Beam grouping minimizes repeated angle evaluations for shared couch/isocenter.

    TODO:
        Electrons: implement clearance model

    Dependencies:
      - RayStation scripting (`connect`)
      - NumPy, optional Matplotlib for plotting
      - `PlanReview.review_definitions` and `PlanReview.utils.contour_utilities.get_voxel_coordinates_direct_optimized`

    Validation:
      - Matches `check_isocenter_clearance` PASS/ALERT/FAIL outcomes for clinical test plans and fully tested
      against measurements. Jupyter notebook available on clinical system at
      http://localhost:8888/lab/tree/RAB034_Clearance_Check_BreastBoardMatrix.ipynb

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 2 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '08-Oct-2025'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '2025'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import numpy as np
import logging
from dataclasses import dataclass
from typing import Iterable, Tuple, Sequence, List, Dict, Optional, Callable
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from library.PlanReview.review_definitions import (
    SUPPORT_TOLERANCE_COLLISION, TRUEBEAM_MAX_DIAMETER, TRUEBEAM_COVER_DIAMETER,
    SUPPORT_TOLERANCE_ALERT, TRUEBEAM_HEAD_LENGTH, HDA_MAX_DIAMETER)
from library.PlanReview.qa_tests.test_beamset.check_isocenter_clearance import (
    shift_to_isocenter_and_couch_rotate_points, get_head_collision_masks, extract_voxel_representation,
    find_gantry_angular_traversal, filter_in_bore_clearing_points_tomo, build_beam_groups, )
from library.StructureOperations import find_types
from library.api.api_utils import find_scope


@dataclass(frozen=True, slots=True)
class RSO:
    """RayStation ScriptObjects container."""
    error: List[str]
    db: object  # PatientDB
    machine_db: object  # Machine
    case: object  # Case
    patient: object  # Patient
    exam: object  # Examination
    plan: object  # Plan
    beamset: object  # BeamSet


@dataclass
class BeamItem:
    """Payload for UI."""
    label: str
    title: str
    gantries: str
    good: np.ndarray  # (N,3)
    violate: np.ndarray  # (M,3)
    warn: np.ndarray  # (K,3)


@dataclass(frozen=True, slots=True)
class CollisionResults:
    """Results of collision classification for a set of points and angles."""
    fail_angles: List[float]
    warn_angles: List[float]
    violate: np.ndarray  # (M,3)
    warn: np.ndarray  # (K,3)
    good: np.ndarray  # (L,3)


def add_isocenter(ax):
    # dashed crosshair at origin
    ax.axhline(0, color="k", lw=0.8, ls=":", alpha=0.6, zorder=3)
    ax.axvline(0, color="k", lw=0.8, ls=":", alpha=0.6, zorder=3)
    # small marker and label
    ax.plot(0, 0, marker="o", ms=4, mfc="none", mec="k", zorder=4)
    ax.text(1.5, 1.5, "ISO", fontsize=8, color="k")  # offset in data units


def collect_roi_points(rso, roi_types: Sequence[str]) -> np.ndarray:
    """
    Collect points from all ROIs of specified types in the given case in patient coordinates.

    Args:
        rso: The RSO object containing the case and beamset.
        roi_types (Sequence[str]): List of ROI types to collect points from.

    Returns:
        (N, 3) numpy array of points in patient coordinates.
        """
    case = rso.case
    rois_to_check: List[str] = []
    for t in roi_types:
        rois_to_check += find_types(case=case, roi_type=t)
    rois_checked = extract_voxel_representation(rso, rois_to_check)
    arrays = [a for a in rois_checked.values() if a is not None and a.size]
    if arrays:
        vox_geom = np.concatenate(arrays, axis=0)
    else:
        vox_geom = np.empty((0, 3))
    return vox_geom


def transform_points_to_isocenter(rso, points: np.ndarray, beam_name: str) -> np.ndarray:
    """
    Shift and rotate points to isocenter coordinates for the specified beam.

    Args:
        rso: The RSO object containing the case and beamset.
        points (np.ndarray): (N, 3) array of points in patient coordinates.
        beam_name (str): Name of the beam to use for transformation.
    Returns:
        (N, 3) numpy array of points in isocenter coordinates.
    """
    if points.size == 0:
        return points
    return shift_to_isocenter_and_couch_rotate_points(rso, points, beam_name,
                                                      representation='Points')


def classify_collision_points_truebeam(
        pts_iso: np.ndarray,
        angles: np.ndarray,
) -> CollisionResults:
    """Classify points using analytic cylinder model for given gantry angles.

    Returns:
        results: dict with keys:
            'fail_angles': List of angles (deg) with collisions
            'warn_angles': List of angles (deg) with near-collisions
            'violate': (M,3) array of points inside collision cylinder
            'warn': (K,3) array of points inside alert cylinder but outside collision
            'good': (L,3) array of points outside alert cylinder
    """

    diameter = TRUEBEAM_COVER_DIAMETER
    length = TRUEBEAM_HEAD_LENGTH
    h_fail = TRUEBEAM_MAX_DIAMETER / 2.0 - SUPPORT_TOLERANCE_COLLISION
    h_warn = TRUEBEAM_MAX_DIAMETER / 2.0 - SUPPORT_TOLERANCE_ALERT

    if angles:
        masks_fail, masks_warn = get_head_collision_masks(
            pts_iso, diameter, length, h_fail, h_warn, angles
        )
        fail_angles = [ang for ang, hit in masks_fail.items() if any(hit)]
        warn_angles = [ang for ang, hit in masks_warn.items() if any(hit)]

        fail_any = _any_mask(masks_fail, angles, pts_iso)
        warn_any = _any_mask(masks_warn, angles, pts_iso)

        violate = pts_iso[fail_any]
        warn = pts_iso[warn_any & ~fail_any]
        good = pts_iso[~(fail_any | warn_any)]
    else:
        fail_angles = []
        warn_angles = []
        violate = np.empty((0, 3))
        warn = np.empty((0, 3))
        good = pts_iso

    return CollisionResults(fail_angles=fail_angles, warn_angles=warn_angles,
                            violate=violate, warn=warn, good=good)


def classify_points_tomo(pts_iso: np.ndarray) -> CollisionResults:
    """Classify points for Tomo delivery."""
    diameter = HDA_MAX_DIAMETER
    collision_tolerance = SUPPORT_TOLERANCE_COLLISION
    alert_tolerance = SUPPORT_TOLERANCE_ALERT
    fail_diameter = diameter - 2 * collision_tolerance  # cm
    alert_diameter = diameter - 2 * alert_tolerance  # cm
    fail_mask, warn_mask = filter_in_bore_clearing_points_tomo(pts_iso, fail_diameter=fail_diameter,
                                                               alert_diameter=alert_diameter)
    violate = pts_iso[fail_mask]
    warn = pts_iso[warn_mask & ~fail_mask]
    good = pts_iso[~(fail_mask | warn_mask)]
    return CollisionResults(fail_angles=[], warn_angles=[],
                            violate=violate, warn=warn, good=good)


def _any_mask(mask_dict: Dict[float, np.ndarray],
              angles: Optional[Iterable[float]],
              pts: Optional[np.ndarray]) -> np.ndarray:
    """Vectorized OR across angle masks. Returns (N,) bool."""
    n = len(pts) if pts is not None else next(iter(mask_dict.values())).size
    out = np.zeros(n, dtype=bool)
    if not mask_dict:
        return out
    if angles is None:
        for m in mask_dict.values():
            out |= m
    else:
        for a in angles:
            out |= mask_dict[a]
    return out


def angles_for_beam(beam_set, beam_name: str) -> Tuple[List[float], Optional[bool]]:
    """Return per-beam gantry angle list and clockwise flag for VMAT/SMLC."""
    delivery = beam_set.Beams[beam_name].DeliveryTechnique
    if "DynamicArc" in delivery:
        angles, clockwise = find_gantry_angular_traversal(beam_set, testing=False)[beam_name]
        return list(angles), bool(clockwise)
    if "SMLC" in delivery and beam_set.Modality == "Photons":
        return [beam_set.Beams[beam_name].GantryAngle], None
    return [], None  # Tomo or electrons handled upstream


def gantry_ranges_text(violate: list, warn: list) -> str:
    """Build fail/warn range strings for subtitle."""
    fail_s, warn_s = _get_failing_gantry_ranges(violate, warn)
    # Compact join while avoiding extra spaces.
    return "\n".join(s for s in (fail_s, warn_s) if s)


def _get_failing_gantry_ranges(violation_angles: list,
                               warning_angles: list) -> Tuple[str, str]:
    """Compute Varian IEC-like angle range strings from computed angles in degrees."""

    def _str_from_angle_list(angle_list, prefix):
        if len(angle_list) == 0:
            return ""
        s, _ = _gantry_string(angle_list, tol_deg=2, wrap=True)
        return f"{prefix}: " + s if s else ""

    return _str_from_angle_list(violation_angles, "Gantry angles with collisions"), \
        _str_from_angle_list(warning_angles, "Gantry angles with near-collisions")


def _gantry_string(cylindrical_angles: Iterable[float],
                   tol_deg: int = 1,
                   wrap: bool = False) -> Tuple[str, np.ndarray]:
    """Integer-round, merge consecutive degrees to ranges."""
    a = np.rint(np.asarray(cylindrical_angles, float)).astype(int) % 360
    if a.size == 0:
        return "", np.array([], dtype=int)
    uniq = np.array(sorted(set(a)), int)
    ranges: List[Tuple[int, int]] = []
    s = p = uniq[0]
    for v in uniq[1:]:
        if v - p <= tol_deg:
            p = v
            continue
        ranges.append((s, p))
        s = p = v
    ranges.append((s, p))
    if wrap and len(ranges) >= 2:
        fs, fe = ranges[0]
        ls, le = ranges[-1]
        if (fs <= 0 + tol_deg) and (le >= 359 - tol_deg):
            ranges = [(ls, fe)] + ranges[1:-1]
    parts = [f"({x})" if x == y else f"({x}-{y})" for x, y in ranges]
    return ", ".join(parts), uniq


ProgressFn = Callable[[int, int, str], None]  # (i, n_total, message)


def make_beam_items(
        rso,
        roi_types: Sequence[str] = ("Fixation", "Support", "External"),
        progress: Optional[ProgressFn] = None,
) -> List[BeamItem]:
    beam_set = rso.beamset
    pts_patient = collect_roi_points(rso, roi_types)
    beam_groups = build_beam_groups(beam_set)

    # compute total beams
    total = sum(len(g["beams"]) for g in beam_groups.values())
    i = 0
    items: List[BeamItem] = []

    for (couch_angle, isocenter), group in beam_groups.items():
        for b in group["beams"]:
            beam_name = b["name"]
            if progress:
                progress(i, total, f"Building {beam_name} (couch {couch_angle}°)")
            delivery = beam_set.Beams[beam_name].DeliveryTechnique
            modality = beam_set.Modality
            pts_iso = transform_points_to_isocenter(rso, pts_patient, beam_name)

            if "Tomo" in delivery:
                collision_results = classify_points_tomo(pts_iso)
            elif "SMLC" in delivery and modality == "Electrons":
                i += 1
                continue
            else:
                angles, _ = angles_for_beam(beam_set, beam_name)
                collision_results = classify_collision_points_truebeam(pts_iso, angles)

            plan_label = beam_set.DicomPlanLabel

            if "Tomo" in delivery:
                title = f"{plan_label}: {beam_name}"
                label = f"{beam_name} (Couch {couch_angle}°, ISO {tuple(round(v, 1) for v in isocenter)})"
                if collision_results.violate.any():
                    gantries = f"FAIL: points are detected that will result in a collision."
                elif collision_results.warn.any():
                    gantries = f"Warning: points are detected that may result in a collision."
                else:
                    gantries = "No collision points detected"
            else:
                title = f"{plan_label}: {beam_name}: Couch {couch_angle}°"
                label = f"{beam_name} (Couch {couch_angle}°, ISO {tuple(round(v, 1) for v in isocenter)})"
                gantries = gantry_ranges_text(collision_results.fail_angles, collision_results.warn_angles)

            items.append(BeamItem(label=label, title=title, gantries=gantries, good=collision_results.good,
                                  violate=collision_results.violate, warn=collision_results.warn))
            i += 1

    if progress:
        progress(total, total, "Done")
    return items


def plot_collisions(rso) -> None:
    # build with GUI progress, then launch viewer
    items = _build_items_with_progress_gui(rso)
    if not items:
        return
    _launch_beam_viewer(items)
    return


# GUI
def _launch_beam_viewer(items) -> None:
    """Start a minimal PySide6 viewer for per-beam paging."""
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton
    )
    import sys

    created_here = False
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        created_here = True

    class BeamViewer(QMainWindow):
        def __init__(self, items):
            super().__init__()
            self.items = items
            self.idx = 0

            central = QWidget()
            self.setCentralWidget(central)
            v = QVBoxLayout(central)

            # controls
            ctrl = QHBoxLayout()
            self.prev_btn = QPushButton("Prev")
            self.next_btn = QPushButton("Next")
            self.combo = QComboBox()
            self.combo.addItems([it.label for it in items])
            ctrl.addWidget(self.prev_btn)
            ctrl.addWidget(self.next_btn)
            ctrl.addWidget(self.combo)
            v.addLayout(ctrl)

            # canvas + toolbar
            self.fig = Figure(figsize=(12, 4), constrained_layout=True)
            self.axes = [self.fig.add_subplot(1, 3, i + 1) for i in range(3)]
            self.canvas = FigureCanvasQTAgg(self.fig)
            self.toolbar = NavigationToolbar2QT(self.canvas, self)
            v.addWidget(self.toolbar)
            v.addWidget(self.canvas)

            self.prev_btn.clicked.connect(self.prev)
            self.next_btn.clicked.connect(self.next)
            self.combo.currentIndexChanged.connect(self.goto)

            self.setWindowTitle("Clearance Test Results")
            self.resize(1300, 600)
            self.render()

        def render(self, **kwargs):
            it = self.items[self.idx]
            plot_clearing_and_colliding_voxels(
                it.good, it.violate, it.warn,
                title=it.title, gantries=it.gantries,
                fig=self.fig, axes=self.axes
            )
            self.canvas.draw_idle()
            self.combo.blockSignals(True)
            self.combo.setCurrentIndex(self.idx)
            self.combo.blockSignals(False)

        def prev(self):
            self.idx = (self.idx - 1) % len(self.items)
            self.render()

        def next(self):
            self.idx = (self.idx + 1) % len(self.items)
            self.render()

        def goto(self, i: int):
            if i >= 0:
                self.idx = i
                self.render()

    win = BeamViewer(items)
    win.show()

    # Always run the loop if we created the app, or if no host loop flag is set.
    host_manages_loop = bool(app.property("_externally_managed"))
    if created_here or not host_manages_loop:
        app.exec()  # do not sys.exit


def plot_clearing_and_colliding_voxels(
        clearing_points: np.ndarray,
        colliding_points: np.ndarray,
        warning_points: Optional[np.ndarray] = None,
        isocenter: Optional[dict] = None,
        title: Optional[str] = None,
        gantries: Optional[str] = None,
        fig: Optional[Figure] = None,
        axes=None,
) -> Figure:
    """Draw 3 projections into provided axes; create fig/axes if None. Return fig."""
    import matplotlib.pyplot as plt
    def split(arr):
        return (arr[:, 0], arr[:, 1], arr[:, 2]) if arr.size else ([], [], [])

    if warning_points is None:
        warning_points = np.empty((0, 3))
    if isocenter is None:
        isocenter = {'x': 0, 'y': 0, 'z': 0}
    clearing_x, clearing_y, clearing_z = split(clearing_points)
    colliding_x, colliding_y, colliding_z = split(colliding_points)
    warning_x, warning_y, warning_z = split(warning_points)

    if fig is None or axes is None:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    if title:
        fig.suptitle(f"{title}", fontsize=12)
    if gantries:
        import textwrap
        wrapped = textwrap.fill(gantries, width=120, break_long_words=False, replace_whitespace=False)
        fig.supxlabel(wrapped, fontsize=14, y=0.02)
    # otherwise wipe the sup label
    else:
        fig.supxlabel("", y=0.02)

    a0, a1, a2 = axes
    for ax in (a0, a1, a2):
        ax.cla()

    # Explicit colors
    blue = (0.0, 0.45, 0.74, 0.10)  # acceptable
    red = (1.0, 0.00, 0.00, 0.70)  # collision
    orange = (1.0, 0.50, 0.00, 0.40)  # alert
    # Size of points
    size_pass = 1.0
    size_warn = 4.0
    size_fail = 6.0

    h0 = a0.scatter(clearing_x, clearing_y, s=size_pass, color=[blue], edgecolors="none", zorder=1, label="Acceptable")
    h1 = a0.scatter(colliding_x, colliding_y, s=size_fail, color=[red], edgecolors="none", zorder=3, label="Collision")
    h2 = a0.scatter(warning_x, warning_y, s=size_warn, color=[orange], edgecolors="none", zorder=2, label="Alert")
    a0.set_xlabel('X Axis (B wall to A-wall)')
    a0.set_ylabel('Y Axis (Floor to Ceiling)')
    a0.set_title('XY Projection')

    a1.scatter(clearing_x, clearing_z, s=size_pass, color=[blue], edgecolors="none", zorder=1)
    a1.scatter(colliding_x, colliding_z, s=size_fail, color=[red], edgecolors="none", zorder=3)
    a1.scatter(warning_x, warning_z, s=size_warn, color=[orange], edgecolors="none", zorder=2)
    a1.set_xlabel('X Axis (B wall to A-wall)')
    a1.set_ylabel('Z Axis (Target to Gun)')
    a1.set_title('XZ Projection')
    a1.legend(handles=[h0, h1, h2], loc="best")

    a2.scatter(clearing_z, clearing_y, s=size_pass, color=[blue], edgecolors="none", zorder=1)
    a2.scatter(colliding_z, colliding_y, s=size_fail, color=[red], edgecolors="none", zorder=3)
    a2.scatter(warning_z, warning_y, s=size_warn, color=[orange], edgecolors="none", zorder=2)
    a2.set_xlabel('Z Axis (Target to Gun)')
    a2.set_ylabel('Y Axis (Floor to Ceiling)')
    a2.set_title('ZY Projection')

    for ax in (a0, a1, a2):
        ax.set_xlim([-70, 70])
        ax.set_ylim([-70, 70])
        add_isocenter(ax)
    fig.tight_layout()
    return fig


def _build_items_with_progress_gui(rso):
    from PySide6.QtWidgets import QApplication, QProgressDialog
    from PySide6.QtCore import Qt
    import sys, logging

    logging.debug('Preparing to build items with GUI progress dialog')

    # 1) Ensure an app exists
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        logging.debug('Created QApplication')

    # 2) Pre-compute total to set a real range before building
    beam_set = rso.beamset
    beam_groups = build_beam_groups(beam_set)
    total = sum(len(g["beams"]) for g in beam_groups.values())
    if total <= 0:
        logging.debug('No beams found; aborting progress dialog')
        return []

    # 3) Create and show dialog
    dlg = QProgressDialog("Initializing...", "Cancel", 0, total)
    dlg.setWindowTitle("Clearance test progress")
    dlg.setLabelText("Gathering data for beams...")
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setAutoClose(True)
    dlg.setValue(0)
    dlg.show()
    app.processEvents()  # force initial paint
    logging.debug('Progress dialog shown')

    cancelled = {"flag": False}

    def cb(i: int, n: int, msg: str):
        # keep range in sync if n changes (defensive)
        if dlg.maximum() != n:
            dlg.setMaximum(n)
        dlg.setValue(i)
        dlg.setLabelText(msg)
        app.processEvents()
        if dlg.wasCanceled():
            cancelled["flag"] = True
            raise KeyboardInterrupt("User cancelled")

    try:
        items = make_beam_items(rso, progress=cb)
    except KeyboardInterrupt:
        items = []
    finally:
        dlg.close()
        app.processEvents()

    return [] if cancelled["flag"] else items


def main():
    logging.getLogger('matplotlib.font_manager').disabled = True
    # Initialize return variable
    rso = RSO(error=[],
              patient=find_scope(level='Patient'),
              case=find_scope(level='Case'),
              exam=find_scope(level='Examination'),
              db=find_scope(level='PatientDB'),
              machine_db=find_scope(level='Machine'),
              plan=find_scope(level='Plan'),
              beamset=find_scope(level='BeamSet'))

    plot_collisions(rso)


if __name__ == '__main__':
    main()
    # prevent premature teardown if a Qt app exists
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None and app.thread().isRunning():
        pass  # app.exec() already called in _launch_beam_viewer
