#!/usr/bin/env python3
"""Download/check/extract the public sentence-OBI release asset safely."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


ARCHIVE_SHA256 = "bc58cd9bbaeedc24dc6032f54b2e7ade2425885a1a78482fcad49ed93cef6a6c"
DEFAULT_RELEASE_URL = (
    "https://github.com/OBI-Future/S-OBI/releases/download/v1.0.0/sentence-OBI.zip"
)
FORMAL_TASK_FILES = (
    "T1_sentence_meaning_order.jsonl",
    "T2_semantic_slots_qa.jsonl",
    "T3_order_sensitive.jsonl",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual.lower() != expected.strip().lower():
        raise ValueError(
            f"SHA-256 mismatch for {path}: expected {expected}, got {actual}"
        )


def _member_path(name: str) -> tuple[PurePosixPath, bool]:
    """Return safe destination path and whether it is an Apple metadata entry."""

    normalized = name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    parts = list(pure.parts)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe ZIP member path: {name!r}")
    if "__MACOSX" in parts or (parts and parts[-1] == ".DS_Store"):
        return PurePosixPath(), True
    if parts and parts[0] == "sentence-OBI":
        parts = parts[1:]
    if not parts:
        return PurePosixPath(), True
    return PurePosixPath(*parts), False


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    # Unix file type bits are stored in the high 16 bits of external_attr.
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def extract_archive(archive: Path, output: Path, *, overwrite: bool = False) -> None:
    """Extract the release ZIP into *output*, rejecting traversal and symlinks."""

    archive = archive.expanduser().resolve()
    raw_output = output.expanduser()
    if raw_output.is_symlink():
        raise ValueError(f"refusing to use symlink output path: {raw_output}")
    output = raw_output.resolve()
    if not archive.is_file():
        raise FileNotFoundError(archive)
    if output.exists() and not overwrite:
        raise FileExistsError(
            f"{output} already exists; pass --overwrite only when replacement is intended"
        )
    if output.exists() and overwrite:
        markers = output / "benchmark_tasks"
        if not output.is_dir() or not all((markers / name).is_file() for name in FORMAL_TASK_FILES):
            raise ValueError(
                "--overwrite is limited to an existing S-OBI dataset directory "
                "containing all three formal benchmark task files"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                relative, ignored = _member_path(info.filename)
                if ignored:
                    continue
                if _is_symlink(info):
                    raise ValueError(f"refusing symlink ZIP member: {info.filename!r}")
                destination = (temp_root / relative).resolve()
                try:
                    destination.relative_to(temp_root)
                except ValueError as exc:
                    raise ValueError(f"ZIP member escapes output: {info.filename!r}") from exc
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info, "r") as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
        if output.exists():
            if output.is_dir() and not output.is_symlink():
                shutil.rmtree(output)
            else:
                output.unlink()
        os.replace(temp_root, output)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise


def download_archive(url: str, destination: Path) -> Path:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target, length=1024 * 1024)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("--archive", type=Path, help="use an existing local ZIP")
    source.add_argument("--url", help="release asset URL")
    parser.add_argument("--dataset-root", type=Path, default=Path("data/sentence-OBI"))
    parser.add_argument("--sha256", default=ARCHIVE_SHA256, help="expected archive SHA-256")
    parser.add_argument(
        "--archive-cache",
        type=Path,
        help="where a URL download is cached (default: a temporary file)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing dataset-root after successful verification",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    temporary: Path | None = None
    try:
        if args.archive is not None:
            archive = args.archive.expanduser().resolve()
        else:
            url = args.url or DEFAULT_RELEASE_URL
            if args.archive_cache:
                archive = args.archive_cache.expanduser().resolve()
            else:
                handle = tempfile.NamedTemporaryFile(prefix="sobi-", suffix=".zip", delete=False)
                handle.close()
                temporary = Path(handle.name)
                archive = temporary
            print(f"Downloading {url}")
            download_archive(url, archive)
        verify_sha256(archive, args.sha256)
        print(f"Verified SHA-256: {args.sha256.lower()}")
        extract_archive(archive, args.dataset_root, overwrite=args.overwrite)
        print(f"Extracted dataset to {args.dataset_root}")
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
