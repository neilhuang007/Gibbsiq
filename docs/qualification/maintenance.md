# Evidence maintenance

Keep each completed experiment together with its frozen plan, observations,
report, and environment. Retain baselines used in regression comparisons and
bundles referenced by exported policies.

## Inventory

`tools/qualification/retention_inventory.py` inventories local artifacts and
their sizes. Use its `--help` output to select the evidence roots to inspect.
Review retention by workload and purpose: release evidence, regression
baselines, development runs, and private inputs.

## Compatibility updates

When changing a numerical dependency, run
`tools/qualification/check_compatibility_update.py` with the proposed
environment. Record the new versions, source revisions, adapter results, and
regression comparison before updating the pinned requirements.

Use [incident response](incident-response.md) for a damaged bundle and
[release recovery](release-recovery.md) for a package defect.
