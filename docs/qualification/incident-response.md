# Recover an experiment

Start by inspecting the saved directory:

```console
gibbsiq inspect runs/experiment --verify --json
```

Read the execution state and reason, then choose the matching action.

| Situation | Action |
| --- | --- |
| Interrupted matching plan | Resume with the original arguments and `--resume` |
| Changed workload or settings | Start in a new output directory |
| Invalid or corrupted evidence | Preserve the directory and reproduce in a fresh one |
| Completed quality failure | Compare the observations with the declared reference |
| Dependency mismatch | Recreate the pinned integration environment |

Record the command, package version, environment, and minimal input in the issue.
Use synthetic inputs for a public reproduction and keep private run data local.

The workflow preserves completed attempts when resuming, so previous execution
evidence remains available for diagnosis. See the
[Python workflow](workflow-contract.md) for recovery semantics.
