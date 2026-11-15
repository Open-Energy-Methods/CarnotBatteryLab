"""Implicit observed-velocity/predicted-temperature exhaust mass-flow boundary.

The 2022 source's exhaust-flow relation (Eq 1) is:
    m_dot = rho_exhaust(T_exhaust) * A_pipe * measured_velocity_exhaust.
A naive evaluation at *measured* T_out leaks the comparison target into
the forward simulation. This alternative solves for m_dot using the
MODEL-PREDICTED exhaust temperature, iterated with the bed state from the
same integration interval. A measured velocity remains an external input.

This is a numerical/structural improvement only, NOT independent hardware
validation: actual exhaust ID, pipe thermal delay, pressure, leakage and
the bed gas density assumption are still unqualified.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, pi
from ..physics.gas_rock_regenerator import GasRockBed,BedState,BedStep,advance_bed

AIR_GAS_CONSTANT_J_KGK=287.05


class ExhaustCouplingError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExhaustCouplingSettings:
    pipe_inner_diameter_m:float=.052  # unmeasured scenario, NOT a calibration
    exhaust_pressure_Pa:float=101325.0 # assumed near atmosphere
    relative_flow_tolerance:float=1e-6
    max_iterations:int=25
    damping:float=.65
    bdf_relative_tolerance:float=1e-7

    def __post_init__(self):
        if not all(isfinite(v) for v in (
            self.pipe_inner_diameter_m,self.exhaust_pressure_Pa,
            self.relative_flow_tolerance,self.damping,self.bdf_relative_tolerance)):
            raise ValueError("nonfinite exhaust flow boundary settings")
        if (self.pipe_inner_diameter_m<=0 or self.exhaust_pressure_Pa<=0 or
            not 0<self.relative_flow_tolerance<1e-2 or not 0<self.damping<=1 or
            not 0<self.bdf_relative_tolerance<=1e-3):
            raise ValueError("invalid exhaust coupling settings")
        if isinstance(self.max_iterations,bool) or self.max_iterations<2:
            raise ValueError("at least two fixed-point iterations required")


@dataclass(frozen=True)
class ExhaustCoupledStep:
    bed_step:BedStep
    mass_flow_kg_s:float
    iterations:int
    relative_flow_residual:float
    predicted_exhaust_temperature_K:float
    measured_velocity_m_s:float
    measured_outlet_temperature_used_as_input:bool=False


def ideal_gas_mass_flow(*,temperature_K:float,measured_velocity_m_s:float,
                        settings:ExhaustCouplingSettings)->float:
    if (not isfinite(temperature_K) or temperature_K<=0 or
        not isfinite(measured_velocity_m_s) or measured_velocity_m_s<0):
        raise ValueError("invalid exhaust density/velocity")
    area=pi*settings.pipe_inner_diameter_m**2/4
    return (settings.exhaust_pressure_Pa/(AIR_GAS_CONSTANT_J_KGK*temperature_K)*
            area*measured_velocity_m_s)


def step_from_velocity(
    bed:GasRockBed,state:BedState, *,
    inlet_temperature_K:float,measured_exhaust_velocity_m_s:float,
    dt_s:float,settings:ExhaustCouplingSettings=ExhaustCouplingSettings()
)->ExhaustCoupledStep:
    if not isfinite(inlet_temperature_K) or inlet_temperature_K<=0:
        raise ValueError("inlet temperature must be positive")
    # Source state at step start, NOT any measured Tout(t). For each
    # fixed-point trial, re-integrate the SAME state to avoid double charging.
    guess=ideal_gas_mass_flow(
        temperature_K=state.fluid_temperature_K[-1],
        measured_velocity_m_s=measured_exhaust_velocity_m_s,settings=settings)
    if guess==0:
        trial=advance_bed(bed,state,inlet_K=inlet_temperature_K,mass_flow_kg_s=0,
                          dt_s=dt_s,relative_tolerance=settings.bdf_relative_tolerance)
        return ExhaustCoupledStep(trial,0.,1,0.,
                                   trial.final_outlet_temperature_K,
                                   measured_exhaust_velocity_m_s)
    for iteration in range(1,settings.max_iterations+1):
        trial=advance_bed(
            bed,state,inlet_K=inlet_temperature_K,mass_flow_kg_s=guess,
            dt_s=dt_s,relative_tolerance=settings.bdf_relative_tolerance)
        newflow=ideal_gas_mass_flow(
            temperature_K=trial.final_outlet_temperature_K,
            measured_velocity_m_s=measured_exhaust_velocity_m_s,
            settings=settings)
        residual=abs(newflow-guess)/max(newflow,1e-10)
        if residual<=settings.relative_flow_tolerance:
            return ExhaustCoupledStep(trial,guess,iteration,residual,
                                      trial.final_outlet_temperature_K,
                                      measured_exhaust_velocity_m_s)
        guess=settings.damping*newflow+(1-settings.damping)*guess
    raise ExhaustCouplingError(
        f"model-outlet / exhaust-flow fixed point not converged after "
        f"{settings.max_iterations} attempts, residual={residual:.5g}")
