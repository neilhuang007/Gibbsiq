"""Read allocation shared by the reference sampler and the THRML runtime."""

from __future__ import annotations

__all__ = ["reads_by_chain"]


def reads_by_chain(num_reads: int, num_chains: int) -> tuple[int, ...]:
    """Distribute reads with chain lengths differing by at most one."""
    base, remainder = divmod(num_reads, num_chains)
    return tuple(base + (chain_index < remainder) for chain_index in range(num_chains))
