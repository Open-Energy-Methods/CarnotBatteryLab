"""Counterflow finite-HX UA and pinch calculation (SI).

The specified duty and terminal temperatures must be thermodynamically
compatible; this is a *required-UA* calculation, not a heat-exchanger design.
The hot-fluid temperature curve can represent real-fluid superheat/condensation.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Callable


class InfeasibleHX(ValueError):
    """A temperature crossing, invalid input or insufficient HX UA."""


@dataclass(frozen=True)
class HXCheck:
    duty_W: float
    required_UA_W_per_K: float
    min_approach_K: float
    installed_UA_W_per_K: float
    segments: int

    @property
    def margin_UA_W_per_K(self) -> float:
        return self.installed_UA_W_per_K - self.required_UA_W_per_K


def required_ua_counterflow(
    *, duty_W: float, hot_temperature_K: Callable[[float], float],
    cold_in_K: float, cold_out_K: float, minimum_approach_K: float,
    installed_UA_W_per_K: float, segments: int = 100,
    cold_temperature_K: Callable[[float], float] | None = None,
) -> HXCheck:
    """Integrate d(UA)=dQ/(Th-Tc) for a counterflow exchanger.

    Fraction x=0 is hot inlet / cold outlet, x=1 hot outlet / cold inlet.
    A constant-heat-capacity cold stream is assumed unless a real-fluid
    state-based cold temperature profile is provided.
    This detects internal pinches missed by terminal-only LMTD.
    """
    values=(duty_W,cold_in_K,cold_out_K,minimum_approach_K,installed_UA_W_per_K)
    if not all(math.isfinite(v) for v in values):
        raise InfeasibleHX("non-finite HX inputs")
    if duty_W <= 0 or cold_in_K <= 0 or cold_out_K < cold_in_K:
        raise InfeasibleHX("positive duty and non-cooling cold stream required")
    if minimum_approach_K <= 0 or installed_UA_W_per_K <= 0:
        raise InfeasibleHX("positive approach and installed UA required")
    if isinstance(segments,bool) or not isinstance(segments,int) or segments < 8:
        raise InfeasibleHX("segments must be an integer >= 8")
    minimum = math.inf
    integral = 0.0
    for i in range(segments+1):
        x = i/segments
        th = hot_temperature_K(x)
        tc = (cold_temperature_K(x) if cold_temperature_K is not None
              else cold_out_K - (cold_out_K-cold_in_K)*x)
        if not math.isfinite(th) or th <= 0 or not math.isfinite(tc) or tc <= 0:
            raise InfeasibleHX("invalid local HX temperature")
        dt = th-tc
        minimum = min(minimum,dt)
        if dt + 1e-9 < minimum_approach_K:
            raise InfeasibleHX(f"HX pinch: {dt:.4g} K < {minimum_approach_K:.4g} K")
        weight = 0.5 if i in (0,segments) else 1.0
        integral += weight/dt
    ua = duty_W * integral/segments
    if installed_UA_W_per_K + 1e-9 < ua:
        raise InfeasibleHX(f"UA insufficient: {installed_UA_W_per_K:.3g} < {ua:.3g} W/K")
    return HXCheck(duty_W,ua,minimum,installed_UA_W_per_K,segments)
