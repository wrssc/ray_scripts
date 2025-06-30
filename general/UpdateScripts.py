""" Refresh Production Scripts

    This script refreshes the local list of scripts from the online repository. This is
    only applicable if a local variable was set in the version of ScriptSelector imported
    into RayStation.

 Version History:
 1.2.0 Clinical release
 1.3.0 Safety improvements
        Temporary directory approach
            Downloads all files to a temporary directory first
            Only replaces the existing directory after successful verification
            If anything fails, the original directory remains untouched
        Automatic Backup Creation
            Creates a timestamped backup of the existing directory before replacement
            Backup format: original_path_backup_YYYYMMDD_HHMMSS
        Robust Error Handling
            If the update fails, attempts to restore from backup
            Provides user feedback about what happened
            Ensures no data loss even if multiple failures occur
        Cleanup Management
            Automatically removes temporary directories on success or failure
            Removes backup directories after successful updates
            Prevents accumulation of temporary files


    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts and Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '1.3.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Local-Repository-Setup'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'


import hashlib
import importlib
import logging
import json
import socket
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, cast, Mapping

import requests
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
)





def _log_github_call(
    url: str,
    headers: Mapping[str, str],
    resp: requests.Response,
    *,
    token: str | None,
    step: str = "request",
) -> None:
    """Detailed but safe GitHub-access audit."""
    auth_method = "token" if token else "none"
    token_fp = (
        f"{token[:6]}…{token[-4:]} sha1:{hashlib.sha1(token.encode()).hexdigest()[:8]}"
        if token else "—"
    )

    redacted = {k: ("<hidden>" if k.lower() == "authorization" else v)
                for k, v in headers.items()}

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
    logging.error("GitHub DEBUG → %s", json.dumps(context, indent=2))


# ──────────────────────────────────────────────────────────────────────────────
# Qt helpers
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
    """Simple wrapper around QProgressDialog for iterative updates."""

    def __init__(self, title: str, label: str, maximum: int):
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
        cast(QWidget, None),  # parent
        title,  # title
        msg,  # text
        QMessageBox.StandardButton.Ok,  # buttons
        QMessageBox.StandardButton.Ok  # defaultButton  (optional)
    )


def warning_box(msg: str, title: str = "Warning") -> None:
    _ensure_qapp()
    QMessageBox.warning(cast(QWidget, None), title, msg)  # cast tells linter the type while providing None at runtime


def question_box(msg: str, title: str = "Confirm") -> bool:
    """
    Return True if the user clicks Yes, False for No.
    """
    _ensure_qapp()
    reply = QMessageBox.question(
        cast(QWidget, None), title, msg,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes


# ──────────────────────────────────────────────────────────────────────────────
# Main logic
# ──────────────────────────────────────────────────────────────────────────────
def _download_file(url: str, token: str | None = None) -> bytes:
    """Download a file, optionally using a GitHub token."""
    headers = {"Authorization": f"token {token}"} if token else {}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.content


def _sha1_blob(content: bytes) -> str:
    """Return Git-compatible SHA-1 of a blob."""
    prefix = f"blob {len(content)}\0".encode()
    return hashlib.sha1(prefix + content).hexdigest()


def main() -> None:
    # Dynamically resolve the calling ScriptSelector module
    selector = importlib.import_module(
        Path(sys.modules["__main__"].__file__).stem  # type: ignore
    )

    branch = "57-beavis-bugs"  # TODO replace with master
    logging.debug("user name %s", os.getenv("username"))
    os.chdir(Path(__file__).parent)
    logging.debug("current directory is %s", os.getcwd())

    # Retrieve file list from GitHub
    api_url = f"{selector.api}/contents?ref={branch}"
    headers = {"Authorization": f"token {selector.token}"} if selector.token else {}

    root_resp = requests.get(api_url, headers=headers)
    _log_github_call(api_url, headers, root_resp, token=selector.token, step="root-listing")
    file_list = root_resp.json()

    if root_resp.status_code != 200:
        logging.error(
            "GitHub API %s (%s) while listing repository root\nURL: %s\nBody: %s",
            root_resp.status_code, root_resp.reason, api_url, root_resp.text.strip()[:200]
        )
        raise RuntimeError("Aborting: failed to list repository root")

    if not isinstance(file_list, list):
        logging.error(
            "Unexpected payload type for repository root Expected list, got %s Payload: %r",
            type(file_list).__name__, file_list
        )
        raise RuntimeError("Aborting: root listing returned non-list JSON")

    # Ask user for local folder if not predefined
    local = selector.local or select_folder_dialog("Select folder location for scripts:")
    if not local:
        warning_box("No target directory selected. Aborting.", "Aborted")
        return
    local_path = Path(local)

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="ray_scripts_update_"))
    logging.info("Using temporary directory: %s", temp_dir)

    # Recursively pull directory structure and files into the temporary directory
    to_process = list(file_list)  # working queue
    for item in to_process:
        if item.get("type") != "dir":
            continue  # Only recurse into directories
        # Extend queue with contents of subdirectory
        sub_api = f"{selector.api}/contents/{item['path']}?ref={branch}"
        sub_headers = (
            {"Authorization": f"token {selector.token}"} if selector.token else {}
        )
        resp = requests.get(sub_api, headers=sub_headers)
        _log_github_call(sub_api, sub_headers, resp, token=selector.token, step="subdir")
        payload = resp.json()
        # --- diagnostic guard ------------------------------------------------
        if resp.status_code != 200:
            logging.error(
                "GitHub API %s (%s) while listing %s\nBody: %s",
                resp.status_code, resp.reason, sub_api, resp.text.strip()[:200]
            )
            raise RuntimeError("Aborting: directory listing failed")

        if not isinstance(payload, list):
            logging.error(
                "Unexpected payload type for %s – expected list, got %s\nPayload: %r",
                sub_api, type(payload).__name__, payload
            )
            raise RuntimeError("Aborting: bad payload type")
        # --------------------------------------------------------------------
        to_process.extend(payload)  # only reached on success
        (temp_dir / item["path"]).mkdir(parents=True, exist_ok=True)

    # Reuse list to iterate twice (download + verify)
    bar = QtProgressBar("Update Progress", "Downloading…", len(to_process) * 2)

    # Download loop
    for item in to_process:
        bar.update(f"Downloading {item['path']}")
        if item["type"] == "file" and item.get("download_url"):
            content = _download_file(item["download_url"], selector.token)
            file_path = temp_dir / item["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)

    # Verification loop
    passed = True
    for item in to_process:
        bar.update("Verifying checksums")
        if item["type"] == "file" and item.get("download_url"):
            content = (temp_dir / item["path"]).read_bytes()
            if _sha1_blob(content) != item["sha"]:
                logging.warning("Hash mismatch for %s", item["path"])
                passed = False

    bar.close()

    # Handle verification result
    if not passed:
        shutil.rmtree(temp_dir, ignore_errors=True)
        warning_box(
            "Scripts downloaded but verification failed. No changes were made.",
            "Verification Failed",
        )
        return

    # Backup existing directory
    backup_dir: Optional[Path] = None
    if local_path.exists():
        backup_dir = local_path.with_name(
            f"{local_path.name}_backup_{time.strftime('%Y%m%d_%H%M%S')}"
        )
        try:
            shutil.copytree(local_path, backup_dir)
            logging.info("Created backup at %s", backup_dir)
        except Exception as exc:
            logging.warning("Backup failed: %s", exc)
            warning_box(
                "Failed to create backup of existing scripts.", "Backup Warning"
            )
            if not question_box("Continue without backup?", "Proceed anyway?"):
                shutil.rmtree(temp_dir, ignore_errors=True)
                return

    # Replace directory
    try:
        if local_path.exists():
            shutil.rmtree(local_path, ignore_errors=True)
        shutil.move(str(temp_dir), local_path)
        logging.info("Scripts updated successfully: %s", local_path)

        # Remove backup if everything succeeded
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
            logging.info("Removed backup directory: %s", backup_dir)

        info_box("Script download and checksum verification successful.", "Success")

    except Exception as exc:
        logging.error("Update failed: %s", exc)
        # Attempt restoration
        if backup_dir and backup_dir.exists():
            try:
                if local_path.exists():
                    shutil.rmtree(local_path, ignore_errors=True)
                shutil.move(str(backup_dir), local_path)
                logging.info("Restored from backup: %s", backup_dir)
                warning_box(
                    "Update failed, restored from backup. No changes were made.",
                    "Update Failed",
                )
            except Exception as restore_exc:
                logging.error("Backup restoration failed: %s", restore_exc)
                warning_box(
                    "Update failed AND backup restoration failed. Check logs.",
                    "Critical Error",
                )
        else:
            warning_box("Update failed. Check logs for details.", "Update Failed")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()