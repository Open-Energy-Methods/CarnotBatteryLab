"""Case B only: mixed-phase Type-K observable compatibility diagnostics.

2024 public data DOI 10.17632/j37x6ptpk2.1, CC BY 4.0.
2022 experimental apparatus Wolde et al. Methods 2.1, page 166:
seven type-K sheaths contact BOTH gas and rock, spaced 50 mm, absolute
initial offset NOT sourced. No arbitrary assignment of T1..T7 to gas.

All gas/rock states evolve from the *initial* 7 measured thermocouples
and subsequent measured Tin(t)/exhaust velocity(t). Subsequent measured
T1..T7 and Tout are NEVER used to adjust physics or mass flow.

The envelope unions all possible axial offsets and instantaneous gas/rock
phase values, with NO time-response adjustment. This is deliberately
permissive and NOT a calibrated sensor-measurement uncertainty interval:
an observation outside the envelope signals a modelling/metadata/sensor
investigation, not an independent model validation failure.

No run A/C/D is simulated, fitted or used for selection here.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from statistics import mean
from math import sqrt

from analyze_horizontal_bed_observations import load_case
from exploratory_forward_horizontal_bed import (
    _initial_state, PUBLISHED_BED_LENGTH_M,PUBLISHED_BED_DIAMETER_M,
    PUBLISHED_PARTICLE_DIAMETER_M_APPROX,PUBLISHED_ESTIMATED_POROSITY,
    ASSUMED_BED_GAS_DENSITY_KG_M3,ASSUMED_GAS_VISCOSITY_PA_S,
    ASSUMED_GAS_CONDUCTIVITY_W_MK,ASSUMED_ROCK_RHO_KG_M3,
    ASSUMED_ROCK_CP_J_KGK,ASSUMED_WALL_UA_W_K)
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.validation.exhaust_flow_coupling import (
    ExhaustCouplingSettings,step_from_velocity)
from carnot_battery_lab.validation.sensor_phase_envelopes import (
    SensorLayoutEvidence,sensor_phase_position_envelope,
    diagnostic_summary)

SOURCE_DOI="10.17632/j37x6ptpk2.1"
RAW_B_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"


def study(data_dir:Path,*,cells:int=128)->dict:
    if isinstance(cells,bool) or not isinstance(cells,int) or cells<8:
        raise ValueError("cells must be >=8")
    source=load_case(data_dir,"B")
    if source["sha256"]!=RAW_B_SHA:
        raise ValueError("unexpected measured source version")
    records=source["rows"]
    bed=GasRockBed(
        geometry=PackedBedGeometry(
            PUBLISHED_BED_LENGTH_M,PUBLISHED_BED_DIAMETER_M,
            PUBLISHED_PARTICLE_DIAMETER_M_APPROX,PUBLISHED_ESTIMATED_POROSITY),
        cells=cells,gas_density_kg_m3=ASSUMED_BED_GAS_DENSITY_KG_M3,
        gas_cp_J_kgK=1005.,gas_viscosity_Pa_s=ASSUMED_GAS_VISCOSITY_PA_S,
        gas_conductivity_W_mK=ASSUMED_GAS_CONDUCTIVITY_W_MK,
        rock_density_kg_m3=ASSUMED_ROCK_RHO_KG_M3,
        rock_cp_J_kgK=ASSUMED_ROCK_CP_J_KGK,
        wall_UA_W_K=ASSUMED_WALL_UA_W_K,
        ambient_K=records[0][r"$T_{0}$"]+273.15,
    )
    layout=SensorLayoutEvidence()
    settings=ExhaustCouplingSettings()
    state=_initial_state(bed,records[0])
    predictions={f"T{i}":[] for i in range(1,8)}
    summaries={f"T{i}":[] for i in range(1,8)}
    times=[]
    outlet_errors=[]
    solver_flow_residuals=[]
    max_energy_residual=0.
    for prev,row in zip(records,records[1:]):
        dt=row["Time exp."]-prev["Time exp."]
        result=step_from_velocity(
            bed,state,inlet_temperature_K=row[r"$T_{in}$"]+273.15,
            measured_exhaust_velocity_m_s=row["Velocity"],dt_s=dt,
            settings=settings)
        assert result.measured_outlet_temperature_used_as_input is False
        state=result.bed_step.final_state
        times.append(row["Time exp."])
        gas=[x-273.15 for x in state.fluid_temperature_K]
        solid=[x-273.15 for x in state.solid_temperature_K]
        solver_flow_residuals.append(result.relative_flow_residual)
        max_energy_residual=max(max_energy_residual,abs(result.bed_step.energy_residual_J))
        outlet_errors.append(result.predicted_exhaust_temperature_K-273.15-
                             row[r"$T_{out}$"])
        # Observed TC targets are retrieved *after* the integration step.
        for i in range(1,8):
            key=f"T{i}"
            envelope=sensor_phase_position_envelope(gas,solid,i-1,layout)
            observed=row[f"$T_{i}$"]
            summaries[key].append((observed,envelope))
            predictions[key].append({
                "time_s":row["Time exp."],
                "source_measured_TC_C":observed,
                "model_lower_extrema_C":envelope.lower_model_temperature_C,
                "model_upper_extrema_C":envelope.upper_model_temperature_C,
                "allowed_axial_range_m":list(envelope.axial_possible_m),
            })
    outputs={key:diagnostic_summary(summaries[key]) for key in summaries}
    return {
        "status":"CASE_B_UNQUALIFIED_MIXED_PHASE_TC_ENVELOPES_NO_VALIDATION",
        "source_doi":SOURCE_DOI,
        "original_csv_sha256":RAW_B_SHA,
        "cells":cells,
        "first_observation_initialises_model_not_scored":True,
        "subsequent_TC_targets_used_as_physics_input":False,
        "measured_Tout_used_as_mass_flow_input":False,
        "verified_2022_TC_source":"Wolde et al. 2022 Methods §2.1 p.166, type-K sheath contacts solid and air, 50mm spacing",
        "verified_2024_same_TC_hardware_revision":False,
        "observation_operator_absolute_offset_m":None,
        "initial_state_reconstruction_assumed_first_sensor_offset_m":0.05,
        "initialisation_note":"First sample T1-T7 interpolated assuming positions 0.05..0.35m; model state not independent at t0",
        "assumed_pipe_inner_diameter_m":settings.pipe_inner_diameter_m,
        "sensor_layout_hypothesis":asdict(layout),
        "numerical_resolution_status":"NOT_ASSESSED_FOR_SENSOR_OBSERVATION_OPERATOR",
        "flow_fixed_point_max_relative_residual":max(solver_flow_residuals),
        "max_absolute_step_energy_residual_J":max_energy_residual,
        "original_case_B_outlet_RMSE_C_NOT_VALIDATION":
            sqrt(mean(x*x for x in outlet_errors)),
        "sensor_outside_extrema_diagnostics":outputs,
        "sensor_time_series":predictions,
        "not_a_calibrated_sensor_uncertainty_interval":True,
        "held_out_from_model_selection":["C","D"],
        "previously_inspected_not_blind":"A",
        "model_validation_pass":False,
        "blockers":[
            "2022-to-2024 TC layout/hardware continuity unverified",
            "absolute position of first TC and radial coordinate unknown",
            "sheath physically contacts rock and gas; thermal mixing/time response unknown",
            "phase-and-position extrema may be broad and do NOT guarantee realizable common offset",
            "source flow probe bore/velocity traverse, pressure/taps, slag properties not calibrated",
            "no holdout, 2-D buoyancy or complete measurement uncertainty",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    p.add_argument("--cells",type=int,default=128)
    p.add_argument("--output",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_TC_phase_position_diagnostic.json"))
    args=p.parse_args()
    data=study(args.input_dir,cells=args.cells)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("SENSOR_COMPATIBILITY_STATUS",data["status"])
    for k,v in data["sensor_outside_extrema_diagnostics"].items():
        print("SENSOR_BOUND",k,
              f"outside_fraction={v['outside_model_extrema_fraction']:.3f}",
              f"outside_mean_C={v['mean_outside_distance_C']:.3f}",
              f"max_outside_C={v['maximum_outside_distance_C']:.3f}")
    print("PHYSICAL_MODEL_VALIDATION",data["model_validation_pass"])


if __name__=="__main__":
    main()
