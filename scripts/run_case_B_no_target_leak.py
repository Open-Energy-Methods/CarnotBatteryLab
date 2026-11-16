"""Case B-only forward benchmark with NO measured outlet-temperature forcing.

Original 2024 CC BY dataset DOI 10.17632/j37x6ptpk2.1.
Observed T_out is used ONLY after the model finishes for evaluation; it
never enters mass flow or intermediate bed-state integration.

Pipe inner diameter remains an unmeasured assumption and the exit gas
temperature is used as a proxy for the exhaust-pipe anemometer location.
This is a methodology advance, not physical model validation.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from math import sqrt
from pathlib import Path
from statistics import mean

from analyze_horizontal_bed_observations import load_case
from exploratory_forward_horizontal_bed import (
    _initial_state,_first_rising_crossing_s,
    PUBLISHED_BED_LENGTH_M,PUBLISHED_BED_DIAMETER_M,
    PUBLISHED_PARTICLE_DIAMETER_M_APPROX,PUBLISHED_ESTIMATED_POROSITY,
    ASSUMED_BED_GAS_DENSITY_KG_M3,ASSUMED_GAS_VISCOSITY_PA_S,
    ASSUMED_GAS_CONDUCTIVITY_W_MK,ASSUMED_ROCK_RHO_KG_M3,
    ASSUMED_ROCK_CP_J_KGK,ASSUMED_WALL_UA_W_K)
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.validation.dynamic_thermocouples import sample_cell_centres
from carnot_battery_lab.validation.exhaust_flow_coupling import (
    ExhaustCouplingSettings,step_from_velocity)


def evaluate_case_B(data_dir:Path,*,pipe_inner_diameter_m:float=.052,
                    cells:int=16)->dict:
    source=load_case(data_dir,"B")  # NEVER load A/C/D in this method
    records=source["rows"]
    geom=PackedBedGeometry(PUBLISHED_BED_LENGTH_M,PUBLISHED_BED_DIAMETER_M,
                           PUBLISHED_PARTICLE_DIAMETER_M_APPROX,
                           PUBLISHED_ESTIMATED_POROSITY)
    bed=GasRockBed(
        geometry=geom,cells=cells,gas_density_kg_m3=ASSUMED_BED_GAS_DENSITY_KG_M3,
        gas_cp_J_kgK=1005,
        gas_viscosity_Pa_s=ASSUMED_GAS_VISCOSITY_PA_S,
        gas_conductivity_W_mK=ASSUMED_GAS_CONDUCTIVITY_W_MK,
        rock_density_kg_m3=ASSUMED_ROCK_RHO_KG_M3,
        rock_cp_J_kgK=ASSUMED_ROCK_CP_J_KGK,
        wall_UA_W_K=ASSUMED_WALL_UA_W_K,
        ambient_K=records[0][r"$T_{0}$"]+273.15,
    )
    settings=ExhaustCouplingSettings(pipe_inner_diameter_m=pipe_inner_diameter_m)
    state=_initial_state(bed,records[0])
    times=[records[0]["Time exp."]]
    predictions=[state.fluid_temperature_K[-1]-273.15]
    # Nominal FIXED physical probe coordinates, NOT verified 2024 sensor
    # positions; identical for all grids and phases. No post-t0 measured
    # thermocouple is used to choose physical positions.
    evaluation_positions_m=tuple(.05*i for i in range(1,8))
    internal_gas_K={f"x{int(i*5):02d}cm":[sample_cell_centres(
        state.fluid_temperature_K,z,geom.length_m)] for i,z in enumerate(
            evaluation_positions_m,start=1)}
    internal_rock_K={f"x{int(i*5):02d}cm":[sample_cell_centres(
        state.solid_temperature_K,z,geom.length_m)] for i,z in enumerate(
            evaluation_positions_m,start=1)}
    flows=[]
    iterations=[]
    flow_residuals=[]
    energy_residuals=[]
    for prev,row in zip(records,records[1:]):
        dt=row["Time exp."]-prev["Time exp."]
        result=step_from_velocity(
            bed,state,inlet_temperature_K=row[r"$T_{in}$"]+273.15,
            measured_exhaust_velocity_m_s=row["Velocity"],dt_s=dt,
            settings=settings)
        assert result.measured_outlet_temperature_used_as_input is False
        state=result.bed_step.final_state
        times.append(row["Time exp."])
        predictions.append(result.predicted_exhaust_temperature_K-273.15)
        for i,z in enumerate(evaluation_positions_m,start=1):
            key=f"x{i*5:02d}cm"
            internal_gas_K[key].append(sample_cell_centres(
                state.fluid_temperature_K,z,geom.length_m))
            internal_rock_K[key].append(sample_cell_centres(
                state.solid_temperature_K,z,geom.length_m))
        flows.append(result.mass_flow_kg_s)
        iterations.append(result.iterations)
        flow_residuals.append(result.relative_flow_residual)
        energy_residuals.append(result.bed_step.energy_residual_J)
    # OBSERVATIONS ACCESSED FOR METRICS ONLY, AFTER numerical solving.
    measured=[r[r"$T_{out}$"] for r in records]
    err=[m-o for m,o in zip(predictions[1:],measured[1:])]
    return {
        "source_doi":"10.17632/j37x6ptpk2.1",
        "case_id":"B",
        "source_sha256":source["sha256"],
        "status":"TARGET_INDEPENDENT_FLOW_FORCING_BUT_UNCALIBRATED_NOT_VALIDATED",
        "outlet_temperature_target_used_in_physics":False,
        "measured_inputs":["exhaust_velocity_m_s(t)","heater_Tin_C(t)","initial_T1_to_T7_C"],
        "excluded_target_input":"measured Tout_C(t) except final performance diagnostics",
        "assumed_exhaust_pipe_ID_m":pipe_inner_diameter_m,
        "gas_density_assumption":"ideal-gas at assumed constant exhaust pressure, model bed gas inventory constant density",
        "flow_implicit_convergence_max_rel":max(flow_residuals),
        "flow_implicit_mean_iterations":mean(iterations),
        "mass_flow_min_kg_s":min(flows),"mass_flow_max_kg_s":max(flows),
        "internal_energy_residual_max_absolute_J":max(abs(x) for x in energy_residuals),
        "rmse_C":sqrt(mean(x*x for x in err)),
        "mae_C":mean(abs(x) for x in err),
        "mean_bias_C":mean(err),
        "measured_first_80C_s":_first_rising_crossing_s(times,measured,80),
        "predicted_first_80C_s":_first_rising_crossing_s(times,predictions,80),
        "model_time_s":times,
        "predicted_exhaust_C":predictions,
        "internal_sample_positions_m":list(evaluation_positions_m),
        "internal_sampled_gas_K":internal_gas_K,
        "internal_sampled_rock_K":internal_rock_K,
        "internal_sample_positions_are_assumptions_NOT_verified_sensor_locations":True,
        "internal_fields_do_not_use_post_initial_measured_TC":True,
        "measured_exhaust_C_evaluation_only":measured,
        "bed_inputs":asdict(bed),
        "model_boundary_settings":asdict(settings),
        "physical_validation_gate":"BLOCKED",
        "blockers":[
            "unmeasured exhaust pipe bore and local static pressure",
            "exhaust pipe thermal lag vs simulated bed exit temperature",
            "bed inventory constant density despite outlet gas-flow ideal-gas relation",
            "inlet gas velocity/pressure profile, radial horizontal-flow and measured cp(T)",
            "spatial mesh front not converged at 16 cells",
            "sensor calibration, true model holdout and pressure units unresolved",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    p.add_argument("--output",type=Path,default=Path("results/external_horizontal_bed/case_B_no_target_leak_forward.json"))
    args=p.parse_args()
    result=evaluate_case_B(args.input_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("NO_TARGET_LEAK_CASE_B",
          f"RMSE_C={result['rmse_C']:.4f}",
          f"MAE_C={result['mae_C']:.4f}",
          f"breakthrough_s={result['predicted_first_80C_s']}",
          f"flow_max_relative_residual={result['flow_implicit_convergence_max_rel']:.3g}",
          f"mean_flow_iterations={result['flow_implicit_mean_iterations']:.2f}")
    print("CASE_C_D_NOT_READ; NO EXPERIMENTAL VALIDATION CLAIM")


if __name__=="__main__":
    main()
