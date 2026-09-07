import os
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).parents[1]
VALIDATOR = Path(os.environ.get("VALIDATOR", ROOT / "scripts" / "validate-release"))


@pytest.fixture(autouse=True)
def restore_manifests():
    originals = {name: (ROOT / name).read_bytes() for name in ("Cargo.toml", "Cargo.lock")}
    yield
    for name, content in originals.items():
        (ROOT / name).write_bytes(content)


def run(tag, cargo_version="0.1.0", lock_version=None):
    lock_version = lock_version or cargo_version
    (ROOT / "Cargo.toml").write_text(f'[package]\nname = "nvflashk-linux"\nversion = "{cargo_version}"\n')
    (ROOT / "Cargo.lock").write_text(
        'version = 3\n\n[[package]]\nname = "nvflashk-linux"\nversion = "'
        + lock_version
        + '"\n'
    )
    return subprocess.run(["bash", VALIDATOR, tag], text=True, capture_output=True)


def test_accepts_stable_matching_manifest_and_lock():
    assert run("v0.1.0").returncode == 0


def test_accepts_rc_matching_manifest_and_lock():
    assert run("v0.1.0-rc.1", "0.1.0-rc.1").returncode == 0


def test_rejects_leading_zero_components_and_zero_rc():
    for tag in ("v01.2.3", "v1.02.3", "v1.2.03", "v1.2.3-rc.0", "v1.2.3-rc.01"):
        assert run(tag, tag[1:]).returncode != 0


def test_rejects_malformed_tags():
    for tag in ("1.2.3", "v1.2", "v1.2.3-dev.1", "v1.2.3-rc", "v1.2.3+meta"):
        assert run(tag, "1.2.3").returncode != 0


def test_requires_lock_version_match():
    assert run("v0.1.0", lock_version="0.1.1").returncode != 0


def test_requires_manifest_match():
    assert run("v0.1.0", "0.1.1").returncode != 0


def test_requires_rc_suffix_to_match_manifest():
    assert run("v0.1.0-rc.1", "0.1.0").returncode != 0
