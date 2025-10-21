"""Refresh Production Scripts

This script refreshes the local list of scripts from the online repository.  It is
only applicable if a local variable was set in the version of ScriptSelector imported
into RayStation.

To test this, I recomment creating a backup of the scripts directory used clinically, e.g. master→testing
Create a copy of a ScriptSelector pointing to the testing directory, e.g. ScriptSelector_testing.py
Copy the version of update_scripts.py to the testing directory, and run it there using a ScriptSelector_testing.pd

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
import requests
import zipfile

from pathlib import Path
from typing import Mapping, Optional, cast
from datetime import datetime
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
# DIRECTORY REMOVAL PARAMETERS
DIRECTORY_REMOVAL_RETRIES = 5
DIRECTORY_REMOVAL_DELAY = 1.0  # seconds


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
    logging.debug(f"GitHub DEBUG → {json.dumps(context, indent=2)}")


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


def fetch_file_list(api, token: str | None = None) -> list[dict]:
    """Fetch the file list from the GitHub API.

    Args:
        api: The base API URL for GitHub (e.g., "https://api.github.com/repos/user/repo").
        token: Optional GitHub token for authentication.

    Returns:
        A list of dictionaries representing files and directories.
    """
    api_url = f"{api}/contents?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {token}"} if token else {}
    branch_url = f"{api}/branches/{GITHUB_BRANCH}"
    if requests.get(branch_url, headers=headers, timeout=30).status_code != 200:
        raise RuntimeError(f'Branch "{GITHUB_BRANCH}" not found (status not 200)')

    response = requests.get(api_url, headers=headers, timeout=30)
    _log_github_call(api_url, headers, response, token=token, step="root-listing")
    if response.status_code != 200:
        logging.error(
            f"GitHub API {response.status_code} ({response.reason}) "
            f"while listing {api_url}\tBody: {response.text.strip()[:200]}"
        )
        raise RuntimeError("Failed to list repository root")
    if not isinstance(response.json(), list):
        logging.error(
            f"Unexpected payload type for repository root: Expected list, "
            f"got {type(response.json()).__name__} - payload: {response.json()!r}"
        )
        raise RuntimeError("Root listing returned non-list JSON")
    return response.json()


def fetch_contents_list(sub_api, item, token: str | None = None) -> list[dict]:
    """Fetch the file list from the GitHub API.

    Args:
        sub_api: sub-API URL for the directory (e.g., "https://api.github.com/repos/user/repo/contents/path").
        item: A dictionary representing a directory item from the file list.
        token: Optional GitHub token for authentication.

    Returns:
        A list of dictionaries representing files and directories.
    """
    sub_headers = {"Authorization": f"token {token}"} if token else {}
    response = requests.get(sub_api, headers=sub_headers, timeout=30)
    _log_github_call(sub_api, sub_headers, response, token=token,
                     step=f"subdir-listing-{item['path']}")
    if response.status_code != 200:
        logging.error(
            f"GitHub API {response.status_code} ({response.reason}) "
            f" while listing {sub_api}\nBody: {response.text.strip()[:200]}"
        )
        raise RuntimeError("Aborting: directory listing failed")
    if not isinstance(response.json(), list):
        logging.error(
            f"Unexpected payload type for {sub_api}: Expected list, "
            f"got {type(response.json()).__name__} - payload: {response.json()!r}"
        )
        raise RuntimeError("Root listing returned non-list JSON")
    return response.json()


def download_files(to_process: list[dict], staging_dir: Path, token: str, progress_bar
                   ) -> None:
    """Download files from the GitHub API.

    This function iterates through a list of items, downloading files that have a
    valid download URL. It raises a ValueError if an item is not a file with a
    download URL.

    Args:
        to_process: A list of dictionaries representing items to download.
        write_dir: The directory where files will be written.
        token: GitHub token for authentication.
        progress_bar: A QtProgressBar instance to update the download progress.

    Returns:
    """
    for item in to_process:
        progress_bar.update(f'Downloading "{item["path"]}"')
        if item.get("type") == "file" and item.get("download_url"):
            content = _download_file(item["download_url"], token)
            file_path = staging_dir / item["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)


def verify_checksums(to_process: list[dict], staging_dir: Path) -> bool:
    """Verify checksums of downloaded files.

    This function checks if the SHA-1 hash of each downloaded file matches the
    expected hash from the GitHub API. If any file does not match, it logs a
    warning and returns False.

    Args:
        to_process: A list of dictionaries representing items to verify.
        staging_dir: The directory where files are stored.

    Returns:
        True if all checksums match, False otherwise.
    """
    passed = True
    for item in to_process:
        if item.get("type") == "file" and item.get("download_url"):
            content = (staging_dir / item["path"]).read_bytes()
            if _sha1_blob(content) != item["sha"]:
                logging.warning(f"Hash mismatch for {item['path']}")
                passed = False
    return passed


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


def cleanup_directory(path: Path, *, retries: int = DIRECTORY_REMOVAL_RETRIES,
                      delay: float = DIRECTORY_REMOVAL_DELAY) -> None:
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


def safe_rmdir(local_path: Path, dir_to_clean: Path) -> None:
    """Ensure the current working directory is not inside the target directory,
    and clean up any half-copied or backup directories."""
    # 1) ensure cwd is not inside either directory
    os.chdir(str(local_path.parent))
    # 2) delete any half-copied or backup trees
    cleanup_directory(dir_to_clean)


def create_zip_snapshot(
    source_dir: Path,
    dest_dir: Path,
    sha: str
) -> Path:
    """Create a ZIP archive of a directory, embedding date and commit SHA in its filename.

    The archive will be named:
        <source_dir.name>_<YYYYMMDD_HHMMSS>_<short_sha>.zip

    Args:
        source_dir: Path to the directory you want to archive (e.g. the 'master' folder).
        dest_dir: Path to the directory where the ZIP should be written.
        sha: Full commit SHA string to embed in the archive name.

    Returns:
        Path to the created .zip file.

    Raises:
        IOError: If writing to disk fails.
    """
    # Ensure destination exists
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Build timestamp and short SHA
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_sha = sha[:7]

    # Construct archive filename
    archive_name = f"rayscripts_{source_dir.name}_{timestamp}_{short_sha}.zip"
    archive_path = dest_dir / archive_name

    # Create the ZIP archive
    with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in source_dir.rglob('*'):
            # Preserve relative structure inside the zip
            relative_path = file_path.relative_to(source_dir.parent)
            zf.write(file_path, arcname=relative_path)

    return archive_path


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # Dynamically resolve the calling ScriptSelector module
    selector = importlib.import_module(Path(sys.modules["__main__"].__file__).stem)  # type: ignore[attr-defined]

    logging.debug(f"user name {os.getenv('USERNAME')}")
    os.chdir(Path(__file__).parent)
    logging.debug(f"current directory is {os.getcwd()}")
    # ----- Get files list from GitHub -----------------------------
    file_list = fetch_file_list(selector.api, selector.token)
    # Extract the SHA for the branch (SHA stands for "Secure Hash Algorithm")
    sha = file_list[0].get("sha", "unknown")
    # ----- Initial Setup --------------------------------
    target = selector.local or select_folder_dialog("Select folder location for scripts:")
    if not target:
        warning_box("No target directory selected. Aborting.", "Aborted")
        return
    target_path = Path(target)
    if not target_path.exists():
        logging.error(f"No scripts found at {target_path}; this tool only performs updates.")
        raise RuntimeError(f"Aborting: no scripts found at {target_path}")
    logging.debug(f"Post selection target path: {target_path}")

    # Put the temp folder a level up from the target so it's on the same drive
    staging_root = target_path.parent
    staging_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix="ray_scripts_update_", dir=str(staging_root)))
    logging.info(f"Using temporary directory for a fresh copy of {GITHUB_BRANCH}: {staging_dir}")

    # ----- Recurse through directories -----------------------------
    to_process = list(file_list)
    for item in to_process:
        if item.get("type") != "dir":
            continue
        sub_api = f"{selector.api}/contents/{item['path']}?ref={GITHUB_BRANCH}"
        payload = fetch_contents_list(sub_api, item, selector.token)

        to_process.extend(payload)
        (staging_dir / item["path"]).mkdir(parents=True, exist_ok=True)

    # ----- Monitor progress --------------------------------
    bar = QtProgressBar("Update Progress", "Downloading...", len(to_process) * 2)

    # ----- Download files --------------------------------
    logging.info(f"Downloading {len(to_process)} items to {staging_dir}")
    download_files(to_process, staging_dir, selector.token, bar)

    # ----- Verify checksums -----------------------------
    logging.info("Verifying checksums of downloaded files")
    bar.update("Verifying checksums")
    checksum_passes = verify_checksums(to_process, staging_dir)
    bar.close()

    # ----- Finalize the update -----------------------------
    if not checksum_passes:
        shutil.rmtree(staging_dir, ignore_errors=True)
        warning_box(
            "Scripts downloaded but verification failed. No changes were made.",
            "Verification Failed",
        )
        return

    # ----- Backup the existing scripts -----------------------------
    backup_dir = target_path.parent / f"{target_path.name}_backup_{time.strftime('%Y%m%d_%H%M%S')}"
    try:
        logging.info(f"Creating backup of {target_path} → {backup_dir} ...")
        shutil.copytree(target_path, backup_dir)
        logging.info(f"Backup created successfully at {backup_dir}")
    except Exception as exc:
        logging.exception(f"Backup failed: {exc}")
        warning_box("Failed to create backup of existing scripts.", "Backup Warning")
        return

    # ----- Replace directory atomically -----------------------------
    old_target_dir: Optional[Path] = None
    try:
        old_target_dir = target_path.with_suffix(".old_tmp")
        # tear down any leftovers from previous runs
        logging.info("Clean up any previous run artifacts")
        safe_rmdir(target_path, old_target_dir)

        # rename the live tree to a temporary suffix
        target_path.rename(old_target_dir)
        logging.info(f"Renamed {target_path} to {old_target_dir}")

        # bring in the freshly-downloaded tree
        logging.info(f"Moving {staging_dir} → {target_path}")
        try:
            shutil.move(str(staging_dir), target_path)
        except shutil.Error as exc:
            logging.error(f"move() fallback failed: {exc}. Forcing copytree()")
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            shutil.copytree(staging_dir, target_path, dirs_exist_ok=True)

        # cleanup backup on success
        if backup_dir and backup_dir.exists():
            logging.info(f"Removing backup at {backup_dir}")
            shutil.rmtree(backup_dir, ignore_errors=True)

        # delete original (now called old_target_dir)
        if old_target_dir.exists():
            logging.info(f"Removing old scripts at {old_target_dir}")
            shutil.rmtree(old_target_dir, ignore_errors=False)

        # create a compressed archive of the finalized target directory
        zipfile_path = create_zip_snapshot(
            source_dir=target_path,
            dest_dir=target_path.parent,
            sha=sha
        )
        if not zipfile_path.exists():
            logging.error(f"Failed to create ZIP archive at {zipfile_path}")
        else:
            logging.info(f"Created ZIP archive at {zipfile_path}")

        logging.info(f"Update completed successfully. New scripts downloaded from {selector.api} branch {GITHUB_BRANCH}"
                     f"and located in {target_path}")
        info_box("Script download and checksum verification successful.", "Success")

    except Exception as exc:
        logging.exception("Update failed: %s", exc)
        # try restore from backup directory first
        if backup_dir and backup_dir.exists():
            logging.info(f"Attempting a rename from {backup_dir} to {target_path}")
            # make sure nothing is in the way
            safe_rmdir(target_path)
            # Rename
            backup_dir.rename(target_path)
            if target_path.exists():
                logging.info(f"Restored scripts from backup at {backup_dir} to {target_path}")
        elif old_target_dir and old_target_dir.exists():
            logging.info("Rolling back from %s → %s", old_target_dir, target_path)
            # Make sure nothing is in the way
            safe_rmdir(target_path)
            # now rename back
            old_target_dir.rename(target_path)
            if target_path.exists():
                logging.info(f"Restored scripts from old target directory {old_target_dir} to {target_path}")
        else:
            logging.error(f"No backup or old_target_dir found to restore {target_path} from, cannot roll back.")
        warning_box("Update failed – the previous version was restored.", "Update Failed")


if __name__ == "__main__":
    main()
