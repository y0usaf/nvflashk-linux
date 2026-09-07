import io
import stat
import tarfile
from pathlib import Path

import pytest

import importlib.util

spec = importlib.util.spec_from_file_location("archive_release", Path(__file__).parents[1] / "scripts/archive-release.py")
archive_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive_release)
ArchiveError = archive_release.ArchiveError
validate_members = archive_release.validate_members
validate_tag_head = archive_release.validate_tag_head


def fixture(names, *, modes=None, contents=None):
    modes = modes or {}
    contents = contents or {}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name in names:
            info = tarfile.TarInfo(name)
            data = contents.get(name, b"")
            info.size = len(data)
            info.mode = modes.get(name, 0o644)
            if stat.S_ISLNK(info.mode):
                info.type = tarfile.SYMTYPE
            archive.addfile(info, io.BytesIO(data) if data else None)
    stream.seek(0)
    return tarfile.open(fileobj=stream, mode="r")


def test_accepts_safe_source_fixture():
    validate_members(fixture(["nvflashk-linux-0.1.0/src/main.rs", "nvflashk-linux-0.1.0/research/samples/.gitkeep"]))


@pytest.mark.parametrize("name", [
    "nvflashk-linux-0.1.0/firmware.bin",
    "nvflashk-linux-0.1.0/boot.rom",
    "nvflashk-linux-0.1.0/research/samples/example.txt",
    "nvflashk-linux-0.1.0/tool.exe",
    "nvflashk-linux-0.1.0/archive.zip",
])
def test_denies_proprietary_binary_rom_samples_and_archives(name):
    with pytest.raises(ArchiveError):
        validate_members(fixture([name]))


def test_denies_symlink():
    with pytest.raises(ArchiveError):
        validate_members(fixture(["nvflashk-linux-0.1.0/src/link"], modes={"nvflashk-linux-0.1.0/src/link": stat.S_IFLNK | 0o777}))


def test_denies_personal_paths():
    with pytest.raises(ArchiveError):
        validate_members(fixture(["nvflashk-linux-0.1.0/home/example/secret.txt"]))


def test_tag_head_mismatch_denied(monkeypatch):
    monkeypatch.setattr(archive_release, "git_output", lambda *args: "deadbeef\n" if args == ("rev-parse", "HEAD") else "cafebabe\n")
    with pytest.raises(ArchiveError):
        validate_tag_head("v0.1.0")


def test_real_git_archive_is_accepted_and_reproducible(tmp_path, monkeypatch):
    import hashlib
    import subprocess

    monkeypatch.chdir(tmp_path)
    def git(*args):
        subprocess.run(["git", *args], check=True, capture_output=True)
    git("init")
    git("config", "user.name", "Archive test")
    git("config", "user.email", "archive@example.invalid")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.rs").write_text("fn main() {}\n")
    git("add", ".")
    git("commit", "-m", "fixture")
    git("tag", "v0.1.0")
    first = tmp_path / "one.tar.gz"
    second = tmp_path / "two.tar.gz"
    archive_release.create_archive("v0.1.0", first)
    archive_release.create_archive("v0.1.0", second)
    assert first.read_bytes() == second.read_bytes()
    assert first.with_name(first.name + ".sha256").read_text() == f"{hashlib.sha256(first.read_bytes()).hexdigest()}  one.tar.gz\n"
    with tarfile.open(first) as archive:
        assert archive.extractfile("nvflashk-linux-0.1.0/src/main.rs").read() == b"fn main() {}\n"
    git("tag", "-d", "v0.1.0")
    git("branch", "v0.1.0")
    with pytest.raises(ArchiveError):
        validate_tag_head("v0.1.0")


@pytest.mark.parametrize("magic", [b"\x7fELF", b"MZ", b"PK\x03\x04"])
def test_binary_magic_without_suffix_denied(magic):
    name = "nvflashk-linux-0.1.0/tool"
    with pytest.raises(ArchiveError):
        validate_members(fixture([name], contents={name: magic}))


@pytest.mark.parametrize("payload", [
    b"x" * 4096 + b"\x7fELF",
    b"x" * 4096 + b"PK\x03\x04",
])
def test_delayed_binary_magic_denied(payload):
    name = "nvflashk-linux-0.1.0/tool"
    with pytest.raises(ArchiveError):
        validate_members(fixture([name], contents={name: payload}))


@pytest.mark.parametrize("payload", [b"text\x00text", b"text\xfftext"])
def test_nul_and_non_utf8_source_content_denied(payload):
    name = "nvflashk-linux-0.1.0/src/tool.txt"
    with pytest.raises(ArchiveError):
        validate_members(fixture([name], contents={name: payload}))


def test_utf8_source_with_textual_magic_literals_accepted():
    name = "nvflashk-linux-0.1.0/scripts/archive-release.py"
    validate_members(fixture([name], contents={name: b'textual b"MZ" and b"\\x7fELF"'}))
