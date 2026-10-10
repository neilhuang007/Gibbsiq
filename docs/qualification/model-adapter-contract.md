# Z1T adapter interface

`NumericalZ1T` wraps the pinned numerical model and exposes named projection
observations. Imports of JAX, Equinox, NumPy, and Z1T occur when the adapter is
used.

```python
from gibbsiq.qualification.adapters.z1t import NumericalZ1T

model = NumericalZ1T(seed=17)
result = model.forward([0, 1, 2, 3])
print(result.logits.shape)
```

The default `TinyZ1TConfig` uses one block, width 8, vocabulary 8, sequence
length 4, and sparse fan-in 4. The forward pass includes the vocabulary head.

## Observe projections

Pass named paths through `observe`. Each block exposes attention qkv/output and
MLP proj1/proj2 projections. Choose `retention="summaries"` for statistics or
`retention="trace"` for selected input, field, and output arrays. Set
`max_trace_bytes` for retained traces.

The adapter exposes operation metadata and an operation-map identity. Trusted
transform callbacks provide the seam used by stochastic profiles, keeping
execution and observation on the same traversal.

## Checkpoint execution

`adapters.z1t_checkpoint` loads a selected local checkpoint using the pinned
model structure. The checkpoint verification tools record its identity,
configuration, token inputs, and projection selection.

See the [Z1T walkthrough](z1t.md) and
[checkpoint workflow](trained-checkpoint-verification.md).
