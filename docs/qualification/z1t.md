# Evaluate a Z1T model

Install the [numerical integration environment](../installation.md), then run:

```console
gibbsiq qualify --example tiny-z1t --output runs/tiny --json
gibbsiq inspect runs/tiny --verify
```

The example generates a small complete model and synthetic token inputs. It
compares stochastic projection execution with the numerical reference, including
the final vocabulary head.

## Observe an operation

```python
from gibbsiq.qualification.adapters.z1t import NumericalZ1T

model = NumericalZ1T(seed=17)
result = model.forward(
    [0, 1, 2, 3],
    observe=("blocks.0.attn.qkv_proj",),
    retention="trace",
    max_trace_bytes=4096,
)
print(result.logits.shape)  # (4, 8)
capture = result.captures["blocks.0.attn.qkv_proj"]
print(capture.field.shape)  # (4, 20)
```

Use summary retention for min/max/mean/RMS statistics, or trace retention for
selected arrays. Projection paths and configuration are described in the
[adapter guide](model-adapter-contract.md).

## Tune sampling

```console
gibbsiq tune --example tiny-z1t --output runs/tiny-search --json
```

Search compares sampling settings on development inputs, then evaluates the
frozen selection on held-out inputs. The report records quality and modeled
spin-draw cost. See [policy search](policy-search-contract.md).

For local trained weights, follow the
[checkpoint workflow](trained-checkpoint-verification.md).
