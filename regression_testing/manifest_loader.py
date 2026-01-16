# regression_testing/manifest_loader.py

"""Loads and validates JSON manifests for RayStation regression tests.

Supports two primary contexts:
- generation tests: scripts create plan/beamset (plan_name/beamset_name not required pre-run)
- context tests: scripts assume existing plan/beamset (plan_name/beamset_name required pre-run)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ValidationError:
    """A single manifest validation issue."""
    path: str
    message: str


class ManifestLoader:
    """Load and validate regression test manifests."""

    # Accept common synonyms to avoid breaking older manifests
    _PATIENT_KEY_SYNONYMS = {
        "patient_first_name": ("patient_first_name", "patient_firstname"),
        "patient_last_name": ("patient_last_name", "patient_lastname"),
    }

    def load_manifest(self, file_path: str) -> Dict[str, Any]:
        """Load a JSON manifest file.

        Args:
            file_path: Path to JSON manifest.

        Returns:
            Parsed manifest dictionary.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If JSON is invalid.
        """
        path = Path(file_path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(f"Manifest file not found: {str(path)!r}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest {str(path)!r}: {e}") from e

    def validate_manifest(self, manifest_data: Dict[str, Any]) -> None:
        """Validate manifest structure. Raises on errors.

        Rules:
          - Always require top-level: directory (str), tests (list)
          - Each test requires: script_path (str), test_type (str), test_patient (dict)
          - test_patient always requires: patient_id (str)
          - For generation tests: require case_name + exam_name; do NOT require plan/beamset
          - For context tests: require case_name + plan_name + beamset_name; exam_name optional

        Accepted test_type values:
          - "generation" or "generator"
          - "context" or "context_execution"
          - "execution" (treated like generation-minimal unless you also supply plan/beamset)

        Args:
            manifest_data: Parsed manifest dict.

        Raises:
            ValueError: If invalid, with details.
        """
        errors = self._collect_errors(manifest_data)
        if errors:
            msg_lines = ["Manifest validation failed:"]
            for err in errors:
                msg_lines.append(f"- {err.path}: {err.message}")
            raise ValueError("\n".join(msg_lines))

    def _collect_errors(self, manifest_data: Dict[str, Any]) -> List[ValidationError]:
        errors: List[ValidationError] = []

        if not isinstance(manifest_data, dict):
            return [ValidationError(path="$", message="Manifest root must be an object/dict.")]

        # Top-level
        directory = manifest_data.get("directory", None)
        if not isinstance(directory, str) or not directory.strip():
            errors.append(ValidationError(path="$.directory", message="Required non-empty string."))

        tests = manifest_data.get("tests", None)
        if not isinstance(tests, list) or len(tests) == 0:
            errors.append(ValidationError(path="$.tests", message="Required non-empty list."))
            return errors

        # Per-test
        for i, test in enumerate(tests):
            tpath = f"$.tests[{i}]"
            if not isinstance(test, dict):
                errors.append(ValidationError(path=tpath, message="Each test entry must be an object/dict."))
                continue

            script_path = test.get("script_path", None)
            if not isinstance(script_path, str) or not script_path.strip():
                errors.append(ValidationError(path=f"{tpath}.script_path", message="Required non-empty string."))

            test_type = test.get("test_type", None)
            if not isinstance(test_type, str) or not test_type.strip():
                errors.append(ValidationError(path=f"{tpath}.test_type", message="Required non-empty string."))
                continue

            test_patient = test.get("test_patient", None)
            if not isinstance(test_patient, dict):
                errors.append(ValidationError(path=f"{tpath}.test_patient", message="Required object/dict."))
                continue

            # Patient core
            patient_id = test_patient.get("patient_id", "")
            if not isinstance(patient_id, str) or not patient_id.strip():
                errors.append(ValidationError(path=f"{tpath}.test_patient.patient_id", message="Required non-empty string."))

            # Normalize optional name keys; do not require.
            # (Still allow you to use them in reports.)
            _ = self._get_patient_name(test_patient)

            # Determine context requirements
            tt = test_type.strip().lower()
            is_generation = tt in ("generation", "generator")
            is_context = tt in ("context", "context_execution", "validation")
            is_execution = tt in ("execution",)

            # Default behavior: if unknown, treat like context (safer) unless setup says create plan.
            if not (is_generation or is_context or is_execution):
                # Look for setup hints
                setup = test.get("setup", {})
                if isinstance(setup, dict) and bool(setup.get("make_plan", False) or setup.get("create_plan", False)):
                    is_generation = True
                else:
                    is_context = True

            # Required fields by mode
            case_name = test_patient.get("case_name", "")
            if not isinstance(case_name, str) or not case_name.strip():
                errors.append(ValidationError(path=f"{tpath}.test_patient.case_name", message="Required non-empty string."))

            if is_generation or is_execution:
                exam_name = test_patient.get("exam_name", "")
                if not isinstance(exam_name, str) or not exam_name.strip():
                    errors.append(ValidationError(path=f"{tpath}.test_patient.exam_name", message="Required for generation/execution tests (set current exam)."))
                # plan/beamset not required pre-run
            else:
                plan_name = test_patient.get("plan_name", "")
                if not isinstance(plan_name, str) or not plan_name.strip():
                    errors.append(ValidationError(path=f"{tpath}.test_patient.plan_name", message="Required for context tests."))
                beamset_name = test_patient.get("beamset_name", "")
                if not isinstance(beamset_name, str) or not beamset_name.strip():
                    errors.append(ValidationError(path=f"{tpath}.test_patient.beamset_name", message="Required for context tests."))

        return errors

    def _get_patient_name(self, test_patient: Dict[str, Any]) -> Optional[str]:
        """Return formatted 'Last, First' if present (optional)."""
        last = self._get_synonym_value(test_patient, "patient_last_name")
        first = self._get_synonym_value(test_patient, "patient_first_name")
        if last or first:
            return f"{last}, {first}".strip(", ")
        return None

    def _get_synonym_value(self, d: Dict[str, Any], canonical: str) -> str:
        keys = self._PATIENT_KEY_SYNONYMS.get(canonical, (canonical,))
        for k in keys:
            v = d.get(k, "")
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""
