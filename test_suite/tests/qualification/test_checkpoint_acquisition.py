"""Tests for the explicit pinned Z1T-0 checkpoint acquisition command."""

from __future__ import annotations

import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


TOOL = Path(__file__).parents[3] / "tools" / "qualification" / "acquire_z1t_checkpoint.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("acquire_z1t_checkpoint", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Response(io.BytesIO):
    pass


class InterruptedResponse(Response):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.calls = 0

    def read(self, size=-1):
        self.calls += 1
        if self.calls > 1:
            raise TimeoutError("controlled interruption")
        return super().read(min(size, 3))


class CheckpointAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tool = load_tool()

    def spec(self, payload: bytes, *, name: str = "fixture.bin"):
        return self.tool.ArtifactSpec(
            name=name,
            url="https://example.invalid/pinned/fixture.bin",
            size=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    @staticmethod
    def ample_disk(_path):
        return shutil._ntuple_diskusage(20 << 30, 1 << 30, 19 << 30)

    def test_streams_byte_exact_payload_and_atomically_publishes(self) -> None:
        payload = b"controlled payload split across reads"
        calls = []

        def opener(request, *, timeout):
            calls.append((request.full_url, timeout))
            return Response(payload)

        with tempfile.TemporaryDirectory() as temporary:
            result = self.tool.acquire_artifact(
                self.spec(payload), Path(temporary), opener=opener, disk_usage=self.ample_disk
            )
            target = Path(temporary) / "fixture.bin"
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(result.status, "downloaded")
            self.assertEqual(calls, [("https://example.invalid/pinned/fixture.bin", 60.0)])
            self.assertFalse(list(Path(temporary).glob("*.part")))

    def test_interrupted_download_never_appears_complete(self) -> None:
        payload = b"abcdefghi"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(TimeoutError, "controlled interruption"):
                self.tool.acquire_artifact(
                    self.spec(payload),
                    Path(temporary),
                    opener=lambda *_args, **_kwargs: InterruptedResponse(payload),
                    disk_usage=self.ample_disk,
                )
            self.assertFalse((Path(temporary) / "fixture.bin").exists())
            self.assertFalse(list(Path(temporary).glob("*.part")))

    def test_refuses_oversized_response_and_removes_partial(self) -> None:
        expected = b"small"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "exceeds expected byte count"):
                self.tool.acquire_artifact(
                    self.spec(expected),
                    Path(temporary),
                    opener=lambda *_args, **_kwargs: Response(expected + b"!"),
                    disk_usage=self.ample_disk,
                )
            self.assertFalse((Path(temporary) / "fixture.bin").exists())
            self.assertFalse(list(Path(temporary).glob("*.part")))

    def test_rejects_digest_mismatch_without_publishing(self) -> None:
        expected = b"expected"
        same_size_wrong_content = b"modified"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                self.tool.acquire_artifact(
                    self.spec(expected),
                    Path(temporary),
                    opener=lambda *_args, **_kwargs: Response(same_size_wrong_content),
                    disk_usage=self.ample_disk,
                )
            self.assertFalse((Path(temporary) / "fixture.bin").exists())

    def test_total_deadline_is_enforced_between_reads(self) -> None:
        payload = b"deadline"
        clock = mock.Mock(side_effect=[0.0, 0.0, self.tool.TOTAL_TIMEOUT_SECONDS + 0.01])
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(TimeoutError, "exceeded 1200 seconds"):
                self.tool.acquire_artifact(
                    self.spec(payload),
                    Path(temporary),
                    opener=lambda *_args, **_kwargs: Response(payload),
                    disk_usage=self.ample_disk,
                    clock=clock,
                )
            self.assertFalse((Path(temporary) / "fixture.bin").exists())

    def test_rejects_insufficient_disk_before_fetch(self) -> None:
        payload = b"payload"
        opener = mock.Mock()

        def low_disk(_path):
            return shutil._ntuple_diskusage(10 << 30, 9 << 30, self.tool.DISK_RESERVE_BYTES + len(payload) - 1)

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(OSError, "insufficient free disk"):
                self.tool.acquire_artifact(
                    self.spec(payload), Path(temporary), opener=opener, disk_usage=low_disk
                )
            opener.assert_not_called()

    def test_invalid_existing_target_is_untouched_and_not_fetched(self) -> None:
        payload = b"expected"
        opener = mock.Mock()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "fixture.bin"
            target.write_bytes(b"existing but wrong")
            with self.assertRaisesRegex(FileExistsError, "unexpected existing artifact"):
                self.tool.acquire_artifact(
                    self.spec(payload), Path(temporary), opener=opener, disk_usage=self.ample_disk
                )
            self.assertEqual(target.read_bytes(), b"existing but wrong")
            opener.assert_not_called()

    def test_valid_existing_target_is_reused_without_fetch(self) -> None:
        payload = b"already valid"
        opener = mock.Mock()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "fixture.bin"
            target.write_bytes(payload)
            result = self.tool.acquire_artifact(
                self.spec(payload), Path(temporary), opener=opener, disk_usage=self.ample_disk
            )
            self.assertEqual(result.status, "existing-valid")
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
