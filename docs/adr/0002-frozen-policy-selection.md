# ADR 0002: Freeze policies before final evaluation

Status: accepted.

Choose execution settings on calibration and development inputs. Freeze the
selected settings, baseline, metrics, and error allocation before evaluating
held-out inputs.

A passing final evaluation produces a policy tied to the evaluated workload and
input identities. Search retains every candidate result, making the selection
and final decision reproducible.
