"""Shared paths for bundled evaluation fixtures."""

from pathlib import Path


FIXTURE_DIRECTORY = Path(__file__).resolve().parents[2] / "src" / "gibbsiq" / "data" / "evaluation"
