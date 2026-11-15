"""HX numerical quadrature convergence for all three real-fluid HX interfaces."""
from __future__ import annotations
from dataclasses import dataclass, replace
from .r718 import R718Inputs, solve_r718


@dataclass(frozen=True)
class HXResolution:
    segments: int
    condenser_UA_W_K: float
    source_UA_W_K: float
    intercool_UA_W_K: float
    worst_relative_change_from_previous: float | None


def hx_resolution_study(
    case: R718Inputs,
    resolutions: tuple[int, ...] = (24, 48, 96, 192, 384),
) -> tuple[HXResolution, ...]:
    if len(resolutions)<3 or any(n<8 for n in resolutions):
        raise ValueError("at least three valid resolutions required")
    if tuple(sorted(set(resolutions)))!=resolutions:
        raise ValueError("resolutions must be unique and increasing")
    studies=[]
    previous=None
    for n in resolutions:
        r=solve_r718(replace(case,segments=n))
        ua=(r.condenser.required_UA_W_per_K,
            r.evaporator.required_UA_W_per_K,
            0 if r.intercooler is None else r.intercooler.required_UA_W_per_K)
        change=(None if previous is None else max(
            abs(a-b)/max(abs(a),1.0) for a,b in zip(ua,previous)))
        studies.append(HXResolution(n,*ua,change))
        previous=ua
    return tuple(studies)
