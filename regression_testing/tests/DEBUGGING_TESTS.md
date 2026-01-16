# Why Print Statements Don't Show in Pytest

## The Problem

When you run pytest, it **captures** (hides) all output by default. This includes:
- `print()` statements
- Regular console output
- Error messages

**Why?** To keep test output clean and only show what matters. However, this can be frustrating when you're trying to debug!

---

## Solution 1: Use the `-s` Flag (Simplest)

Add `-s` to your pytest command to disable output capturing:

```bash
pytest -s
```

Or for more verbose output:
```bash
pytest -s -v
```

**What this does:**
- `-s` = Show print statements and other output
- `-v` = Verbose mode (shows each test name as it runs)

---

## Solution 2: Use `--capture=no`

Same as `-s`, just more explicit:

```bash
pytest --capture=no
```

---

## Solution 3: See Output Only When Tests Fail

By default, pytest will show captured output **only if a test fails**. So if your test passes, you won't see the print statements.

To always see output for a specific test, you can force it to show:

```python
def test_load_valid_manifest(sample_manifest_path):
    import sys
    print(f"Loaded manifest: {manifest}", file=sys.stderr)  # stderr always shows
```

But this is messy - better to just use `-s`!

---

## Solution 4: Use Pytest's Built-in Debugging (Recommended for Debugging)

Instead of `print()`, use pytest's `capsys` fixture to capture and display output properly:

```python
def test_load_valid_manifest(sample_manifest_path, capsys):
    """Test loading a valid JSON manifest file."""
    from regression_testing.manifest_loader import ManifestLoader
    
    loader = ManifestLoader()
    manifest = loader.load_manifest(str(sample_manifest_path))
    
    # This will show when using -s flag
    print(f"Loaded manifest: {manifest}")
    
    # Or use capsys to capture and check output:
    captured = capsys.readouterr()
    assert "Loaded manifest:" in captured.out
    
    assert manifest is not None
    assert manifest["directory"] == "general"
```

---

## Solution 5: Use Logging (Best for Production Code)

Instead of `print()`, use Python's logging module:

```python
import logging

def test_load_valid_manifest(sample_manifest_path):
    """Test loading a valid JSON manifest file."""
    from regression_testing.manifest_loader import ManifestLoader
    
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    loader = ManifestLoader()
    manifest = loader.load_manifest(str(sample_manifest_path))
    
    logger.debug(f"Loaded manifest: {manifest}")
    
    assert manifest is not None
```

Then run with:
```bash
pytest --log-cli-level=DEBUG
```

---

## Quick Reference: Common Pytest Flags

| Flag | What it does |
|------|--------------|
| `-s` or `--capture=no` | Show all print statements and output |
| `-v` or `--verbose` | Show more detailed test names |
| `-vv` | Even more verbose |
| `-x` | Stop after first failure |
| `-k "test_name"` | Run only tests matching the name pattern |
| `--pdb` | Drop into debugger on failure |
| `--tb=short` | Shorter traceback format |

---

## Example: Running Your Test with Output

To see your print statement, run:

```bash
# Show print statements
pytest regression_testing/tests/test_manifold_loader.py::test_load_valid_manifest -s

# Or with verbose output
pytest regression_testing/tests/test_manifold_loader.py::test_load_valid_manifest -s -v

# Or run all tests in the file with output
pytest regression_testing/tests/test_manifold_loader.py -s -v
```

---

## Why This Happens (The Technical Reason)

Pytest captures stdout and stderr by default because:
1. **Clean output**: Only shows test results, not debug spam
2. **Performance**: Faster test runs when not printing constantly
3. **Debugging**: Shows captured output when tests fail, so you can see what happened

Think of it like a security camera - it records everything (captures), but only shows you the recording when something goes wrong (test fails).

---

## Recommendation

For debugging:
- **Quick debugging**: Use `pytest -s` to see print statements
- **Better debugging**: Use `pytest --pdb` to drop into debugger on failures
- **Production tests**: Remove print statements, use assertions instead

For your current code, just add `-s` when running pytest:
```bash
pytest -s regression_testing/tests/test_manifold_loader.py
```




