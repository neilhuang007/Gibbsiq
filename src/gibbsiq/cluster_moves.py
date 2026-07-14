"""Isoenergetic cluster moves for replica-coupled optimization.

This module implements the disagreement-cluster primitive used by adaptive
parallel tempering with isoenergetic cluster moves (APT+ICM) in Chowdhury et
al., Nature Communications 16, 9193 (2025), arXiv:2503.10302.

An ICM couples two same-temperature replicas.  It is an optimization move, not
a single-chain Gibbs update, and the resulting replica traces are dependent.
Callers must not interpret the two outputs as independent chains for sampler
diagnostics.

This is the general-field disagreement-cluster primitive rather than the full
Algorithm S2.  The paper's cluster-larger-than-half shortcut globally flips one
zero-field replica; that shortcut is intentionally absent because linear Ising
fields break its isoenergetic invariant.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from gibbsiq.model import IsingModel, SpinSample, Variable, sample_to_spin

SelectionMethod = Literal["component_index", "rng", "seed", "none"]
MoveReason = Literal["applied", "replicas_identical"]
PAIR_ENERGY_ABS_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class IsoenergeticClusterMove:
    """Result and audit record for one replica-coupling cluster move.

    ``replica_a`` and ``replica_b`` are immutable copies.  Component and
    disagreement tuples follow ``model.variables`` order, so mixed-type labels
    never require cross-type comparison.
    """

    replica_a: Mapping[Variable, int]
    replica_b: Mapping[Variable, int]
    applied: bool
    reason: MoveReason
    disagreement_variables: tuple[Variable, ...]
    components: tuple[tuple[Variable, ...], ...]
    selected_component_index: int | None
    selected_component: tuple[Variable, ...]
    selected_component_size: int
    selection_method: SelectionMethod
    seed: int | None
    energy_before: tuple[float, float]
    energy_after: tuple[float, float]
    combined_energy_before: float
    combined_energy_after: float
    combined_energy_residual: float

    @property
    def combined_energy_invariant(self) -> bool:
        """Whether the pair-energy residual is within floating-point error."""
        return math.isclose(
            self.combined_energy_residual,
            0.0,
            rel_tol=0.0,
            abs_tol=PAIR_ENERGY_ABS_TOLERANCE,
        )

    def to_metadata(self) -> dict[str, object]:
        """Return a plain-container audit mapping without replica samples."""
        return {
            "move": "isoenergetic_cluster",
            "semantics": "optimization_only_replica_coupling",
            "replicas_are_independent": False,
            "same_temperature_required": True,
            "applied": self.applied,
            "reason": self.reason,
            "disagreement_variables": list(self.disagreement_variables),
            "components": [list(component) for component in self.components],
            "component_count": len(self.components),
            "selected_component_index": self.selected_component_index,
            "selected_component": list(self.selected_component),
            "selected_component_size": self.selected_component_size,
            "selection_method": self.selection_method,
            "seed": self.seed,
            "energy_before": list(self.energy_before),
            "energy_after": list(self.energy_after),
            "combined_energy_before": self.combined_energy_before,
            "combined_energy_after": self.combined_energy_after,
            "combined_energy_residual": self.combined_energy_residual,
            "combined_energy_tolerance": PAIR_ENERGY_ABS_TOLERANCE,
            "combined_energy_invariant": self.combined_energy_invariant,
        }


def _validated_spins(
    model: IsingModel,
    sample: SpinSample,
    *,
    name: str,
) -> dict[Variable, int]:
    if not isinstance(sample, Mapping):
        raise TypeError(f"{name} must be a mapping from model variables to spins")

    model_variables = set(model.variables)
    sample_variables = set(sample)
    missing = tuple(variable for variable in model.variables if variable not in sample_variables)
    extra = tuple(variable for variable in sample if variable not in model_variables)
    if missing or extra:
        raise ValueError(
            f"{name} variables must match model.variables exactly; missing={missing!r}, extra={extra!r}"
        )
    return sample_to_spin(sample, model.variables, "SPIN")


def _disagreement_components(
    model: IsingModel,
    replica_a: Mapping[Variable, int],
    replica_b: Mapping[Variable, int],
) -> tuple[tuple[Variable, ...], tuple[tuple[Variable, ...], ...]]:
    disagreement = tuple(
        variable for variable in model.variables if replica_a[variable] != replica_b[variable]
    )
    if not disagreement:
        return (), ()

    disagreement_set = set(disagreement)
    adjacency: dict[Variable, list[Variable]] = {variable: [] for variable in disagreement}
    for left, right in model.graph:
        if left in disagreement_set and right in disagreement_set:
            adjacency[left].append(right)
            adjacency[right].append(left)

    order = {variable: position for position, variable in enumerate(model.variables)}
    components: list[tuple[Variable, ...]] = []
    unseen = set(disagreement)
    for start in disagreement:
        if start not in unseen:
            continue
        unseen.remove(start)
        stack = [start]
        component: list[Variable] = []
        while stack:
            variable = stack.pop()
            component.append(variable)
            for neighbor in reversed(adjacency[variable]):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        component.sort(key=order.__getitem__)
        components.append(tuple(component))
    return disagreement, tuple(components)


def _selection_source(
    *,
    rng: random.Random | None,
    seed: int | None,
    component_index: int | None,
) -> SelectionMethod:
    if rng is not None and not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError("seed must be an integer and must not be boolean")
    if component_index is not None and (
        isinstance(component_index, bool) or not isinstance(component_index, int)
    ):
        raise TypeError("component_index must be an integer and must not be boolean")

    supplied = sum(value is not None for value in (rng, seed, component_index))
    if supplied > 1:
        raise ValueError("provide only one of rng, seed, or component_index")
    if component_index is not None:
        return "component_index"
    if rng is not None:
        return "rng"
    if seed is not None:
        return "seed"
    return "none"


def isoenergetic_cluster_move(
    model: IsingModel,
    replica_a: SpinSample,
    replica_b: SpinSample,
    *,
    rng: random.Random | None = None,
    seed: int | None = None,
    component_index: int | None = None,
) -> IsoenergeticClusterMove:
    """Flip one connected disagreement component in two replicas.

    Exactly one of ``rng``, ``seed``, or ``component_index`` selects a cluster.
    A selector may be omitted only when the replicas are identical and the move
    is therefore a deterministic no-op.  ``component_index`` is exposed for
    replay and audit; component order is deterministic in ``model.variables``
    order.

    Algorithm S2 uses a global flip of one replica when the selected component
    exceeds half the model.  That zero-field shortcut is deliberately excluded:
    it does not preserve pair energy for a general ``IsingModel`` with linear
    fields.  This function always applies the portable cluster flip to both
    replicas.  The caller is responsible for pairing replicas governed by the
    same model and inverse temperature; this model-level primitive cannot verify
    a runtime temperature assignment.
    """
    if not isinstance(model, IsingModel):
        raise TypeError("model must be an IsingModel")

    selection_method = _selection_source(
        rng=rng,
        seed=seed,
        component_index=component_index,
    )
    spins_a = _validated_spins(model, replica_a, name="replica_a")
    spins_b = _validated_spins(model, replica_b, name="replica_b")
    disagreement, components = _disagreement_components(model, spins_a, spins_b)

    energy_before = (model.energy(spins_a), model.energy(spins_b))
    combined_before = math.fsum(energy_before)

    if not components:
        if component_index is not None:
            raise ValueError("component_index cannot select from identical replicas")
        return IsoenergeticClusterMove(
            replica_a=MappingProxyType(dict(spins_a)),
            replica_b=MappingProxyType(dict(spins_b)),
            applied=False,
            reason="replicas_identical",
            disagreement_variables=(),
            components=(),
            selected_component_index=None,
            selected_component=(),
            selected_component_size=0,
            selection_method=selection_method,
            seed=seed,
            energy_before=energy_before,
            energy_after=energy_before,
            combined_energy_before=combined_before,
            combined_energy_after=combined_before,
            combined_energy_residual=0.0,
        )

    if selection_method == "none":
        raise ValueError("provide rng, seed, or component_index when disagreement clusters exist")
    if component_index is not None:
        if component_index < 0 or component_index >= len(components):
            raise ValueError(f"component_index must be in [0, {len(components) - 1}], got {component_index}")
        selected_index = component_index
    elif rng is not None:
        selected_index = rng.randrange(len(components))
    else:
        selected_index = random.Random(seed).randrange(len(components))

    selected_component = components[selected_index]
    moved_a = dict(spins_a)
    moved_b = dict(spins_b)
    for variable in selected_component:
        moved_a[variable] = -moved_a[variable]
        moved_b[variable] = -moved_b[variable]

    energy_after = (model.energy(moved_a), model.energy(moved_b))
    combined_after = math.fsum(energy_after)
    residual = combined_after - combined_before
    return IsoenergeticClusterMove(
        replica_a=MappingProxyType(moved_a),
        replica_b=MappingProxyType(moved_b),
        applied=True,
        reason="applied",
        disagreement_variables=disagreement,
        components=components,
        selected_component_index=selected_index,
        selected_component=selected_component,
        selected_component_size=len(selected_component),
        selection_method=selection_method,
        seed=seed,
        energy_before=energy_before,
        energy_after=energy_after,
        combined_energy_before=combined_before,
        combined_energy_after=combined_after,
        combined_energy_residual=residual,
    )
