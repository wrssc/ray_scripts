"""Tests for manifest_loader.py following TDD approach."""

import json
import pytest
from pathlib import Path


"""Assign a decorator so that when pytest runs and sees 'fixtures_dir'
  it gets the path to the fixtures directory where we store the test inputs"""
@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_manifest_path(fixtures_dir):
    """Return path to sample manifest."""
    return fixtures_dir / "sample_manifest.json"

@pytest.fixture
def sample_invalid_manifest_path(fixtures_dir):
    """Return path to invalid sample manifest."""
    return fixtures_dir / "sample_manifest_invalid.json"

@pytest.fixture
def sample_broken_manifest_path(fixtures_dir):
    """Return path to broken sample manifest."""
    return fixtures_dir / "sample_manifest_broken.json"

def test_load_valid_manifest(sample_manifest_path):
    """Test loading a valid JSON manifest file."""
    from regression_testing.manifest_loader import ManifestLoader

    loader = ManifestLoader()
    manifest = loader.load_manifest(str(sample_manifest_path))
    
    assert manifest is not None
    assert manifest["directory"] == "general"


def test_load_broken_json(sample_broken_manifest_path):
    """Test loading an invalid JSON manifest file."""
    from regression_testing.manifest_loader import ManifestLoader

    loader = ManifestLoader()
    with pytest.raises(json.JSONDecodeError):
        loader.load_manifest(str(sample_broken_manifest_path))


def test_validate_valid_manifest(sample_manifest_path):
    """Test validating a valid manifest structure."""
    from regression_testing.manifest_loader import ManifestLoader
    loader = ManifestLoader()
    manifest = loader.load_manifest(str(sample_manifest_path))
    is_valid = loader.validate_manifest(manifest)
    assert is_valid is True

