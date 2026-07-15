# Gibbsiq Inspector Summary

- Schema: `gibbsiq.inspector.summary.v1`
- Samples: 4
- Variables: 2
- Vartype: `SPIN`
- Model association: `caller_supplied_sample_checked`

## Best stored row

- Row: 1
- Stored interaction energy: -2.5
- Stored total energy: 1.75

## Complete machine-readable summary

```json
{
  "artifact": {
    "categorical_num_states_by_position": null,
    "sample_count": 4,
    "source_type": "SampleResult",
    "variable_count": 2,
    "variable_order": [
      {
        "label": {
          "kind": "str",
          "value": "alpha"
        },
        "position": 0
      },
      {
        "label": {
          "kind": "str",
          "value": "beta"
        },
        "position": 1
      }
    ],
    "vartype": "SPIN"
  },
  "availability": {
    "baseline_comparison": {
      "reason": "no matched baseline artifact is associated with this result",
      "status": "not_available"
    },
    "block_schedule": {
      "reason": "SampleResult contains no compiled block schedule",
      "status": "not_available"
    },
    "compiled_manifest": {
      "reason": "compiled-manifest binding is deferred to TM-API-001 and TM-REP-001",
      "status": "not_available"
    },
    "constraint_feasibility": {
      "reason": "no general constraint contract is associated with this result",
      "status": "not_available"
    },
    "html_report": {
      "reason": "static HTML rendering is deferred to TM-REP-001",
      "status": "not_available"
    },
    "thermodynamic_profile": {
      "reason": "no profiler artifact is associated with this result",
      "status": "not_available"
    },
    "topology": {
      "reason": "SampleResult contains no topology artifact",
      "status": "not_available"
    }
  },
  "best_row": {
    "index": 1,
    "sample_values": [
      -1,
      1
    ],
    "selection_basis": "first_argmin_stored_interaction_energy",
    "stored_interaction_energy": -2.5,
    "stored_total_energy": 1.75,
    "variable_order": [
      {
        "label": {
          "kind": "str",
          "value": "alpha"
        },
        "position": 0
      },
      {
        "label": {
          "kind": "str",
          "value": "beta"
        },
        "position": 1
      }
    ]
  },
  "diagnostics": {
    "data": {
      "flags": [
        "chain_disagreement"
      ],
      "future_metric": {
        "status": "experimental",
        "value": 17
      }
    },
    "source": "result.diagnostics",
    "status": "available"
  },
  "metadata": {
    "data": {
      "artifact_case": "gq-inspect-01",
      "backend": "stored-artifact-only",
      "best_sample_selection_basis": "offset-free Ising interaction energy",
      "conversion_offset": 4.25,
      "input_offset": 4.25,
      "reported_energy_collision_count": 0,
      "seed": 481,
      "source_format": "ising",
      "source_model_format": "ising",
      "timing": {
        "sample_seconds": 0.125
      },
      "variable_order": [
        "alpha",
        "beta"
      ],
      "versions": {
        "gibbsiq": "0.1.0"
      }
    },
    "source": "result.metadata",
    "status": "available"
  },
  "model_association": {
    "association_source": "caller_supplied_model",
    "checked_row_count": 4,
    "fingerprint_encoding": "canonical_utf8_json_sorted_keys_compact",
    "fingerprint_payload": {
      "linear": [
        "0x1.8000000000000p-1",
        "-0x1.4000000000000p+0"
      ],
      "num_variables": 2,
      "offset": "0x1.1000000000000p+2",
      "quadratic": [
        [
          0,
          1,
          "0x1.0000000000000p-1"
        ]
      ],
      "schema": "gibbsiq.ising_energy.v1",
      "vartype": "SPIN"
    },
    "fingerprint_schema": "gibbsiq.ising_energy.v1",
    "model_fingerprint": "a7b042c433de7bb4c0ec3d71cfa63296019744fcfaae2f2d0761874a75291ff5",
    "model_offset": 4.25,
    "objective_recomputation": {
      "method": "all_rows_total_and_interaction_energy",
      "status": "available"
    },
    "relative_tolerance": 0.0,
    "result_vartype": "SPIN",
    "status": "caller_supplied_sample_checked",
    "variable_order": [
      {
        "label": {
          "kind": "str",
          "value": "alpha"
        },
        "position": 0
      },
      {
        "label": {
          "kind": "str",
          "value": "beta"
        },
        "position": 1
      }
    ],
    "verification_tolerance": 1e-09
  },
  "schema_version": "gibbsiq.inspector.summary.v1",
  "stored_energies": {
    "interaction": [
      0.0,
      -2.5,
      1.5,
      1.0
    ],
    "status": "stored_artifact_values",
    "total": [
      4.25,
      1.75,
      5.75,
      5.25
    ]
  },
  "traces": {
    "data": {
      "chain_labels": [
        "alpha",
        "beta"
      ],
      "energy": [
        [
          6.0,
          4.0
        ],
        [
          5.0,
          4.0
        ]
      ]
    },
    "source": "result.traces",
    "status": "available"
  },
  "warnings": {
    "items": [
      "chain_disagreement"
    ],
    "source": "result.diagnostics.flags",
    "status": "available"
  }
}
```
