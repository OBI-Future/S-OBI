from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.download_data import extract_archive, verify_sha256


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DownloadTests(unittest.TestCase):
    def test_extract_strips_release_root_and_ignores_macos(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            archive = tmp_path / "sentence-OBI.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(
                    "sentence-OBI/benchmark_tasks/T1_sentence_meaning_order.jsonl", "{}\n"
                )
                bundle.writestr("sentence-OBI/images/example.png", b"png")
                bundle.writestr("__MACOSX/._sentence-OBI", b"metadata")
            output = tmp_path / "data" / "sentence-OBI"
            extract_archive(archive, output)
            self.assertTrue((output / "benchmark_tasks/T1_sentence_meaning_order.jsonl").is_file())
            self.assertEqual((output / "images/example.png").read_bytes(), b"png")
            self.assertFalse((output / "__MACOSX").exists())

    def test_hash_failure_does_not_extract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            archive = tmp_path / "sentence-OBI.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("sentence-OBI/file.txt", "data")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_sha256(archive, "0" * 64)
            self.assertFalse((tmp_path / "data").exists())

    def test_traversal_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            archive = tmp_path / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("sentence-OBI/../../escape.txt", "no")
            with self.assertRaisesRegex(ValueError, "unsafe ZIP member path"):
                extract_archive(archive, tmp_path / "out")
            self.assertFalse((tmp_path / "escape.txt").exists())

    def test_overwrite_requires_existing_sobi_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            archive = tmp_path / "sentence-OBI.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr(
                    "sentence-OBI/benchmark_tasks/T1_sentence_meaning_order.jsonl", "{}\n"
                )
            output = tmp_path / "existing"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "existing S-OBI dataset"):
                extract_archive(archive, output, overwrite=True)


if __name__ == "__main__":
    unittest.main()
