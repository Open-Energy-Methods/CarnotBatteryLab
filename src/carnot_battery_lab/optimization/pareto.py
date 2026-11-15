"""Verified Pareto filtering for feasible design *evaluations*.

This module does not optimise hardware or simulate a hybrid cycle. It filters
objective vectors with all objectives minimized, while rejecting infeasible
candidate designs. Tie vectors remain in the input order; no false dominance.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class EvaluatedDesign:
    identifier: str
    objectives: tuple[float, ...]
    feasible: bool
    evidence_reference: str

    def __post_init__(self) -> None:
        if not self.identifier.strip() or not self.evidence_reference.strip():
            raise ValueError("design must have identifier and run-evidence reference")
        if not self.objectives or not all(math.isfinite(x) for x in self.objectives):
            raise ValueError("objectives must be nonempty finite values")


def non_dominated_designs(designs: list[EvaluatedDesign]) -> list[EvaluatedDesign]:
    """Filter min-objective feasible points; numerical uncertainty is external."""
    if not designs:
        return []
    dimensions = len(designs[0].objectives)
    if any(len(x.objectives) != dimensions for x in designs):
        raise ValueError("inconsistent objective dimensions")
    feasible = [x for x in designs if x.feasible]
    out=[]
    for i,candidate in enumerate(feasible):
        if not any(
            i != j
            and all(a <= b for a,b in zip(other.objectives,candidate.objectives))
            and any(a < b for a,b in zip(other.objectives,candidate.objectives))
            for j,other in enumerate(feasible)
        ):
            out.append(candidate)
    return out
