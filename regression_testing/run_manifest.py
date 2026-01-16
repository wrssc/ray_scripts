# regression_testing/run_manifest.py
#
# Minimal RayStation runner: load a manifest, set patient/context, import script, execute.
#
# Intended usage (RayStation script console):
#   exec(open(r"Q:\RadOnc\RayStation\RayScripts\master\regression_testing\run_manifest.py").read())
#
# Or call run_manifest(...) from another RayStation script.

from __future__ import annotations

import importlib.util
import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from regression_testing.manifest_loader import ManifestLoader
from regression_testing.rs_context_loader import connect, set_current_from_manifest_test


@dataclass
class TestResult:
    script_path: str
    test_type: str
    status: str  # "passed" | "failed"
    duration_s: float
    error: Optional[str] = None
    traceback_str: Optional[str] = None


def _find_repo_root(start: Optional[str] = None) -> str:
    """Find repo root by walking upward until we see a marker directory."""
    if start is None:
        start = os.getcwd()
    p = Path(start).resolve()

    markers = ("library", "general", "regression_testing")
    for parent in [p] + list(p.parents):
        if all((parent / m).exists() for m in markers):
            return str(parent)
    # Fallback: assume this file is under repo_root/regression_testing/
    try:
        here = Path(__file__).resolve()
        return str(here.parents[1])
    except Exception:
        return str(p)


def _import_module_from_path(module_name: str, abs_path: str):
    """Import a Python module from a filesystem path."""
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import module from path: {abs_path!r}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _call_script_entrypoint(
    mod: Any,
    spec: Dict[str, Any],
) -> None:
    """Execute the test based on test_type conventions.

    Current convention:
      - If module has main(), call it.
      - For generation tests, pass bypass_dialogs=True if main accepts it.
      - For other tests, call main() with no args.

    Extend this later with:
      spec["entrypoint"] = {"func": "main", "kwargs": {...}}
    """
    test_type = str(spec.get("test_type", "")).strip().lower()
    setup = spec.get("setup", {})
    if not isinstance(setup, dict):
        setup = {}

    if not hasattr(mod, "main"):
        raise AttributeError("Script module has no main() function")

    # Best-effort: call main(bypass_dialogs=...) for generator tests.
    if test_type in ("generation", "generator", "execution"):
        bypass_dialogs = bool(setup.get("bypass_dialogs", True))
        try:
            mod.main(bypass_dialogs=bypass_dialogs)
        except TypeError:
            # main() does not accept bypass_dialogs
            mod.main()
        return

    # Context tests: default main()
    mod.main()


def run_manifest(
    manifest_path: str,
    *,
    repo_root: Optional[str] = None,
    test_indices: Optional[List[int]] = None,
    stop_on_fail: bool = False,
) -> List[TestResult]:
    """Run tests from a manifest inside RayStation.

    Args:
        manifest_path: Path to the manifest JSON.
        repo_root: Repository root directory. If None, attempts to infer.
        test_indices: If provided, run only these indices from manifest["tests"].
        stop_on_fail: Stop after first failure.

    Returns:
        List of TestResult.
    """
    if repo_root is None:
        # Prefer repo_root based on manifest location.
        repo_root = _find_repo_root(start=str(Path(manifest_path).resolve().parent))

    loader = ManifestLoader()
    manifest = loader.load_manifest(manifest_path)
    loader.validate_manifest(manifest)

    tests = manifest["tests"]
    if test_indices is None:
        indices = list(range(len(tests)))
    else:
        indices = test_indices

    patient_db = rs.get_current("PatientDB")

    results: List[TestResult] = []
    for idx in indices:
        spec = tests[idx]
        script_rel = str(spec["script_path"])
        test_type = str(spec.get("test_type", "")).strip()

        start = time.time()
        try:
            # 1) Load patient and set current objects based on manifest spec
            _rso = set_current_from_manifest_test(spec, patient_db)

            # 2) Import script
            script_abs = os.path.join(repo_root, script_rel)
            if not os.path.exists(script_abs):
                raise FileNotFoundError(f"Script not found: {script_abs!r}")

            # Use unique module name per test to avoid collisions
            module_name = f"rs_regtest_{idx}_{Path(script_rel).stem}"
            mod = _import_module_from_path(module_name, script_abs)

            # 3) Execute entrypoint
            _call_script_entrypoint(mod, spec)

            dur = time.time() - start
            results.append(
                TestResult(
                    script_path=script_rel,
                    test_type=test_type,
                    status="passed",
                    duration_s=dur,
                )
            )
            print(f"[PASS] [{idx}] {script_rel} ({dur:.2f}s)")

        except Exception as e:
            dur = time.time() - start
            tb = traceback.format_exc()
            results.append(
                TestResult(
                    script_path=script_rel,
                    test_type=test_type,
                    status="failed",
                    duration_s=dur,
                    error=str(e),
                    traceback_str=tb,
                )
            )
            print(f"[FAIL] [{idx}] {script_rel} ({dur:.2f}s): {e}")
            print(tb)

            if stop_on_fail:
                break

    return results


def run_manifest_from_here() -> None:
    """Convenience: run a manifest path hardcoded below."""
    # Edit these to taste when running from RayStation.
    manifest_path = r"Q:\RadOnc\RayStation\RayScripts\master\regression_testing\manifests\general_autoplan_wb.json"
    run_manifest(manifest_path, stop_on_fail=True)


# If executed via exec(open(...).read()), __name__ is usually "__main__".
if __name__ == "__main__":
    # Optional: allow passing manifest path as first arg (rare in RayStation, but harmless).
    if len(sys.argv) > 1 and sys.argv[1].strip():
        run_manifest(sys.argv[1].strip(), stop_on_fail=True)
    else:
        run_manifest_from_here()
