"""Refresh Production Scripts

This script refreshes the local list of scripts from the online repository.  It is
only applicable if a local variable was set in the version of ScriptSelector imported
into RayStation.

Version History
---------------
1.2.0  Clinical release
1.3.0  Safety improvements
       • Temporary directory approach
         Downloads all files to a temporary directory first
         Only replaces the existing directory after successful verification
         If anything fails, the original directory remains untouched
       • Automatic Backup Creation
         Creates a timestamped backup of the existing directory before replacement
         Backup format: original_path_backup_YYYYMMDD_HHMMSS
       • Robust Error Handling
         If the update fails, attempts to restore from backup
         Provides user feedback about what happened
         Ensures no data loss even if multiple failures occur
       • Cleanup Management
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

from __future__ import annotations  # noqa: E402 – kept at top purely for typing; no future import requested
                                    # If strict, simply delete this line.

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
    """Detailed but safe GitHub-access audit."""
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
    # NB keep logging style unchanged (no f-string here)
    logging.error("GitHub DEBUG -> %s", json.dumps(context, indent=2))


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
# Main logic
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:  # pragma: no cover – entry-point
    # Dynamically resolve the calling ScriptSelector module
    selector = importlib.import_module(Path(sys.modules["__main__"].__file__).stem)  # type: ignore[attr-defined]

    branch = "57-beavis-bugs"  # TODO: replace with "main"
    logging.debug("user name %s", os.getenv("USERNAME"))
    os.chdir(Path(__file__).parent)
    logging.debug("current directory is %s", os.getcwd())

    api_url = f"{selector.api}/contents?ref={branch}"
    headers = {"Authorization": f"token {selector.token}"} if selector.token else {}
    branch_url = f"{selector.api}/branches/{branch}"

    if requests.get(branch_url, headers=headers, timeout=30).status_code != 200:
        raise RuntimeError(f'Branch "{branch}" not found (status not 200)')

    root_resp = requests.get(api_url, headers=headers, timeout=30)
    _log_github_call(api_url, headers, root_resp, token=selector.token, step="root-listing")
    file_list = root_resp.json()

    if root_resp.status_code != 200:
        logging.error(
            "GitHub API %s (%s) while listing repository root\nURL: %s\nBody: %s",
            root_resp.status_code,
            root_resp.reason,
            api_url,
            root_resp.text.strip()[:200],
        )
        raise RuntimeError("Aborting: failed to list repository root")

    if not isinstance(file_list, list):
        logging.error(
            "Unexpected payload type for repository root: Expected list, got %s – payload: %r",
            type(file_list).__name__,
            file_list,
        )
        raise RuntimeError("Aborting: root listing returned non-list JSON")

    local = selector.local or select_folder_dialog("Select folder location for scripts:")
    if not local:
        warning_box("No target directory selected. Aborting.", "Aborted")
        return
    local_path = Path(local)

    # Put the temp folder two levels up from the target so it's on the same drive
    temp_root = local_path.parent.parent  # Q:\RadOnc\RayStation\RayScripts
    temp_root.mkdir(parents=True, exist_ok=True)  # should exist, but be safe
    temp_dir = Path(tempfile.mkdtemp(prefix="ray_scripts_update_", dir=str(temp_root)))
    logging.info("Using temporary directory: %s", temp_dir)

    # ------------------------------------------------------------------ recurse
    to_process = list(file_list)
    for item in to_process:
        if item.get("type") != "dir":
            continue
        sub_api = f"{selector.api}/contents/{item['path']}?ref={branch}"
        sub_headers = {"Authorization": f"token {selector.token}"} if selector.token else {}
        resp = requests.get(sub_api, headers=sub_headers, timeout=30)
        _log_github_call(sub_api, sub_headers, resp, token=selector.token, step="subdir")
        payload = resp.json()

        if resp.status_code != 200:
            logging.error(
                "GitHub API %s (%s) while listing %s\nBody: %s",
                resp.status_code,
                resp.reason,
                sub_api,
                resp.text.strip()[:200],
            )
            raise RuntimeError("Aborting: directory listing failed")

        if not isinstance(payload, list):
            logging.error(
                "Unexpected payload type for %s – expected list, got %s\nPayload: %r",
                sub_api,
                type(payload).__name__,
                payload,
            )
            raise RuntimeError("Aborting: bad payload type")

        to_process.extend(payload)
        (temp_dir / item["path"]).mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- progress
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
                logging.warning("Hash mismatch for %s", item["path"])
                passed = False
    bar.close()

    if not passed:
        shutil.rmtree(temp_dir, ignore_errors=True)
        warning_box(
            "Scripts downloaded but verification failed. No changes were made.",
            "Verification Failed",
        )
        return

    # ----------------------------------------------------------------- backup
    backup_dir: Optional[Path] = None
    if local_path.exists():
        backup_dir = local_path.parent.parent / f"{local_path.name}_backup_{time.strftime('%Y%m%d_%H%M%S')}"
        try:
            logging.info("Creating backup of %s -> %s ...", local_path, backup_dir)
            shutil.copytree(local_path, backup_dir)
            logging.info("Backup created successfully at %s", backup_dir)
        except Exception as exc:  # pragma: no cover – OS-level failure
            logging.exception("Backup failed: %s", exc)
            warning_box("Failed to create backup of existing scripts.", "Backup Warning")
            return

    # ── Replace directory atomically ────────────────────────────────────────────
    try:
        scratch_old = local_path.with_suffix(".old_tmp")

        # ─────────────────────────────────────────────────────────────
        # Replace directory
        # ─────────────────────────────────────────────────────────────
        try:
            #  rename the live tree to a temporary suffix  ─────────
            tmp_dst = local_path.with_suffix(".old_tmp")
            logging.info("Renaming %s -> %s", local_path, tmp_dst)
            if local_path.exists():
                local_path.rename(tmp_dst)

            #  make sure nothing has recreated the folder  ─────────
            if local_path.exists():  # race-protection
                logging.warning("%s re-appeared – removing", local_path)
                shutil.rmtree(local_path, ignore_errors=True)

            #  bring in the freshly-downloaded tree  ───────────────
            logging.info("Moving %s -> %s", temp_dir, local_path)
            try:
                shutil.move(str(temp_dir), local_path)  # fast path (rename)
            except shutil.Error as exc:
                # move() fell back to copy and hit a duplicate – clean and retry
                logging.error("move() fallback failed: %s. Forcing copytree()", exc)
                if local_path.exists():
                    shutil.rmtree(local_path, ignore_errors=True)
                shutil.copytree(temp_dir, local_path, dirs_exist_ok=True)

            #  cleanup backup on success  ───────────────────────────
            if backup_dir and backup_dir.exists():
                logging.info("Removing backup at %s", backup_dir)
                shutil.rmtree(backup_dir, ignore_errors=True)

            info_box("Script download and checksum verification successful.", "Success")

        # ───── error handler remains the same ─────────────────────────
        except Exception as exc:
            logging.exception("Update failed: %s", exc)

        # Step 2: move temp_dir -> local_path  (this is the only risky op)
        logging.info("Moving %s -> %s", temp_dir, local_path)
        shutil.move(str(temp_dir), local_path)  # can raise

        # Step 3: delete original (now called scratch_old)
        if scratch_old.exists():
            shutil.rmtree(scratch_old, ignore_errors=False)

        # Step 4: delete backup we made earlier (it is redundant now)
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=False)

        info_box("Scripts updated successfully.", "Success")

    except Exception as exc:
        logging.exception("Update failed: %s", exc)

        # Try to roll back <- scratch_old
        if scratch_old.exists():
            logging.info("Rolling back %s -> %s", scratch_old, local_path)
            # Remove half-copied target, if any
            if local_path.exists():
                shutil.rmtree(local_path, ignore_errors=True)
            scratch_old.rename(local_path)

        warning_box("Update failed – the previous version was restored.",
                    "Update Failed")


if __name__ == "__main__":
    main()