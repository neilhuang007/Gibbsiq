# Installation

## Core

Use Python 3.10 or newer:

```console
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on Linux/macOS or
`.venv\Scripts\Activate.ps1` in PowerShell, then install from the repository:

```console
python -m pip install .
gibbsiq doctor
```

The core provides discrete models, exact references, diagnostics, qualification,
and offline inspection using the standard library.

## Optional features

| Install command | Feature |
| --- | --- |
| `python -m pip install ".[qualification]"` | NumPy array artifacts |
| `python -m pip install ".[dimod]"` | dimod conversion |
| `python -m pip install ".[networkx]"` | NetworkX import |
| `python -m pip install ".[thrml]"` | THRML sampling |
| `python -m pip install ".[arviz]"` | ArviZ diagnostic crosschecks |

## Numerical integration environment

Use a separate Python 3.13.5 environment for the pinned THRML, Torx, and Z1T
integration stack. The requirements file records numerical versions and source
revisions:

```console
python -m pip install -r requirements/qualification-integration.txt
python -m pip install .
python -m pip check
gibbsiq doctor --json
```

Set `JAX_PLATFORMS=cpu` and `JAX_ENABLE_X64=false` for the CPU integration
profile. See the [Z1T walkthrough](qualification/z1t.md) for model examples.
