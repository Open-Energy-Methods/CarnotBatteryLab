"""SEQUENTIAL R718 heat-pump -> packed-bed charge -> reverse discharge screen.

Reuses the already implemented, TES-state-responsive R718 condenser/bed
charge and the independent M3 reverse-flow thermal bed discharge. Charge
is an actual transient feedback model; after it ends, storage is released
to a candidate gas process. No simultaneous HP/process operating coupling,
no vendor compressor envelope, no measured bed pressure validation and
no system round-trip efficiency claim.

The original 80C-source R718 5:1-stage design remains HARDWARE UNQUALIFIED.
A numerically feasible cycle is NOT an independently supported compressor.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .coupled_charge import ChargeRun
from .gas_rock_regenerator import GasRockBed,BedState,bed_energy_J
from .reverse_flow_discharge import advance_reverse_discharge


@dataclass(frozen=True)
class CandidateProcessGasService:
    process_return_K:float=353.15
    required_supply_K:float=383.15
    reverse_mass_flow_kg_s:float=25.
    dt_s:float=120.
    requested_steps:int=4
    reference_ambient_K:float=293.15

    def __post_init__(self):
        vals=(self.process_return_K,self.required_supply_K,
              self.reverse_mass_flow_kg_s,self.dt_s,self.reference_ambient_K)
        if not all(isfinite(x) and x>0 for x in vals) or (
            self.required_supply_K<=self.process_return_K or
            isinstance(self.requested_steps,bool) or
            not isinstance(self.requested_steps,int) or
            self.requested_steps<1):
            raise ValueError("invalid candidate process-gas thermal service")


def handoff_coupled_charge_to_reverse_discharge(
    bed:GasRockBed,
    charge:ChargeRun,
    contract:CandidateProcessGasService=CandidateProcessGasService()
)->dict:
    if not charge.completed or not charge.steps:
        return {
            "status":"BLOCKED_INCOMPLETE_COUPLED_CHARGE",
            "termination_reason":charge.termination_reason or "charge returned no steps",
            "discharge_steps":[],
            "qualified_process_heat_J":0.,
            "experimental_hardware_validation":False,
            "round_trip_efficiency":None,
        }
    if len(charge.final_bed.fluid_temperature_K)!=bed.cells:
        raise ValueError("charge final grid does not match discharge bed model")
    state=charge.final_bed
    charge_terminal_energy=bed_energy_J(bed,state)
    run=[]
    delivered=0.
    recovered_signed=0.
    loss=0.
    fan=0.
    process_exergy=0.
    peak_outlet=0.
    for n in range(contract.requested_steps):
        step=advance_reverse_discharge(
            bed,state,return_gas_K=contract.process_return_K,
            mass_flow_kg_s=contract.reverse_mass_flow_kg_s,
            dt_s=contract.dt_s,
            minimum_process_delivery_K=contract.required_supply_K,
            dead_state_K=contract.reference_ambient_K)
        state=step.final_state
        delivered+=step.qualified_process_heat_J
        recovered_signed+=step.signed_heat_to_process_gas_J
        loss+=step.ambient_loss_J
        fan+=step.fan_electric_J_model
        process_exergy+=step.useful_heat_exergy_J
        peak_outlet=max(peak_outlet,step.time_mean_outlet_K)
        run.append({
            "interval":n+1,
            "first_process_gas_out_K":step.first_outlet_K,
            "mean_process_gas_out_K":step.time_mean_outlet_K,
            "end_process_gas_out_K":step.final_outlet_K,
            "sampled_temperature_grade_qualified":step.screen_passed_temperature_samples,
            "signed_process_gas_heat_J":step.signed_heat_to_process_gas_J,
            "qualified_process_heat_J":step.qualified_process_heat_J,
            "predicted_Ergun_pressure_drop_Pa_not_calibrated":
                step.model_pressure_drop_Pa_not_calibrated,
            "step_first_law_residual_J":step.bed_first_law_residual_J,
        })
    terminal_energy=bed_energy_J(bed,state)
    residual=(terminal_energy-charge_terminal_energy+
              recovered_signed+loss)
    if abs(residual)>1e-5*max(1.,abs(recovered_signed),
                              abs(terminal_energy-charge_terminal_energy)):
        raise RuntimeError("R718 charge handoff to reverse discharge failed first law")
    charge_to_bed=charge.cumulative_heat_into_bed_J
    from_hp=charge.cumulative_hp_heat_J
    charge_loop_mismatch=from_hp-charge_to_bed
    return {
        "status":("PROVISIONAL_GAS_GRADE_PASSED_SAMPLED_STEPS"
                  if delivered>0 else "PROCESS_GRADE_UNMET_AT_REQUESTED_TEMPERATURE"),
        "service_request":{
            "return_K":contract.process_return_K,
            "required_supply_K":contract.required_supply_K,
            "mass_flow_kg_s":contract.reverse_mass_flow_kg_s,
            "interval_duration_s":contract.dt_s,
            "intervals":contract.requested_steps,
        },
        "charging_HP_was_TES_state_responsive":True,
        "charge_compressor_hardware_qualified":False,
        "charge_source_hardware_operating_envelope_qualified":False,
        "charge_completed_steps":len(charge.steps),
        "charge_end_bed_energy_J":charge_terminal_energy,
        "heat_pump_output_to_gas_J":from_hp,
        "actual_gas_heat_into_storage_J":charge_to_bed,
        "charge_fixed_point_heat_split_residual_J":charge_loop_mismatch,
        "charge_grid_electricity_J_including_partial_aux":charge.cumulative_electric_grid_J,
        "signed_discharge_heat_into_process_gas_J":recovered_signed,
        "qualified_process_heat_J":delivered,
        "discharge_process_gas_exergy_gain_J":process_exergy,
        "discharge_wall_loss_J":loss,
        "discharge_model_blower_electricity_J":fan,
        "total_partial_grid_electricity_J":
            charge.cumulative_electric_grid_J+fan,
        # Expose the ACTUAL terminal field for a non-reset repeated-cycle audit.
        # Keep it JSON-compatible for the source-controlled evidence artifact.
        "final_bed_state":{
            "fluid_temperature_K":list(state.fluid_temperature_K),
            "solid_temperature_K":list(state.solid_temperature_K),
        },
        "all_discharge_intervals_sampled_grade_qualified":all(
            row["sampled_temperature_grade_qualified"] for row in run),
        "final_bed_energy_J":terminal_energy,
        "discharge_energy_residual_J":residual,
        "peak_mean_process_gas_out_K":peak_outlet,
        "discharge_steps":run,
        "first_law_charge_vs_discharge_data_consistent":True,
        "temperature_gate_is_sampled_not_full_transient":True,
        "total_qualified_thermodynamic_process_service":False,
        "full_cyclic_terminal_state_established":False,
        "matched_service_architecture_comparison_qualified":False,
        "experimental_hardware_validation":False,
        "round_trip_efficiency":None,
        "note":"Standalone process GAS discharge after HP charging; not a verified process-liquid HX or industrial duty",
    }
