"""Source-aware, uncalibrated DYNAMIC observation model for contact thermocouples.

The 2022 Wolde et al. copper-slag rig documented seven sheathed Type-K probes,
50 mm apart along a nominal 400 mm horizontal bed, with both gas and rock
contact. 2024 absolute positions, contact conductances and dynamic response
are not independently measured.

A scenario fixes ONE common first-probe offset, ONE common gas-contact
fraction and ONE common first-order response time for all seven probes.
These are explicitly *hypotheses*, NEVER fit to measured downstream TCs.
The equilibrium bead temperature is the weighted gas/solid temperature at
the SAME fixed position (not independent sensor-specific extrema).

dTbead/dt = (w*Tgas(z,t)+(1-w)*Trock(z,t)-Tbead)/tau,
integrated exactly for piecewise-LINEAR equilibrium forcing at each interval.
This is a one-way sensor: it DOES NOT remove energy from the packed-bed model.
It is not a calibrated Type-K hardware/instrument response model.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, expm1, isfinite
from typing import Sequence

SOURCE_REF="Wolde et al. (2022), Methods 2.1, DOI 10.59627/rbens.2022v13i2.395"


@dataclass(frozen=True)
class ThermocoupleHypothesis:
    first_position_m:float
    gas_contact_fraction:float
    response_tau_s:float
    bed_length_m:float=.400
    spacing_m:float=.050
    sensors:int=7

    def __post_init__(self):
        for k in ("first_position_m","gas_contact_fraction","response_tau_s",
                  "bed_length_m","spacing_m"):
            if not isfinite(getattr(self,k)):
                raise ValueError(f"{k} must be finite")
        if self.sensors!=7 or self.spacing_m<=0 or self.bed_length_m<=0:
            raise ValueError("source layout must have seven equally spaced sensors")
        if not 0<=self.first_position_m<=self.bed_length_m-(self.sensors-1)*self.spacing_m+1e-12:
            raise ValueError("first-position hypothesis outside source-geometric envelope")
        if not 0<=self.gas_contact_fraction<=1:
            raise ValueError("gas-contact fraction must be between zero and one")
        if self.response_tau_s<0:
            raise ValueError("response time must be nonnegative")

    @property
    def positions_m(self)->tuple[float,...]:
        return tuple(self.first_position_m+i*self.spacing_m
                     for i in range(self.sensors))


def sample_cell_centres(temperature_K:Sequence[float],position_m:float,length_m:float)->float:
    """Linear interpolation on finite-volume cell centres, clamped at wall.

    This interpolation is an observation operator, NOT the finite-volume
    advection/conduction scheme. Only evaluation at fixed source-defined
    physical positions is meaningful for cross-grid convergence.
    """
    n=len(temperature_K)
    if n<2 or not isfinite(position_m) or not 0<=position_m<=length_m:
        raise ValueError("invalid field sample/axial coordinate")
    if not all(isfinite(v) and v>0 for v in temperature_K):
        raise ValueError("nonphysical temperature field")
    dz=length_m/n
    u=position_m/dz-.5
    if u<=0:
        return float(temperature_K[0])
    if u>=n-1:
        return float(temperature_K[-1])
    i=int(u)
    a=u-i
    return float(temperature_K[i]*(1-a)+temperature_K[i+1]*a)


def mixed_equilibrium_K(gas_K:Sequence[float],solid_K:Sequence[float],
                        hypothesis:ThermocoupleHypothesis)->tuple[float,...]:
    if len(gas_K)!=len(solid_K):
        raise ValueError("same spatial mesh required for gas and solid fields")
    w=hypothesis.gas_contact_fraction
    return tuple(
        w*sample_cell_centres(gas_K,z,hypothesis.bed_length_m)
        +(1-w)*sample_cell_centres(solid_K,z,hypothesis.bed_length_m)
        for z in hypothesis.positions_m
    )


def first_order_ramp_step(
    sensor_initial_K:float,equilibrium_initial_K:float,equilibrium_final_K:float,
    dt_s:float,tau_s:float
)->float:
    """EXACT update for equilibrium stimulus linear within the interval.

    Formula is analytically derived by integrating exponential response to
    a + (b-a)t/dt. Uses expm1 for cancellation-safe short time steps.
    """
    args=(sensor_initial_K,equilibrium_initial_K,equilibrium_final_K,dt_s,tau_s)
    if not all(isfinite(x) for x in args) or dt_s<=0 or tau_s<0:
        raise ValueError("invalid time/temperature for sensor response")
    if min(args[:3])<=0:
        raise ValueError("Kelvin temperatures must be positive")
    if tau_s==0:
        return float(equilibrium_final_K)
    x=dt_s/tau_s
    e=exp(-x)
    one_minus_e=-expm1(-x)
    ramp_weight=(x/2-x*x/6+x**3/24) if x<1e-3 else (1-one_minus_e/x)
    out=(e*sensor_initial_K+one_minus_e*equilibrium_initial_K+
         ramp_weight*(equilibrium_final_K-equilibrium_initial_K))
    return float(out)


def simulate_probe_history(
    times_s:Sequence[float],
    gas_history_K:Sequence[Sequence[float]],
    solid_history_K:Sequence[Sequence[float]],
    hypothesis:ThermocoupleHypothesis,
)->tuple[tuple[float,...],...]:
    """Returns seven source-geometry-consistent thermocouple histories in K.

    The initial bead state is model equilibrium, NOT an observed TC target.
    A frozen scenario applies to ALL seven probes at ALL times.
    """
    if len(times_s)!=len(gas_history_K) or len(times_s)!=len(solid_history_K) or len(times_s)<2:
        raise ValueError("times and gas/solid histories must align")
    if any(not isfinite(t) for t in times_s) or any(
        b<=a for a,b in zip(times_s,times_s[1:])):
        raise ValueError("strictly increasing time series required")
    last=mixed_equilibrium_K(gas_history_K[0],solid_history_K[0],hypothesis)
    histories=[[float(t)] for t in last]
    for j in range(1,len(times_s)):
        end=mixed_equilibrium_K(gas_history_K[j],solid_history_K[j],hypothesis)
        delta=times_s[j]-times_s[j-1]
        last=tuple(first_order_ramp_step(y,prev,new,delta,hypothesis.response_tau_s)
                   for y,prev,new in zip(last,
                       mixed_equilibrium_K(gas_history_K[j-1],solid_history_K[j-1],hypothesis),
                       end))
        for i,val in enumerate(last):
            histories[i].append(val)
    return tuple(tuple(h) for h in histories)


def preregistered_scenarios()->tuple[ThermocoupleHypothesis,...]:
    """Transparent deterministic hypotheses, NOT probability distributions.

    Bounds 0, 50, 100 mm reflect geometry; contact weights and response
    times are illustrative sensitivity values, NOT measured uncertainty.
    No observed T1-T7 data are used to pick these hypotheses.
    """
    return tuple(ThermocoupleHypothesis(x,w,tau)
                 for x in (0.,.05,.10)
                 for w in (.25,.5,.75)
                 for tau in (0.,30.,180.))


def uncalibrated_scenario_envelope(
    times_s:Sequence[float],
    gas_history_K:Sequence[Sequence[float]],
    solid_history_K:Sequence[Sequence[float]],
    scenarios:Sequence[ThermocoupleHypothesis]|None=None,
)->dict:
    """All scenario histories share one layout/contact/lag across sensors.

    Output min/max at a given sensor/time MAY come from different global
    scenarios. They are an exploratory scenario range, not a joint credible
    interval, measurement error bar or fitted predictions.
    """
    scenarios=tuple(scenarios) if scenarios is not None else preregistered_scenarios()
    if not scenarios:
        raise ValueError("must specify at least one independent scenario")
    runs=[simulate_probe_history(times_s,gas_history_K,solid_history_K,s)
          for s in scenarios]
    count=len(times_s)
    lo=tuple(tuple(min(run[i][t] for run in runs) for t in range(count))
             for i in range(7))
    hi=tuple(tuple(max(run[i][t] for run in runs) for t in range(count))
             for i in range(7))
    return {
        "status":"HYPOTHETICAL_COMMON_LAYOUT_SENSOR_RESPONSE_NOT_VALIDATED",
        "source":SOURCE_REF,
        "scenarios":tuple({
            "first_position_m":s.first_position_m,
            "gas_contact_fraction_UNMEASURED":s.gas_contact_fraction,
            "response_tau_s_UNMEASURED":s.response_tau_s,
            "shared_by_all_seven_probes":True,
        } for s in scenarios),
        "time_s":tuple(float(t) for t in times_s),
        "low_K":lo,
        "high_K":hi,
        "all_parameters_fixed_before_observation_comparison":True,
        "not_a_calibrated_uncertainty_or_joint_confidence_interval":True,
        "experimental_validation_pass":False,
    }
