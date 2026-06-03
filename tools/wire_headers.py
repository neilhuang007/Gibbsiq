"""Prepend a canonical citation header to each transcription ``.md``.

Every per-paper transcription should point back to the single verified citation
record in ``reference/references.bib`` (rather than carry an independently typed
bibliography) and to its companion Gibbsiq lab note. This tool parses
``references.bib`` for each paper's DOI / arXiv id and inserts a short citation
blockquote immediately after the file's ``# Title`` heading.

It is idempotent: a file that already contains a ``**Citation.**`` marker is
left untouched, so the hand-written exemplar header (camsari-2018) is preserved
and re-runs are safe.

Usage:
    python tools/wire_headers.py            # wire every mapped paper
    python tools/wire_headers.py --check     # report only, change nothing
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BIB = REPO / "reference" / "references.bib"

# slug stem -> (bibtex key, section directory). One row per paper; the slug is
# the on-disk filename stem of the cleaned ``.md`` transcription.
PAPERS = [
    ("jelincic-2025-probabilistic-hardware-architecture", "jelincic2025", "01-architecture"),
    ("ayodele-2022-penalty-weights-permutation", "ayodele2022", "02-interfaces"),
    ("mucke-2025-qubolite", "mucke2025", "02-interfaces"),
    ("zaman-2021-pyqubo", "zaman2021", "02-interfaces"),
    ("pawlowski-2026-simulated-bifurcation-annealing", "pawlowski2026", "03-samplers"),
    ("tao-2026-tabu-simulated-bifurcation", "tao2026", "03-samplers"),
    ("turingq-2025-qis3-qubo-solver", "turingq2025", "03-samplers"),
    ("alessandroni-2025-quantum-big-m", "alessandroni2025bigm", "04-diagnostics"),
    ("alessandroni-2026-penalization-weights", "alessandroni2026weights", "04-diagnostics"),
    ("doucet-2026-qubo-encoding-thermodynamics", "doucet2026", "04-diagnostics"),
    ("turner-2018-sampler-diagnostics", "turner2018", "04-diagnostics"),
    ("vehtari-2021-rhat-ess", "vehtari2021", "04-diagnostics"),
    ("camsari-2016-stochastic-pbits-invertible-logic", "camsari2017invertible", "05-theory"),
    ("camsari-2018-probabilistic-spin-logic", "camsari2019pbits", "05-theory"),
    ("camsari-2025-pdits-extended-variable", "duffee2025pdits", "05-theory"),
    ("duffee-2026-pdit-ising-qap", "duffee2026qap", "05-theory"),
    ("lucas-2014-ising-formulations", "lucas2014", "05-theory"),
    ("magar-2025-pc-cop-pbit-accelerator", "magar2025", "05-theory"),
    ("onizawa-2026-parallel-pbit-ising", "onizawa2026", "05-theory"),
    ("arshad-2026-qubo-suspension-benchmark", "arshad2026", "06-benchmarks"),
    ("bernal-neira-2024-quantum-heuristics-ising-machines", "bernalneira2024", "06-benchmarks"),
    ("oshiyama-2022-qubo-heuristic-benchmark", "oshiyama2022", "06-benchmarks"),
    ("shaglel-2025-maxcut-ising-benchmark", "shaglel2025", "06-benchmarks"),
]


def parse_bib(text: str) -> dict[str, dict[str, str]]:
    """Return ``{key: {field: value}}`` for every entry in ``references.bib``."""
    entries: dict[str, dict[str, str]] = {}
    for block in re.split(r"\n@", text):
        head = re.match(r"@?\w+\{([^,]+),", block)
        if not head:
            continue
        key = head.group(1).strip()
        fields = dict(re.findall(r"(\w+)\s*=\s*\{(.+?)\}\s*,?\s*\n", block))
        entries[key] = fields
    return entries


def citation_block(key: str, fields: dict[str, str], slug: str) -> str:
    """Render the citation blockquote for one paper."""
    ids = []
    doi = fields.get("doi")
    eprint = fields.get("eprint") or (
        fields.get("howpublished", "").replace("arXiv:", "") or None
    )
    if doi:
        ids.append(f"DOI [{doi}](https://doi.org/{doi})")
    if eprint:
        ids.append(f"arXiv:[{eprint}](https://arxiv.org/abs/{eprint})")
    id_line = " · ".join(ids) if ids else "see entry for identifiers"
    return (
        f"> **Citation.** Canonical entry `{key}` in "
        f"[`references.bib`](../../references.bib) "
        f"(resolved via Crossref/DataCite). {id_line}.\n"
        f">\n"
        f"> **Companion note.** "
        f"[`{slug}.note.md`](./{slug}.note.md) — how this paper links to Gibbsiq.\n"
    )


def wire(text: str, block: str) -> str | None:
    """Insert ``block`` after the first H1. Return None if already wired."""
    if "**Citation.**" in text:
        return None
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = i + 1
            # Skip one trailing blank line after the H1, if present.
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            new = lines[:insert_at] + ["\n", block, "\n"] + lines[insert_at:]
            return "".join(new)
    # No H1: prepend.
    return block + "\n" + text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report only")
    args = parser.parse_args(argv)

    entries = parse_bib(BIB.read_text(encoding="utf-8"))
    wired, skipped, missing = 0, 0, 0
    for slug, key, section in PAPERS:
        path = REPO / "reference" / section / "papers" / f"{slug}.md"
        if not path.exists():
            print(f"MISSING  {path.relative_to(REPO)}")
            missing += 1
            continue
        if key not in entries:
            print(f"NO-KEY   {key} ({slug})")
            missing += 1
            continue
        block = citation_block(key, entries[key], slug)
        result = wire(path.read_text(encoding="utf-8"), block)
        if result is None:
            skipped += 1
            continue
        if not args.check:
            path.write_text(result, encoding="utf-8")
        wired += 1
        print(f"WIRED    {path.relative_to(REPO)}")
    print(f"\n{wired} wired, {skipped} already-wired, {missing} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
