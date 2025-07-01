"""Refresh Production Scripts

This script refreshes the local list of scripts from the online repository.  It is
only applicable if a local variable was set in the version of ScriptSelector imported
into RayStation.

To test this, I recomment creating a backup of the scripts directory used clinically, e.g. master->testing
Create a copy of a ScriptSelector pointing to the testing directory, e.g. ScriptSelector_testing.py
Copy the version of UpdateScripts.py to the testing directory, and run it there using a ScriptSelector_testing.pd

Version History
---------------
1.2.0  Clinical release
1.3.0  Safety improvements
       * Temporary directory approach
         Downloads all files to a temporary directory first
         Only replaces the existing directory after successful verification
         If anything fails, the original directory remains untouched
       * Automatic Backup Creation
         Creates a timestamped backup of the existing directory before replacement
         Backup format: original_path_backup_YYYYMMDD_HHMMSS
       * Robust Error Handling
         If the update fails, attempts to restore from backup
         Provides user feedback about what happened
         Ensures no data loss even if multiple failures occur
       * Cleanup Management
         Automatically removes temporary directories on success or failure
         Removes backup directories after successful updates
         Prevents accumulation of temporary files

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Mark Geurts and Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__version__ = "1.3.0"
__license__ = "GPLv3"
__help__ = "https://github.com/wrssc/ray_scripts/wiki/Local-Repository-Setup"
__copyright__ = "Copyright (C) 2025, University of Wisconsin Board of Regents"

import hashlib
import importlib
import json
import logging
import os
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Mapping, Optional, cast

import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QWidget,
)
# GITHUB BRANCH TO RETRIEVE
GITHUB_BRANCH = "master"


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────
def _log_github_call(
        url: str,
        headers: Mapping[str, str],
        resp: requests.Response,
        *,
        token: str | None,
        step: str = "request",
) -> None:
    """GitHub-access audit."""
    auth_method = "token" if token else "none"
    token_fp = (
        f"{token[:6]}...{token[-4:]} sha1:{hashlib.sha1(token.encode()).hexdigest()[:8]}"
        if token
        else "-"
    )

    redacted = {
        k: ("<hidden>" if k.lower() == "authorization" else v) for k, v in headers.items()
    }

    context = {
        "step": step,
        "auth_method": auth_method,
        "token_fp": token_fp,
        "url": url,
        "status": resp.status_code,
        "req_headers": redacted,
        "resp_headers": dict(resp.headers),
        "machine": socket.gethostname(),
        "user": os.getenv("USERNAME") or os.getenv("USER") or "",
        "proxy": os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or "",
    }
    logging.debug(f"GitHub DEBUG -> {json.dumps(context, indent=2)}")


def _download_file(url: str, token: str | None = None) -> bytes:
    """Download a file, optionally using a GitHub token."""
    headers = {"Authorization": f"token {token}"} if token else {}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.content


def _sha1_blob(content: bytes) -> str:
    """Return Git-compatible SHA-1 of a blob."""
    prefix = f"blob {len(content)}\0".encode()
    return hashlib.sha1(prefix + content).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# Dialog Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _ensure_qapp() -> QApplication:
    """Return the current QApplication instance, creating one if necessary."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def select_folder_dialog(caption: str) -> str:
    """Return a folder path selected by the user (empty string on cancel)."""
    _ensure_qapp()
    folder = QFileDialog.getExistingDirectory(
        parent=None, caption=caption, dir=str(Path.home())
    )
    return folder or ""


class QtProgressBar:
    """Simple wrapper around :class:`QProgressDialog` for iterative updates."""

    def __init__(self, title: str, label: str, maximum: int) -> None:
        _ensure_qapp()
        self._dlg = QProgressDialog(label, "", 0, maximum)
        self._dlg.setWindowTitle(title)
        self._dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._dlg.setMinimumDuration(0)
        self._value = 0
        self._dlg.show()
        QApplication.processEvents()

    def update(self, text: str) -> None:
        self._value += 1
        self._dlg.setLabelText(text)
        self._dlg.setValue(self._value)
        QApplication.processEvents()

    def close(self) -> None:
        self._dlg.setValue(self._dlg.maximum())
        self._dlg.close()
        QApplication.processEvents()


def info_box(msg: str, title: str = "Info") -> None:
    _ensure_qapp()
    QMessageBox.information(
        cast(QWidget, None),
        title,
        msg,
        QMessageBox.StandardButton.Ok,
        QMessageBox.StandardButton.Ok,
    )


def warning_box(msg: str, title: str = "Warning") -> None:
    _ensure_qapp()
    QMessageBox.warning(cast(QWidget, None), title, msg)


def question_box(msg: str, title: str = "Confirm") -> bool:
    """Return *True* if the user clicks *Yes*, *False* otherwise."""
    _ensure_qapp()
    reply = QMessageBox.question(
        cast(QWidget, None),
        title,
        msg,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def cleanup_directory(path: Path, *, retries: int = 5, delay: float = 1.0) -> None:
    """Ensure a directory is removed, retrying on Windows sharing-violations (WinError 5).

    Args:
        path: The directory to delete.
        retries: Number of attempts before giving up.
        delay: Base delay (seconds) that increases linearly with attempt number.
    """
    for attempt in range(1, retries + 1):
        try:
            if path.exists():
                shutil.rmtree(path)
                logging.info(f"Successfully removed {path}")
            return
        except PermissionError as e:
            if attempt == retries:
                logging.warning(f"Could not remove {path} after {retries} attempts: {e}")
            else:
                logging.warning(f"Attempt {attempt}/{retries} to remove {path} failed: {e}, retrying in {delay * attempt:.1f}s")
                time.sleep(delay * attempt)


def clean_previous_run(local_path: Path, scratch_old: Path) -> None:
    """Ensure the old_tmp directory is cleaned up before starting."""
    # 1) ensure cwd is not inside either directory
    os.chdir(str(local_path.parent))
    # 2) delete any half-copied or backup trees
    cleanup_directory(scratch_old)


def prepare_and_cleanup(local_path: Path, scratch_old: Path) -> None:
    """Release locks and delete both the existing master and old_tmp directories."""
    # 1) ensure cwd is not inside either directory
    os.chdir(str(local_path.parent))

    # 2) delete any half-copied or backup trees
    cleanup_directory(local_path)
    # cleanup_directory(scratch_old)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # Dynamically resolve the calling ScriptSelector module
    selector = importlib.import_module(Path(sys.modules["__main__"].__file__).stem)  # type: ignore[attr-defined]

    logging.debug(f"user name {os.getenv('USERNAME')}")
    os.chdir(Path(__file__).parent)
    logging.debug(f"current directory is {os.getcwd()}")

    api_url = f"{selector.api}/contents?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {selector.token}"} if selector.token else {}
    branch_url = f"{selector.api}/branches/{GITHUB_BRANCH}"

    if requests.get(branch_url, headers=headers, timeout=30).status_code != 200:
        raise RuntimeError(f'Branch "{GITHUB_BRANCH}" not found (status not 200)')

    root_resp = requests.get(api_url, headers=headers, timeout=30)
    _log_github_call(api_url, headers, root_resp, token=selector.token, step="root-listing")
    file_list = root_resp.json()

    if root_resp.status_code != 200:
        logging.error(
            f"GitHub API {root_resp.status_code} ({root_resp.reason}) "
            f"while listing repository root\tURL: {api_url}\tBody: {root_resp.text.strip()[:200]}"
        )
        raise RuntimeError("Aborting: failed to list repository root")

    if not isinstance(file_list, list):
        logging.error(
            f"Unexpected payload type for repository root: Expected list, "
            f"got {type(file_list).__name__} - payload: {file_list!r}"
        )
        raise RuntimeError("Aborting: root listing returned non-list JSON")

    local = selector.local or select_folder_dialog("Select folder location for scripts:")
    if not local:
        warning_box("No target directory selected. Aborting.", "Aborted")
        return
    local_path = Path(local)
    logging.debug(f"Post selection local path: {local_path}")

    # Put the temp folder a level up from the target so it's on the same drive
    temp_root = local_path.parent
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="ray_scripts_update_", dir=str(temp_root)))
    logging.info(f"Using temporary directory for a fresh copy of {GITHUB_BRANCH}: {temp_dir}")

    # ----- Recurse through directories -----------------------------
    to_process = list(file_list)
    for item in to_process:
        if item.get("type") != "dir":
            continue
        sub_api = f"{selector.api}/contents/{item['path']}?ref={GITHUB_BRANCH}"
        sub_headers = {"Authorization": f"token {selector.token}"} if selector.token else {}
        resp = requests.get(sub_api, headers=sub_headers, timeout=30)
        _log_github_call(sub_api, sub_headers, resp, token=selector.token, step="subdir")
        payload = resp.json()

        if resp.status_code != 200:
            logging.error(
                f"GitHub API {resp.status_code} ({resp.reason})"
                f" while listing {sub_api}\nBody: {resp.text.strip()[:200]}"
            )
            raise RuntimeError("Aborting: directory listing failed")

        if not isinstance(payload, list):
            logging.error(
                f"Unexpected payload type for {sub_api} - expected list,"
                f" got {type(payload).__name__}\nPayload: {payload!r}"
            )
            raise RuntimeError("Aborting: bad payload type")

        to_process.extend(payload)
        (temp_dir / item["path"]).mkdir(parents=True, exist_ok=True)

    # ----- Monitor progress --------------------------------
    bar = QtProgressBar("Update Progress", "Downloading...", len(to_process) * 2)

    for item in to_process:
        bar.update(f'Downloading "{item["path"]}"')
        if item["type"] == "file" and item.get("download_url"):
            content = _download_file(item["download_url"], selector.token)
            file_path = temp_dir / item["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)

    passed = True
    for item in to_process:
        bar.update("Verifying checksums")
        if item["type"] == "file" and item.get("download_url"):
            content = (temp_dir / item["path"]).read_bytes()
            if _sha1_blob(content) != item["sha"]:
                logging.warning(f"Hash mismatch for {item['path']}")
                passed = False
    bar.close()

    if not passed:
        shutil.rmtree(temp_dir, ignore_errors=True)
        warning_box(
            "Scripts downloaded but verification failed. No changes were made.",
            "Verification Failed",
        )
        return

    # ----- Backup the existing scripts -----------------------------
    backup_dir: Optional[Path] = None
    if local_path.exists():
        backup_dir = local_path.parent.parent / f"{local_path.name}_backup_{time.strftime('%Y%m%d_%H%M%S')}"
        try:
            logging.info(f"Creating backup of {local_path} -> {backup_dir} ...")
            shutil.copytree(local_path, backup_dir)
            logging.info(f"Backup created successfully at {backup_dir}")
        except Exception as exc:
            logging.exception(f"Backup failed: {exc}")
            warning_box("Failed to create backup of existing scripts.", "Backup Warning")
            return
    else:
        logging.info(f"No existing scripts found at {local_path}, skipping backup.")

    # ----- Replace directory atomically -----------------------------
    scratch_old = Path()
    try:
        scratch_old = local_path.with_suffix(".old_tmp")
        # tear down any leftovers from previous runs
        logging.info("Clean up any previous run artifacts")
        clean_previous_run(local_path, scratch_old)

        # create a blank instance of path
        old_path = Path()
        # rename the live tree to a temporary suffix
        if local_path.exists():
            # Store the old path before renaming
            old_path = local_path
            local_path.rename(scratch_old)
            logging.info(f"Renamed {local_path} to {scratch_old}")
        else:
            logging.info(f"No existing scripts found at {local_path}, proceeding creating a "
                         f"new directory at {local_path} from {temp_dir}")

        # make sure nothing has recreated the folder
        if old_path.exists():
            logging.warning(f"{local_path} re-appeared - removing")
            shutil.rmtree(old_path, ignore_errors=True)
        else:
            logging.info(f"{old_path} does not exist, proceeding with update - no magic reappearing")

        # move temp_dir -> local_path  (this is the only risky op)
        # bring in the freshly-downloaded tree
        logging.info(f"Moving {temp_dir} -> {local_path}")
        try:
            shutil.move(str(temp_dir), local_path)
        except shutil.Error as exc:
            logging.error(f"move() fallback failed: {exc}. Forcing copytree()")
            if local_path.exists():
                shutil.rmtree(local_path, ignore_errors=True)
            shutil.copytree(temp_dir, local_path, dirs_exist_ok=True)

        # cleanup backup on success
        if backup_dir and backup_dir.exists():
            logging.info(f"Removing backup at {backup_dir}")
            shutil.rmtree(backup_dir, ignore_errors=True)

        info_box("Script download and checksum verification successful.", "Success")

        # delete original (now called scratch_old)
        if scratch_old.exists():
            logging.info(f"Removing old scripts at {scratch_old}")
            shutil.rmtree(scratch_old, ignore_errors=False)

        info_box("Scripts updated successfully.", "Success")

    except Exception as exc:
        logging.exception("Update failed: %s", exc)
        # try restore from backup directory first
        if backup_dir and backup_dir.exists():
            logging.info(f"Attempting a rename from {backup_dir} to {local_path}")
            # make sure nothing is in the way
            cleanup_directory(local_path)
            # Rename
            backup_dir.rename(local_path)
        elif scratch_old and scratch_old.exists():
            logging.info("Rolling back from %s -> %s", scratch_old, local_path)
            # Make sure nothing is in the way
            cleanup_directory(local_path)
            # now rename back
            scratch_old.rename(local_path)
        warning_box("Update failed – the previous version was restored.", "Update Failed")


if __name__ == "__main__":
    main()
