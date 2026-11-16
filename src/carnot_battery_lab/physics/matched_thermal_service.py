"""M3.2: strictly fail-closed, numerical matched thermal-cycle screening.

Searches finite charge/discharge schedules for the SAME source-side R718
hypothesis and gas/rock bed. Each cycle begins with the actual prior-cycle
discharge state. The per-interval process gas must satisfy BOTH sampled
temperature grade and the specified heat duty. Consecutive full-field
terminal states must converge; inventory-only closure is insufficient.

This is an unqualified gas-thermal screen. It NEVER claims an equipment
operating envelope, a liquid/process heat exchanger, physical validation,
matched architecture ranking, or electricity/thermal round-trip efficiency.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from math import isfinite

from .coupled_charge import ChargeControl, simulate_charge
from .gas_rock_regenerator import GasRockBed, BedState, bed_energy_J
from .r718 import R718Inputs
from .sequential_hp_tes_service import (
    CandidateProcessGasService, handoff_coupled_charge_to_reverse_discharge,
)


@dataclass(frozen=True)
class MatchedThermalProtocol:
    charge_step_counts: tuple[int, ...] = (2, 4)
    discharge_step_counts: tuple[int, ...] = (2,)
    repeat_cycles: int = 3
    nominal_process_duty_W: float = 1_000_000.
    terminal_max_abs_difference_K: float = .25

    def __post_init__(self):
        for name in ("charge_step_counts", "discharge_step_counts"):
            values=getattr(self,name)
            if (not isinstance(values,tuple) or not values
                or any(isinstance(n,bool) or not isinstance(n,int) or n<1
                       for n in values)
                or len(set(values))!=len(values)):
                raise ValueError(f"{name} must be unique positive integer steps")
        if isinstance(self.repeat_cycles,bool) or not isinstance(
                self.repeat_cycles,int) or self.repeat_cycles<3:
            raise ValueError("at least 3 cycles required for consecutive closure")
        if (not isfinite(self.nominal_process_duty_W)
                or self.nominal_process_duty_W<=0
                or not isfinite(self.terminal_max_abs_difference_K)
                or self.terminal_max_abs_difference_K<=0):
            raise ValueError("positive finite duty and closure tolerance required")


def bed_state_dict(state:BedState)->dict:
    return {
        "fluid_temperature_K":list(state.fluid_temperature_K),
        "solid_temperature_K":list(state.solid_temperature_K),
    }


def max_terminal_field_difference_K(before:BedState,after:BedState)->float:
    if (len(before.fluid_temperature_K)!=len(after.fluid_temperature_K)
        or len(before.solid_temperature_K)!=len(after.solid_temperature_K)
        or not before.fluid_temperature_K or not before.solid_temperature_K):
        raise ValueError("incompatible bed fields for cyclic closure")
    pairs=zip((*before.fluid_temperature_K,*before.solid_temperature_K),
              (*after.fluid_temperature_K,*after.solid_temperature_K))
    if not all(isfinite(t) for field in (
            before.fluid_temperature_K,before.solid_temperature_K,
            after.fluid_temperature_K,after.solid_temperature_K) for t in field):
        raise ValueError("nonfinite temperature in cyclic closure")
    return max(abs(a-b) for a,b in pairs)


def sampled_interval_service_passes(
    rows:list[dict], *,
    required_interval_heat_J:float,
    expected_intervals:int
)->bool:
    """No partial-step credit and no extrapolation between temperature samples."""
    if (not isfinite(required_interval_heat_J) or required_interval_heat_J<=0
        or isinstance(expected_intervals,bool) or expected_intervals<1):
        raise ValueError("invalid process energy requirement")
    return (len(rows)==expected_intervals and all(
        row["sampled_temperature_grade_qualified"] is True
        and isfinite(row["qualified_process_heat_J"])
        and row["qualified_process_heat_J"] >=
            required_interval_heat_J*(1.-1e-8)
        for row in rows))


def screen_one_schedule(
    bed:GasRockBed, initial_state:BedState, hp_inputs:R718Inputs,
    charge_control:ChargeControl, process_service:CandidateProcessGasService,
    protocol:MatchedThermalProtocol
)->dict:
    """Repeat with non-reset bed fields, auditing service AND cyclic closure."""
    state=initial_state
    records=[]
    required_power=max(
        protocol.nominal_process_duty_W,
        process_service.reverse_mass_flow_kg_s*bed.gas_cp_J_kgK*
        (process_service.required_supply_K-process_service.process_return_K),
    )
    interval_heat_required=required_power*process_service.dt_s
    for i in range(protocol.repeat_cycles):
        before=state
        charge=simulate_charge(bed,before,hp_inputs,charge_control)
        if not charge.completed:
            records.append({
                "cycle":i+1,
                "status":"BLOCKED_INCOMPLETE_R718_CHARGE",
                "start_bed_state":bed_state_dict(before),
                "completed_charge_steps":len(charge.steps),
                "termination_reason":charge.termination_reason,
                "process_service_pass":False,
                "terminal_field_closure_pass":False,
            })
            break
        handoff=handoff_coupled_charge_to_reverse_discharge(
            bed,charge,process_service)
        if handoff["status"]=="BLOCKED_INCOMPLETE_COUPLED_CHARGE":
            raise RuntimeError("completed R718 charge unexpectedly blocked at handoff")
        end=handoff["final_bed_state"]
        state=BedState(tuple(end["fluid_temperature_K"]),
                       tuple(end["solid_temperature_K"]))
        deviation=max_terminal_field_difference_K(before,state)
        qualified=sampled_interval_service_passes(
            handoff["discharge_steps"],
            required_interval_heat_J=interval_heat_required,
            expected_intervals=process_service.requested_steps,
        )
        # Q_gas,charge is the ACTUAL heat transferred to storage, not merely
        # nominal condenser heat. The discharge gas heat remains SIGNED.
        # ΔU + Q_wall,charge + Q_wall,discharge
        #     + Q_into_process_gas - Q_into_bed_from_charge_gas = 0.
        cycle_residual=(bed_energy_J(bed,state)-bed_energy_J(bed,before)
            +charge.cumulative_wall_loss_J+handoff["discharge_wall_loss_J"]
            +handoff["signed_discharge_heat_into_process_gas_J"]
            -charge.cumulative_heat_into_bed_J)
        scale=max(1.,abs(charge.cumulative_heat_into_bed_J),
            abs(handoff["signed_discharge_heat_into_process_gas_J"]),
            abs(charge.cumulative_wall_loss_J),
            abs(handoff["discharge_wall_loss_J"]))
        if abs(cycle_residual)>1e-5*scale:
            raise RuntimeError("combined charge-discharge storage first-law failure")
        records.append({
            "cycle":i+1,
            "status":"NUMERICAL_CYCLE_COMPLETED",
            "start_bed_state":bed_state_dict(before),
            "post_charge_bed_state":bed_state_dict(charge.final_bed),
            "final_bed_state":bed_state_dict(state),
            "completed_charge_steps":len(charge.steps),
            "charge_electricity_J_partial_aux":charge.cumulative_electric_grid_J,
            "discharge_blower_electricity_J_uncalibrated":
                handoff["discharge_model_blower_electricity_J"],
            "actual_heat_into_bed_from_charge_gas_J":
                charge.cumulative_heat_into_bed_J,
            "signed_process_heat_J":
                handoff["signed_discharge_heat_into_process_gas_J"],
            "qualified_process_heat_J":
                handoff["qualified_process_heat_J"],
            "sampled_discharge_intervals":handoff["discharge_steps"],
            "process_service_pass":qualified,
            "max_terminal_field_difference_K":deviation,
            "terminal_field_closure_pass":
                deviation<=protocol.terminal_max_abs_difference_K,
            "storage_energy_closure_residual_J":cycle_residual,
        })
    completed=(len(records)==protocol.repeat_cycles and all(
        x["status"]=="NUMERICAL_CYCLE_COMPLETED" for x in records))
    # Two consecutive CLOSED cycles, not simply a small change in bulk energy
    # at the very end, are required to call thermal state repeatability.
    closed=bool(completed and all(
        row["terminal_field_closure_pass"] for row in records[-2:]))
    grade=bool(completed and all(
        row["process_service_pass"] for row in records[-2:]))
    matched=closed and grade
    if not completed:
        status="BLOCKED_CHARGE_INCOMPLETE_NO_CYCLIC_SERVICE"
    elif not grade and not closed:
        status="PROCESS_GRADE_OR_DUTY_UNMET_AND_STATE_NOT_CLOSED"
    elif not grade:
        status="PROCESS_GRADE_OR_DUTY_UNMET"
    elif not closed:
        status="CYCLIC_STATE_NOT_CLOSED"
    else:
        status="MODEL_ONLY_SAMPLED_GAS_THERMAL_MATCH_NO_HARDWARE_QUALIFICATION"
    return {
        "status":status,
        "charge_steps_per_cycle":charge_control.number_of_steps,
        "discharge_steps_per_cycle":process_service.requested_steps,
        "requested_process_gas_power_W":protocol.nominal_process_duty_W,
        "required_interval_gas_heat_J":interval_heat_required,
        "requested_gas_temperature_grade_K":[
            process_service.process_return_K,process_service.required_supply_K],
        "model_cycles_completed":completed,
        "consecutive_terminal_field_closure":closed,
        "consecutive_full_duty_and_sampled_grade":grade,
        "model_only_matched_gas_thermal_screen":matched,
        "cycles":records,
        "validated_compressor_and_source_envelope":False,
        "physical_industrial_process_HX_qualified":False,
        "experimental_validation":False,
        "qualified_architecture_comparison":False,
        "system_round_trip_efficiency":None,
        "continuous_between_samples_temperature_guarantee":False,
    }


def scan_matched_thermal_schedules(
    bed:GasRockBed, initial_state:BedState, hp_inputs:R718Inputs,
    base_charge_control:ChargeControl, process_service:CandidateProcessGasService,
    protocol:MatchedThermalProtocol=MatchedThermalProtocol()
)->dict:
    candidates={}
    for charge_steps,discharge_steps in product(
            protocol.charge_step_counts,protocol.discharge_step_counts):
        charge=replace(base_charge_control,number_of_steps=charge_steps)
        service=replace(process_service,requested_steps=discharge_steps)
        key=f"charge_{charge_steps}_discharge_{discharge_steps}"
        candidates[key]=screen_one_schedule(
            bed,initial_state,hp_inputs,charge,service,protocol)
    model_matches=[key for key,x in candidates.items()
                   if x["model_only_matched_gas_thermal_screen"]]
    return {
        "status":("MODEL_ONLY_MATCHED_GAS_SCHEDULES_FOUND_UNQUALIFIED"
                  if model_matches else "NO_MATCHED_GAS_SCHEDULE_ESTABLISHED"),
        "candidate_count":len(candidates),
        "model_only_matches":model_matches,
        "candidates":candidates,
        "hardware_qualified":False,
        "real_process_hx_qualified":False,
        "physical_validation":False,
        "matched_architecture_rank":None,
        "round_trip_efficiency":None,
        "scientific_limitations":[
            "R718 stage limits are numerical guards, not manufacturer compressor maps",
            "The source 80 to 70 Celsius envelope remains hardware unqualified",
            "Gas discharge is not the contracted industrial liquid-process HX",
            "Temperature qualification checks sampled initial/mean/final only",
            "Thermal terminal state is the full fluid+solid field, not bulk SOC",
            "Ergun-only blowers and simplified wall heat transfer lack calibration",
            "The finite schedule grid is not proof of global infeasibility",
        ],
    }
