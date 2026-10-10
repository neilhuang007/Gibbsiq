# Gibbsiq

Python models and sampling tools for QUBO and Ising problems.

Requires Python 3.10 or newer. Install with `python -m pip install .`.

```python
from gibbsiq import compile_ising

model = compile_ising({"a": 0.25}, {})
print(model.energy({"a": 1}))
```
