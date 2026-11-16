"""Reverse-flow packed-bed discharge and cyclic thermal-service audit (M3).

This module reuses the EXACT previously tested conservative gas/rock finite
volume solver by reversing the symmetric physical bed state before/after
a discharge step. Charging always flows from physical x=0 to x=L;
discharge cold gas enters physical x=L and useful hot gas exits at x=0.

The original model has uniform geometry and constant gas/solid properties.
A real bidirectional piping system, valves, partial pressure, hot spot
reversal, axial direction-dependent dispersion or reservoir may invalidate
this simplification. The pressure loss is an UNCALIBRATED Ergun prediction.

This is thermal TES useful-heat delivery, NOT electricity-to-electricity
round-trip, validated R718/HTHP integration or certified process service.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite,log
from typing import Sequence

from .gas_rock_regenerator import (
    GasRockBed,BedState,BedStep,advance_bed,bed_energy_J,
)


def reverse_bed_state(state:BedState)->BedState:
    return BedState(tuple(float(x) for x in reversed(state.fluid_temperature_K)),
                    tuple(float(x) for x in reversed(state.solid_temperature_K)))


def thermal_exergy_change_J(
    *,mass_flow_kg_s:float,cp_J_kgK:float,dt_s:float,
    source_inlet_K:float,source_outlet_mean_K:float,
    dead_state_K:float
)->float:
    """Signed specific-flow exergy gain across a sensible-gas service stage.

    Δb = cp[(Tout-Tin) - T0 ln(Tout/Tin)]. Physical fluid/exhaust state,
    fixed cp and common dead-state temperature; pressure exergy excluded.
    """
    vals=(mass_flow_kg_s,cp_J_kgK,dt_s,source_inlet_K,
          source_outlet_mean_K,dead_state_K)
    if not all(isfinite(v) for v in vals) or min(vals)<=0:
        raise ValueError("positive finite flow/exergy conditions required")
    return mass_flow_kg_s*cp_J_kgK*dt_s*(
        source_outlet_mean_K-source_inlet_K-
        dead_state_K*log(source_outlet_mean_K/source_inlet_K))


@dataclass(frozen=True)
class DischargeResult:
    final_state:BedState
    inlet_K:float
    first_outlet_K:float
    time_mean_outlet_K:float
    final_outlet_K:float
    bed_energy_change_J:float
    signed_heat_to_process_gas_J:float
    qualified_process_heat_J:float
    rejected_grade_heat_J:float
    ambient_loss_J:float
    fan_electric_J_model:float
    useful_heat_exergy_J:float
    bed_first_law_residual_J:float
    model_pressure_drop_Pa_not_calibrated:float
    qualifying_temperature_K:float
    screen_passed_temperature_samples:bool
    status:str="SYNTHETIC_M3_DISCHARGE_NOT_EXPERIMENTALLY_VALIDATED"


def advance_reverse_discharge(
    bed:GasRockBed,state:BedState, *,
    return_gas_K:float,mass_flow_kg_s:float,dt_s:float,
    minimum_process_delivery_K:float,dead_state_K:float=293.15,
    rtol:float=1e-7
)->DischargeResult:
    vals=(return_gas_K,mass_flow_kg_s,dt_s,minimum_process_delivery_K,dead_state_K)
    if not all(isfinite(v) and v>0 for v in vals):
        raise ValueError("discharge requires strictly positive finite conditions")
    if minimum_process_delivery_K<=return_gas_K:
        raise ValueError("process delivery threshold must exceed process return")
    # Reversing gas AND rock arrays implements physical opposite-direction
    # flow on a uniform symmetric bed without altering any energy capacity.
    if abs(bed_energy_J(bed,reverse_bed_state(state))-bed_energy_J(bed,state))>1e-6:
        raise RuntimeError("symmetric-reverse inventory conservation failed")
    flipped=reverse_bed_state(state)
    step=advance_bed(bed,flipped,inlet_K=return_gas_K,
                     mass_flow_kg_s=mass_flow_kg_s,dt_s=dt_s,
                     relative_tolerance=rtol)
    final=reverse_bed_state(step.final_state)
    # Positive when the process stream *gains* heat from hot packed bed.
    delivered=-step.heat_from_hot_gas_J
    sampled_qualified=all(t>=minimum_process_delivery_K for t in (
        step.first_temperature_K,
        step.mean_outlet_temperature_K,
        step.final_outlet_temperature_K,
    ))
    qualified=max(0.,delivered) if sampled_qualified else 0.
    # An unqualified positive heat pickup remains an enthalpy gain of
    # the stream but cannot count as useful specified high-grade service.
    grade_rejected=max(0.,delivered)-qualified
    exergy=thermal_exergy_change_J(
        mass_flow_kg_s=mass_flow_kg_s,cp_J_kgK=bed.gas_cp_J_kgK,
        dt_s=dt_s,source_inlet_K=return_gas_K,
        source_outlet_mean_K=step.mean_outlet_temperature_K,
        dead_state_K=dead_state_K)
    change=float(bed_energy_J(bed,final)-bed_energy_J(bed,state))
    residual=float(change+delivered+step.heat_loss_to_ambient_J)
    if abs(residual)>1e-5*max(1.,abs(delivered),abs(change)):
        raise RuntimeError("reverse-flow discharge energy conservation failure")
    return DischargeResult(
        final,return_gas_K,step.first_temperature_K,
        step.mean_outlet_temperature_K,step.final_outlet_temperature_K,
        change,delivered,qualified,grade_rejected,
        step.heat_loss_to_ambient_J,step.blower_electric_W*dt_s,
        exergy,residual,step.pressure_drop_Pa,
        minimum_process_delivery_K,sampled_qualified,
    )


def thermal_soc(
    bed:GasRockBed,state:BedState, *,
    empty_temperature_K:float,full_temperature_K:float
)->float:
    """Unclipped inventory SOC; reference temperatures are *assumed* states."""
    if not all(isfinite(x) and x>0 for x in (
        empty_temperature_K,full_temperature_K)) or (
        full_temperature_K<=empty_temperature_K):
        raise ValueError("invalid SOC reference temperatures")
    empty=BedState((empty_temperature_K,)*bed.cells,
                   (empty_temperature_K,)*bed.cells)
    full=BedState((full_temperature_K,)*bed.cells,
                  (full_temperature_K,)*bed.cells)
    denominator=bed_energy_J(bed,full)-bed_energy_J(bed,empty)
    if denominator<=0:
        raise ValueError("negative/zero reference capacity")
    # A value outside [0,1] is a physically important signal; do not clip.
    return float((bed_energy_J(bed,state)-bed_energy_J(bed,empty))/denominator)


@dataclass(frozen=True)
class CycleConditions:
    charge_inlet_K:float=430.
    discharge_return_K:float=303.15
    minimum_process_delivery_K:float=350.
    mass_flow_kg_s:float=.010
    dt_s:float=30.
    charge_steps:int=40
    discharge_steps:int=40
    empty_soc_K:float=303.15
    full_soc_K:float=430.
    dead_state_K:float=303.15

    def __post_init__(self):
        vals=(self.charge_inlet_K,self.discharge_return_K,
              self.minimum_process_delivery_K,self.mass_flow_kg_s,
              self.dt_s,self.empty_soc_K,self.full_soc_K,self.dead_state_K)
        if not all(isfinite(x) and x>0 for x in vals) or (
            self.charge_inlet_K<=self.discharge_return_K or
            not self.discharge_return_K<self.minimum_process_delivery_K<self.charge_inlet_K or
            self.full_soc_K<=self.empty_soc_K or
            not isinstance(self.charge_steps,int) or
            not isinstance(self.discharge_steps,int) or
            isinstance(self.charge_steps,bool) or
            isinstance(self.discharge_steps,bool) or
            min(self.charge_steps,self.discharge_steps)<1):
            raise ValueError("invalid synthetic charge/discharge protocol")


def simulate_charge_discharge_cycle(
    bed:GasRockBed,state:BedState,
    c:CycleConditions=CycleConditions()
)->dict:
    """Single cycle ledger, not a cyclic steady-state efficiency estimate."""
    start_energy=float(bed_energy_J(bed,state))
    charge_input_J=0.
    charge_loss_J=0.
    discharge_loss_J=0.
    fan_J=0.
    heat_to_gas_J=0.
    useful_J=0.
    lowgrade_J=0.
    delivered_exergy_J=0.
    high_grade_steps=0
    max_abs_residual_J=0.
    for _ in range(c.charge_steps):
        r=advance_bed(bed,state,inlet_K=c.charge_inlet_K,
                      mass_flow_kg_s=c.mass_flow_kg_s,dt_s=c.dt_s)
        state=r.final_state
        charge_input_J+=r.heat_from_hot_gas_J
        charge_loss_J+=r.heat_loss_to_ambient_J
        fan_J+=r.blower_electric_W*c.dt_s
        max_abs_residual_J=max(max_abs_residual_J,abs(r.energy_residual_J))
    after_charge_energy=float(bed_energy_J(bed,state))
    after_charge_soc=thermal_soc(bed,state,empty_temperature_K=c.empty_soc_K,
                                 full_temperature_K=c.full_soc_K)
    discharge_trace=[]
    for k in range(c.discharge_steps):
        r=advance_reverse_discharge(
            bed,state,return_gas_K=c.discharge_return_K,
            mass_flow_kg_s=c.mass_flow_kg_s,dt_s=c.dt_s,
            minimum_process_delivery_K=c.minimum_process_delivery_K,
            dead_state_K=c.dead_state_K)
        state=r.final_state
        heat_to_gas_J+=r.signed_heat_to_process_gas_J
        useful_J+=r.qualified_process_heat_J
        lowgrade_J+=r.rejected_grade_heat_J
        discharge_loss_J+=r.ambient_loss_J
        fan_J+=r.fan_electric_J_model
        delivered_exergy_J+=r.useful_heat_exergy_J
        max_abs_residual_J=max(max_abs_residual_J,abs(r.bed_first_law_residual_J))
        high_grade_steps+=int(r.screen_passed_temperature_samples)
        discharge_trace.append({
            "index":k+1,"mean_process_outlet_K":r.time_mean_outlet_K,
            "end_process_outlet_K":r.final_outlet_K,
            "high_grade_qualified":r.screen_passed_temperature_samples,
            "qualified_process_heat_J":r.qualified_process_heat_J,
            "model_pressure_loss_Pa_unvalidated":r.model_pressure_drop_Pa_not_calibrated,
        })
    final_energy=float(bed_energy_J(bed,state))
    cycle_residual=float(final_energy-start_energy-charge_input_J+heat_to_gas_J+
                    charge_loss_J+discharge_loss_J)
    if abs(cycle_residual)>1e-5*max(1.,abs(charge_input_J),abs(heat_to_gas_J)):
        raise RuntimeError("cycle-integrated first law failed")
    return {
        "final_state":state,
        "charge_gas_thermal_input_J":charge_input_J,
        "discharge_signed_heat_to_process_gas_J":heat_to_gas_J,
        "qualified_process_heat_J":useful_J,
        "unqualified_positive_process_gas_heat_J":lowgrade_J,
        "discharge_process_exergy_gain_J":delivered_exergy_J,
        "wall_ambient_loss_J":charge_loss_J+discharge_loss_J,
        "model_Ergun_blower_electric_J_not_calibrated":fan_J,
        "stored_energy_initial_J":start_energy,
        "stored_energy_after_charge_J":after_charge_energy,
        "stored_energy_final_J":final_energy,
        "soc_after_charge_unclipped":after_charge_soc,
        "soc_final_unclipped":thermal_soc(bed,state,
            empty_temperature_K=c.empty_soc_K,full_temperature_K=c.full_soc_K),
        "first_law_cycle_residual_J":cycle_residual,
        "max_step_energy_residual_J":max_abs_residual_J,
        "qualified_sampled_discharge_intervals":high_grade_steps,
        "total_discharge_intervals":c.discharge_steps,
        "discharge_trace":discharge_trace,
        "sampled_temperature_gate_only_no_continuous_guarantee":True,
        "thermal_round_trip_efficiency_claim":None,
        "electricity_round_trip_efficiency_claim":None,
        "physical_experiment_validation_pass":False,
    }


def simulate_repeated_cycles(
    bed:GasRockBed, initial_state:BedState,
    conditions:CycleConditions=CycleConditions(), *,
    cycles:int=3,cyclic_state_max_abs_K_threshold:float=.25
)->dict:
    if isinstance(cycles,bool) or cycles<1 or not isfinite(
        cyclic_state_max_abs_K_threshold) or cyclic_state_max_abs_K_threshold<=0:
        raise ValueError("invalid cycle count or convergence threshold")
    records=[]
    state=initial_state
    for i in range(cycles):
        before=state
        r=simulate_charge_discharge_cycle(bed,state,conditions)
        state=r["final_state"]
        deviation=float(max(max(abs(a-b) for a,b in zip(
            before.fluid_temperature_K,state.fluid_temperature_K)),
            max(abs(a-b) for a,b in zip(
            before.solid_temperature_K,state.solid_temperature_K))))
        item={k:v for k,v in r.items() if k!="final_state"}
        item["cycle_number"]=i+1
        item["max_start_end_temperature_difference_K"]=deviation
        item["cyclic_state_within_assumed_screen"]=bool(deviation<=cyclic_state_max_abs_K_threshold)
        records.append(item)
    # Even converged thermal state does not establish physically validated
    # roundtrip: charging heat source, process gas equipment and fan balance
    # are synthetic and HP compressor work is not included.
    return {
        "cycles":records,
        "final_state":state,
        "nominal_cyclic_state_screen_pass":records[-1]["cyclic_state_within_assumed_screen"],
        "cyclic_screen_is_NOT_experimental_validation":True,
        "system_round_trip_efficiency":None,
        "service_matching_established":False,
        "charge_source_and_process_gas_were_synthetic":True,
        "discharge_flow_direction":"physical x=L to x=0 (reversed)",
    }
