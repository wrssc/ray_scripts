""" Check Clearance for Beamset """
import numpy as np
import textwrap
import logging
from dataclasses import dataclass
from typing import Iterable, Tuple, Sequence, List, Dict, Optional, Callable
import matplotlib.pyplot as plt
from collections import namedtuple
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from library.PlanReview.review_definitions import (SUPPORT_TOLERANCE_COLLISION, TRUEBEAM_MAX_DIAMETER, TRUEBEAM_COVER_DIAMETER,
                                                   TRUEBEAM_HEAD_LENGTH)
from library.PlanReview.qa_tests.test_beamset.check_isocenter_clearance import (
    shift_to_isocenter_and_couch_rotate_points, get_head_collision_masks, extract_voxel_representation,
    find_gantry_angular_traversal, filter_in_bore_clearing_points_tomo, build_beam_groups, )
from library.StructureOperations import find_types
from library.api.api_utils import find_scope


@dataclass(frozen=True)
class BeamKey:
    """Identity of a beam within a group."""
    name: str
    couch_deg: float
    isocenter: Tuple[float, float, float]


@dataclass
class BeamItem:
    """Payload for UI."""
    label: str
    title: str
    gantries: str
    good: np.ndarray  # (N,3)
    violate: np.ndarray  # (M,3)
    warn: np.ndarray  # (K,3)


def plot_clearing_and_colliding_voxels(clearing_points, colliding_points, warning_points=None,
                                       isocenter=None, title=None, gantries=None):
    """
    Plot clearing and rotated points with different colors in 2D projections (XY, XZ, YZ).

    Args:
        clearing_points (np.array): Numpy array with clearing points, shape (N, 3).
        colliding_points (np.array): Numpy array with colliding points, shape (N, 3).
        warning_points (np.array): Numpy array with near-colliding (laserguard) points, shape (N, 3).
    """

    # extract coords
    def split(arr):
        return (arr[:, 0], arr[:, 1], arr[:, 2]) if arr.size else ([], [], [])

    if warning_points is None:
        warning_points = np.empty((0, 3))
    if isocenter is None:
        isocenter = {'x': 0, 'y': 0, 'z': 0}

    clearing_x, clearing_y, clearing_z = split(clearing_points)
    colliding_x, colliding_y, colliding_z = split(colliding_points)
    warning_x, warning_y, warning_z = split(warning_points)

    # Create a figure with three subplots for XY, XZ, and YZ planes
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    if title:
        fig.suptitle(f"{title}", fontsize=12)
    if gantries:
        wrapped_gantries = textwrap.fill(gantries, width=120, break_long_words=False, replace_whitespace=False)
        fig.supxlabel(wrapped_gantries, fontsize=14, y=0.02)
    # Plot XY plane
    axes[0].scatter(clearing_x, clearing_y, c='b', label='Acceptable Points', s=1, alpha=0.1)
    axes[0].scatter(colliding_x, colliding_y, c='r', label='Collision Points', s=1, alpha=0.4)
    axes[0].scatter(warning_x, warning_y, c='orange', label='Alert Points', s=1, alpha=0.4)
    axes[0].set_xlabel('X Axis (B wall to A-wall)')
    axes[0].set_ylabel('Y Axis (Floor to Ceiling)')
    axes[0].set_title('XY Projection')

    # Plot XZ plane
    axes[1].scatter(clearing_x, clearing_z, c='b', label='Acceptable Points', s=1, alpha=0.1)
    axes[1].scatter(colliding_x, colliding_z, c='r', label='Collision Points', s=1, alpha=0.4)
    axes[1].scatter(warning_x, warning_z, c='orange', label='Alert Points', s=1, alpha=0.4)
    axes[1].set_xlabel('X Axis (B wall to A-wall)')
    axes[1].set_ylabel('Z Axis (Target to Gun)')
    axes[1].set_title('XZ Projection')
    axes[1].legend()

    # Plot YZ plane
    axes[2].scatter(clearing_z, clearing_y, c='b', label='Acceptable Points', s=1, alpha=0.1)
    axes[2].scatter(colliding_z, colliding_y, c='r', label='Collision Points', s=1, alpha=0.1)
    axes[2].scatter(warning_z, warning_y, c='orange', label='Alert Points', s=1, alpha=0.1)
    axes[2].set_xlabel('Z Axis (Target to Gun)')
    axes[2].set_ylabel('Y Axis (Floor to Ceiling)')
    axes[2].set_title('ZY Projection')

    # Set axis limits for all subplots (adjust to your expected range)
    for ax in axes:
        ax.set_xlim([-70, 70])
        ax.set_ylim([-70, 70])
        add_isocenter(ax)

    plt.tight_layout()
    plt.show()


# PLOTTING UTILITIES

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
        angles: Sequence[float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Classify points using analytic cylinder model for given gantry angles.

    Returns:
      good, violate, warn arrays (each (*,3)).
    """
    diameter = TRUEBEAM_COVER_DIAMETER
    length = TRUEBEAM_HEAD_LENGTH
    h_fail = TRUEBEAM_MAX_DIAMETER / 2.0 - SUPPORT_TOLERANCE_COLLISION
    h_warn = h_fail - 2.0

    masks_fail, masks_warn = get_head_collision_masks(
        pts_iso, diameter, length, h_fail, h_warn, angles
    )
    fail_any = _any_mask(masks_fail, angles, pts_iso)
    warn_any = _any_mask(masks_warn, angles, pts_iso)

    violate = pts_iso[fail_any]
    warn = pts_iso[warn_any & ~fail_any]
    good = pts_iso[~(fail_any | warn_any)]
    return good, violate, warn


def classify_points_tomo(pts_iso: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Classify points for Tomo delivery."""
    fail_mask, warn_mask = filter_in_bore_clearing_points_tomo(pts_iso)
    violate = pts_iso[fail_mask]
    warn = pts_iso[warn_mask & ~fail_mask]
    good = pts_iso[~(fail_mask | warn_mask)]
    return good, violate, warn


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


# ---------- labeling ---------------------------------------------------------

def angles_for_beam(beam_set, beam_name: str) -> Tuple[List[float], Optional[bool]]:
    """Return per-beam gantry angle list and clockwise flag for VMAT/SMLC."""
    delivery = beam_set.Beams[beam_name].DeliveryTechnique
    if "DynamicArc" in delivery:
        angles, clockwise = find_gantry_angular_traversal(beam_set, testing=False)[beam_name]
        return list(angles), bool(clockwise)
    if "SMLC" in delivery and beam_set.Modality == "Photons":
        return [beam_set.Beams[beam_name].GantryAngle], None
    return [], None  # Tomo or electrons handled upstream


def gantry_ranges_text(violate: np.ndarray, warn: np.ndarray) -> str:
    """Build fail/warn range strings for subtitle."""
    fail_s, warn_s = _get_failing_gantry_ranges(violate, warn)
    # Compact join while avoiding extra spaces.
    return "\n".join(s for s in (fail_s, warn_s) if s)


def _get_failing_gantry_ranges(violation_points: np.ndarray,
                               warning_points: np.ndarray) -> Tuple[str, str]:
    """Compute Varian IEC-like angle range strings from XY projection."""

    def _str_from_pts(pts, prefix):
        if pts.size == 0:
            return ""
        x = pts[:, 0];
        y = pts[:, 1]
        cyl = (360 - (np.degrees(np.arctan2(y, x)) - 90)) % 360
        s, _ = _gantry_string(cyl, tol_deg=2, wrap=True)
        return f"{prefix}: " + s if s else ""

    return _str_from_pts(violation_points, "Gantry angles with collisions"), \
        _str_from_pts(warning_points, "Gantry angles with near-collisions")


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
            p = v;
            continue
        ranges.append((s, p));
        s = p = v
    ranges.append((s, p))
    if wrap and len(ranges) >= 2:
        fs, fe = ranges[0];
        ls, le = ranges[-1]
        if (fs <= 0 + tol_deg) and (le >= 359 - tol_deg):
            ranges = [(ls, fe)] + ranges[1:-1]
    parts = [f"({x})" if x == y else f"({x}-{y})" for x, y in ranges]
    return ", ".join(parts), uniq


# ---------- downsampling -----------------------------------------------------

def downsample(points: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform without replacement if N>n, else return as-is."""
    if points.size == 0 or points.shape[0] <= n:
        return points
    idx = rng.choice(points.shape[0], size=n, replace=False)
    return points[idx]


# ---------- main builder for viewer -----------------------------------------


ProgressFn = Callable[[int, int, str], None]  # (i, n_total, message)


def make_beam_items(
        rso,
        roi_types: Sequence[str] = ("Fixation", "Support", "External"),
        n_good: int = 50_000,
        n_bad: int = 100_000,
        seed: int = 20250922,
        progress: Optional[ProgressFn] = None,
) -> List[BeamItem]:
    rng = np.random.default_rng(seed)
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
            # --- existing per-beam work ---
            logging.debug(f"Building {beam_name} (couch {couch_angle})")
            delivery = beam_set.Beams[beam_name].DeliveryTechnique
            modality = beam_set.Modality
            pts_iso = transform_points_to_isocenter(rso, pts_patient, beam_name)

            if "Tomo" in delivery:
                good, violate, warn = classify_points_tomo(pts_iso)
            elif "SMLC" in delivery and modality == "Electrons":
                i += 1
                continue
            else:
                angles, _ = angles_for_beam(beam_set, beam_name)
                if angles:
                    good, violate, warn = classify_collision_points_truebeam(pts_iso, angles)
                else:
                    good, violate, warn = pts_iso, np.empty((0, 3)), np.empty((0, 3))

            good = downsample(good, n_good, rng)
            violate = downsample(violate, n_bad, rng)
            warn = downsample(warn, n_bad, rng)

            plan_label = beam_set.DicomPlanLabel

            if "Tomo" in delivery:
                title = f"{plan_label}: {beam_name}"
                label = f"{beam_name} (Couch {couch_angle}°, ISO {tuple(round(v, 1) for v in isocenter)})"
                if violate.any():
                    gantries = f"FAIL: points are detected that will result in a collision."
                elif warn.any():
                    gantries = f"Warning: points are detected that may result in a collision."
                else:
                    gantries = "No collision points detected"
            else:
                title = f"{plan_label}: {beam_name}: Couch {couch_angle}°"
                label = f"{beam_name} (Couch {couch_angle}°, ISO {tuple(round(v, 1) for v in isocenter)})"
                gantries = gantry_ranges_text(violate, warn)

            items.append(BeamItem(label=label, title=title, gantries=gantries,
                                  good=good, violate=violate, warn=warn))
            i += 1

    if progress:
        progress(total, total, "Done")
    return items


def plot_collisions(rso, interactive: bool = False) -> None:
    if interactive:
        # build with GUI progress, then launch viewer
        logging.debug("Interactive mode")
        items = _build_items_with_progress_gui(rso)
        if not items:
            return
        _launch_beam_viewer(items)
        return

    # non-GUI path: simple console progress
    def console_cb(i, n, msg):
        if n:
            pct = int((i / n) * 100)
            logging.debug(f"[{i}/{n}] {pct:3d}% {msg}")

    items = make_beam_items(rso, progress=console_cb)
    for it in items:
        plot_clearing_and_colliding_voxels(it.good, it.violate, it.warn,
                                           title=it.title, gantries=it.gantries)
    plt.show()


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

            central = QWidget();
            self.setCentralWidget(central)
            v = QVBoxLayout(central)

            # controls
            ctrl = QHBoxLayout()
            self.prev_btn = QPushButton("Prev")
            self.next_btn = QPushButton("Next")
            self.combo = QComboBox()
            self.combo.addItems([it.label for it in items])
            ctrl.addWidget(self.prev_btn);
            ctrl.addWidget(self.next_btn);
            ctrl.addWidget(self.combo)
            v.addLayout(ctrl)

            # canvas + toolbar
            self.fig = Figure(figsize=(12, 4), constrained_layout=True)
            self.axes = [self.fig.add_subplot(1, 3, i + 1) for i in range(3)]
            self.canvas = FigureCanvasQTAgg(self.fig)
            self.toolbar = NavigationToolbar2QT(self.canvas, self)
            v.addWidget(self.toolbar);
            v.addWidget(self.canvas)

            self.prev_btn.clicked.connect(self.prev)
            self.next_btn.clicked.connect(self.next)
            self.combo.currentIndexChanged.connect(self.goto)

            self.setWindowTitle("Clearance Test Results")
            self.resize(1300, 600)
            self.render()

        def render(self):
            it = self.items[self.idx]
            alt_plot_clearing_and_colliding_voxels(
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


def alt_plot_clearing_and_colliding_voxels(
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

    a0, a1, a2 = axes
    a0.cla();
    a1.cla();
    a2.cla()
    a0.scatter(clearing_x, clearing_y, s=1, alpha=0.1)
    a0.scatter(colliding_x, colliding_y, s=1, alpha=0.4)
    a0.scatter(warning_x, warning_y, s=1, alpha=0.4)
    a0.set_xlabel('X Axis (B wall to A-wall)');
    a0.set_ylabel('Y Axis (Floor to Ceiling)');
    a0.set_title('XY Projection')

    a1.scatter(clearing_x, clearing_z, s=1, alpha=0.1)
    a1.scatter(colliding_x, colliding_z, s=1, alpha=0.4)
    a1.scatter(warning_x, warning_z, s=1, alpha=0.4)
    a1.set_xlabel('X Axis (B wall to A-wall)');
    a1.set_ylabel('Z Axis (Target to Gun)');
    a1.set_title('XZ Projection')
    a1.legend(['Acceptable', 'Collision', 'Alert'])

    a2.scatter(clearing_z, clearing_y, s=1, alpha=0.1)
    a2.scatter(colliding_z, colliding_y, s=1, alpha=0.1)
    a2.scatter(warning_z, warning_y, s=1, alpha=0.1)
    a2.set_xlabel('Z Axis (Target to Gun)');
    a2.set_ylabel('Y Axis (Floor to Ceiling)');
    a2.set_title('ZY Projection')

    for ax in (a0, a1, a2):
        ax.set_xlim([-70, 70]);
        ax.set_ylim([-70, 70]);
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
    dlg.setWindowModality(Qt.WindowModal)  # less fragile in notebooks than ApplicationModal
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
    Pd = namedtuple('Pd', ['error', 'db', 'machine_db', 'case', 'patient', 'exam', 'plan',
                           'beamset'])
    # Get current patient, case, exam
    rso = Pd(error=[],
             patient=find_scope(level='Patient'),
             case=find_scope(level='Case'),
             exam=find_scope(level='Examination'),
             db=find_scope(level='PatientDB'),
             machine_db=find_scope(level='Machine'),
             plan=find_scope(level='Plan'),
             beamset=find_scope(level='BeamSet'))

    plot_collisions(rso, interactive=True)


if __name__ == '__main__':
    main()
    # prevent premature teardown if a Qt app exists
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None and app.thread().isRunning():
        pass  # app.exec() already called in _launch_beam_viewer
