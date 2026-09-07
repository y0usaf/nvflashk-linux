#!/usr/bin/env python3
"""Create and validate a deterministic source-only release archive."""
from __future__ import annotations

import hashlib
import io
import gzip
import subprocess
import sys
import tarfile
from pathlib import Path


class ArchiveError(ValueError):
    pass


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def validate_tag_head(tag: str) -> None:
    try:
        tag_commit = git_output("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
        head = git_output("rev-parse", "HEAD")
    except subprocess.CalledProcessError as exc:
        raise ArchiveError(f"cannot resolve tag {tag}") from exc
    if not tag_commit or tag_commit != head:
        raise ArchiveError(f"tag {tag} does not point at HEAD")


def validate_members(archive: tarfile.TarFile) -> None:
    forbidden_suffixes = (".bin", ".rom", ".exe", ".dll", ".so", ".elf", ".pe", ".zip")
    for member in archive:
        name = member.name
        parts = Path(name).parts
        if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
            raise ArchiveError(f"unsupported archive member: {name}")
        if Path(name).is_absolute() or ".." in parts:
            raise ArchiveError(f"unsafe archive path: {name}")
        if any(part in {"home", "Users", "Desktop", "Documents", "Downloads"} for part in parts):
            raise ArchiveError(f"personal path in archive: {name}")
        if member.isdir():
            continue
        if "research" in parts and "samples" in parts:
            if Path(name).name != ".gitkeep":
                raise ArchiveError(f"sample content in archive: {name}")
        if name.lower().endswith(forbidden_suffixes):
            raise ArchiveError(f"proprietary/binary file in archive: {name}")
        data = archive.extractfile(member).read()
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArchiveError(f"non-text content in archive: {name}") from exc
        if b"\x00" in data or b"PK\x03\x04" in data or b"\x7fELF" in data or data.startswith(b"MZ"):
            raise ArchiveError(f"binary content in archive: {name}")


def create_archive(tag: str, output: Path) -> Path:
    validate_tag_head(tag)
    version = tag.removeprefix("v")
    raw = subprocess.check_output(["git", "archive", "--format=tar", f"--prefix=nvflashk-linux-{version}/", f"refs/tags/{tag}"])
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        validate_members(archive)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as source:
        members = source.getmembers()
        for member in members:
            member.mtime = 0
            member.uid = member.gid = 0
            member.uname = member.gname = ""
        packed = io.BytesIO()
        with tarfile.open(fileobj=packed, mode="w", format=tarfile.PAX_FORMAT) as dest:
            for member in members:
                data = source.extractfile(member) if member.isfile() else None
                dest.addfile(member, data)
        output.write_bytes(gzip.compress(packed.getvalue(), compresslevel=9, mtime=0))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name + ".sha256").write_text(f"{digest}  {output.name}\n")
    return output


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: archive-release.py TAG OUTPUT")
    try:
        create_archive(sys.argv[1], Path(sys.argv[2]))
    except ArchiveError as exc:
        raise SystemExit(str(exc))
