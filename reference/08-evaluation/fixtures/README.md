# Evaluation Fixtures

These JSON files are intended to become test inputs. They are also readable examples of the expected Gibbsiq contract.

Files:

- `exact-small-instances.json` - exact energies, conversions, conditionals, Boltzmann probabilities, and Max-Cut outputs.
- `diagnostic-fixtures.json` - synthetic traces and sample counts for diagnostics.

Run the evaluator:

```bash
python -m gibbsiq.evaluation examples/evaluation-candidate.example.json
```

Candidate input format:

```json
{
  "results": [
    {
      "id": "fixture_id",
      "actual": {
        "field_from_expected_fixture": "candidate value"
      }
    }
  ]
}
```

The command prints a JSON report and exits with status `0` only when every known fixture passes.

Rules:

- Treat these as source-controlled golden fixtures.
- Do not regenerate expected outputs silently.
- If a formula changes, update `../equation-audit.md` first.
- Energies use the Gibbsiq convention from `../equation-audit.md`.
- Floating-point comparisons should use absolute tolerance `1e-9` unless the fixture says otherwise.
