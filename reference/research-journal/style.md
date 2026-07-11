# Writing style for the research journal

This file defines the writing tone for every entry in `reference/research-journal/`
and, by extension, for the prose in the `reference/` pack. The journal is a
publication-grade record: its methodology and decisions are meant to transcribe
directly into the final paper without being reconstructed from code and git
history. Write each entry as if it were a section of that paper.

## Where the style comes from

The reference tone follows the project's anchor paper, Jelinčič et al. 2025, "An
Efficient Probabilistic Hardware Architecture for Diffusion-like Models"
(arXiv:2510.23972v2). Read the primary PDF for its register. The local Markdown at
`reference/01-architecture/papers/jelincic-2025-probabilistic-hardware-architecture.md`
is a source guide and withdrawal notice; it is not a quotation corpus.

The paper states a problem, names the mechanism that addresses it, distinguishes
measurement from system-level modeling, and marks limitations. Apply those traits
without imitating sentences. The companion lab note demonstrates the expected
source-level distinctions in a shorter local form.

## Voice and register

- **Declarative and present-tense.** State what a thing is and what it does:
  "The oracle recomputes each witness objective from the input model." Reserve
  past tense for the work actually performed in the session ("Stage 2 lowered the
  IR into THRML programs").
- **First person plural for decisions and actions**, matching the paper's "we
  propose / we demonstrate / we measured." Use it for choices made and work done,
  not as filler.
- **Precise and quantitative.** Every claim that can carry a number carries one,
  with units and provenance: "diagnostics_seconds = 0.0255, about 2% of
  sample_seconds = 1.262"; "corpus checksum `afb035ee...f40fe`"; "worst relative
  error 4.9e-15". Name mechanisms, files, and symbols exactly (`blocks.py`,
  `gamma_i = h_i + sum_j J_ij s_j`, DSATUR, `traces["beta_schedule"]`).
- **One claim per sentence, mechanism before consequence.** Say why a decision
  holds, then what it buys: "Every recorded read is collected at constant
  `config.beta`, so the stationarity precondition holds by construction."

## Direct tone: state the positive fact

Write what a thing is, does, or requires. Do not define it by what it is not, and
do not lean on the "not X but Y" contrast as a sentence pattern — it reads as
robotic filler and buries the fact the reader needs.

- Avoid: "This is not just a diagnostics package but a full optimization stack."
  Write: "Gibbsiq provides the optimization stack above THRML: ingestion, audited
  lowering, block construction, schedules, diagnostics, and benchmark
  verification."
- Avoid: "not merely best-known-to-date."
  Write: "every fixture's optimum is proven by exhaustive enumeration."
- Avoid: "not yet implemented."
  Write: "remains to be built," or state the required next action.

A contrast is allowed when both sides carry real content and the rejected side is
a genuine alternative — the paper's "Rather than implementing sampling in
software on general-purpose processors, we construct circuits that directly
implement the conditional" is substantive, not a tic. Even then, prefer stating
the chosen mechanism directly and recording the rejected path under "Rejected
Alternatives."

## Concreteness

- Tie every non-obvious claim to a source, a measurement, or a file location.
  Sources are primary references with identifiers (arXiv, DOI, a repository
  commit, a file:line), not tool names — record "Vehtari et al. 2021, Bayesian
  Analysis 16(2)," not "the search tool."
- Report exact artifacts: file paths, line counts, SHA-256 checksums, seeds, test
  counts, and the command that reproduces them.
- State limitations and open items plainly in their own section, as the paper
  states its limitations: name the gap and the condition that closes it.

## What to leave out

- No emojis, and no decorative `**bold**` / `*italic*` emphasis used for rhetoric.
  The paper uses none; a symbol or an emphasized word is not an argument. Reserve
  emphasis for a genuine term of art on first definition, if at all. Use status
  words ("Complete / Current target / Pending") rather than symbols.
- No marketing adjectives ("powerful," "seamless," "cutting-edge") and no
  hedging filler ("basically," "essentially," "it is worth noting that").
- No vague verbs where a specific one exists: prefer "recomputes," "rejects,"
  "pins," "lowers" over "handles," "deals with," "supports" when the precise
  action is known.

## Structure of an entry

Lead with the paper connection and the reasoning, then the decisions, then the
evidence. The strongest existing entries
(`2026-07-02-stage-03-diagnostics-pipeline.md`,
`2026-07-01-stage-02-thrml-runtime-implementation.md`) follow this skeleton;
match it, using only the sections an entry needs:

1. **Title and date** — `# YYYY-MM-DD - Topic`.
2. **Paper Hook** — the paper section this entry feeds (methods, framing,
   limitations) in one or two sentences.
3. **Context** — the state before the work and the problem the entry addresses.
4. **Hard-Parts Analysis** — the points that required genuine design, numbered
   `H1..Hn`, each with the difficulty and the binding resolution. Lead with this
   whenever the work had non-trivial reasoning; it is the paper's contribution
   argument in miniature.
5. **Decisions** — the choices made, each with its reason and the mechanism.
6. **Rejected Alternatives** — the paths not taken and why, so a later reader does
   not reopen a closed question.
7. **Sources Read / Examples Used** — primary references and fixtures, with
   identifiers.
8. **Follow-Up / Open Items** — named gaps and their closing conditions.
9. **Verification** — the commands run, counts, and measured results.

Entries are append-only. When a decision is later revised, add a new dated entry
rather than rewriting an old one; refining the prose of an existing entry is
allowed, but its facts, numbers, and recorded decisions stay as they were on the
entry's date.

## Math and Markdown

Follow the rules in `CLAUDE.md` -> "Markdown LaTeX math formatting": inline math
as `$...$`; every display equation in multiline form with `$$` alone on its own
line; `\lt` / `\gt` in place of literal `<` / `>`; no punctuation on a `$$` line.
Reuse the project's domain symbols (`h`, `J`, `beta`, `gamma`, `s_i in {-1,+1}`)
rather than inventing notation.

## Checklist before committing an entry

- The first paragraphs say what problem the work solved and why the approach
  holds, in declarative present tense.
- No sentence defines its subject by what it is not; no "not X but Y" filler.
- No emojis and no rhetorical emphasis; status words replace symbols.
- Every number carries units and a source or a reproducing command; every
  external claim carries a primary-reference identifier.
- Limitations and open items are stated plainly with their closing conditions.
- Display math is multiline and uses `\lt` / `\gt`; symbols match the project
  convention.
