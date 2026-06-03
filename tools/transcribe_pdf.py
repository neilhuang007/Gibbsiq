"""Extract a faithful UTF-8 text transcription from a born-digital PDF.

The reference-pack papers are arXiv / publisher PDFs with a clean embedded
text layer, so a text-layer extraction (``pdftotext``) reproduces prose,
equations, and reference lists accurately -- unlike a vision/OCR pass, which
hallucinates author names and equations. This helper wraps ``pdftotext`` and
applies the light, lossless cleanup needed before hand-formatting into
Markdown:

* ``-enc UTF-8 -nopgbrk`` so dashes/quotes survive and page-break form feeds
  are dropped;
* Unicode NFKC normalization, which maps ligatures (``ﬁ ﬂ ﬀ ﬃ ﬄ``) back to
  their ASCII letters;
* collapsing runs of blank lines.

It does not summarize, reorder, or invent content. Equation LaTeX and heading
structure are added by hand afterwards.

Usage:
    python tools/transcribe_pdf.py <input.pdf> [--out <output.txt>]

Requires ``pdftotext`` (poppler) on PATH.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

# Ligatures that NFKC handles, kept here only for documentation of intent.
LIGATURES = "ﬁﬂﬀﬃﬄ"


def extract_text(pdf_path: Path) -> str:
    """Return the cleaned UTF-8 text layer of ``pdf_path``."""
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext (poppler) is not on PATH")
    result = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-nopgbrk", str(pdf_path), "-"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8", errors="replace")
    return clean_text(text)


def clean_text(text: str) -> str:
    """Apply lossless normalization to raw ``pdftotext`` output."""
    # NFKC folds ligatures and compatibility forms to plain letters.
    text = unicodedata.normalize("NFKC", text)
    # Drop any stray form feeds and carriage returns.
    text = text.replace("\f", "").replace("\r", "")
    # Flag, but do not silently delete, replacement characters.
    # (They indicate a glyph pdftotext could not map; rare for these PDFs.)
    # Collapse 3+ blank lines into a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="input PDF path")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output .txt path (default: alongside the PDF)",
    )
    args = parser.parse_args(argv)

    text = extract_text(args.pdf)
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text, encoding="utf-8")
        replacement = text.count("�")
        note = f" ({replacement} unmapped glyphs)" if replacement else ""
        print(f"wrote {args.out}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
