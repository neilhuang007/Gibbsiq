"""Portable source verification for pinned optional integration stacks."""

from __future__ import annotations

import hashlib
from importlib.metadata import PackageNotFoundError
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from gibbsiq.qualification.adapters._pinned import verify_stack


class PinnedStackTests(unittest.TestCase):
    def test_python_source_hash_accepts_lf_and_crlf_but_rejects_changed_content(self) -> None:
        expected = hashlib.sha256(b"first\nsecond\n").hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "adapter.py"
            for payload in (b"first\nsecond\n", b"first\r\nsecond\r\n"):
                with self.subTest(payload=payload):
                    source.write_bytes(payload)
                    with patch("importlib.metadata.version", return_value="1.0"):
                        verify_stack(
                            adapter="Test",
                            module_file=str(source),
                            distribution_versions={"test": "1.0"},
                            source_hashes={"adapter.py": expected},
                            source_revision="revision",
                            python_version=None,
                            error_type=RuntimeError,
                        )

            source.write_bytes(b"first\nchanged\n")
            with patch("importlib.metadata.version", return_value="1.0"):
                with self.assertRaisesRegex(RuntimeError, "differs from pinned revision"):
                    verify_stack(
                        adapter="Test",
                        module_file=str(source),
                        distribution_versions={"test": "1.0"},
                        source_hashes={"adapter.py": expected},
                        source_revision="revision",
                        python_version=None,
                        error_type=RuntimeError,
                    )

    def test_python_pin_can_be_omitted_without_wrapping_missing_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "adapter.py"
            source.write_bytes(b"pinned\n")
            with (
                patch("importlib.metadata.version", side_effect=PackageNotFoundError),
                patch.object(sys, "version_info", (9, 9, 9)),
            ):
                with self.assertRaises(PackageNotFoundError):
                    verify_stack(
                        adapter="Z1T",
                        module_file=str(source),
                        distribution_versions={"z1t": "0.0.1"},
                        source_hashes={"adapter.py": hashlib.sha256(b"pinned\n").hexdigest()},
                        source_revision="test",
                        python_version=None,
                        error_type=RuntimeError,
                        wrap_missing=False,
                    )


if __name__ == "__main__":
    unittest.main()
