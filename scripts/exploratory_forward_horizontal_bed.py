"""Uncalibrated exploratory forward check against 2024 horizontal-bed measurements.

Geometry is sourced from a 2022 publication by the SAME experimental group:
Wolde et al., Revista Brasileira de Energia Solar 13(2), 165–173 (2022),
https://rbens.emnuvens.com.br/rbens/article/download/395/287/791
sec.2.1-2.2: 400mm long, 158mm ID, ~20mm slag, epsilon estimated 0.39,
T1-T7 spaced 50mm. Later 2025 paper reports matching 7.45L rig.

This is NOT full experimental validation: pipe exact bore, fluid properties,
time delay, thermo-physical slag parameters, wall losses, sensor position/
fluid-solid phase, pressure units and true mass flow remain uncertain.
Importantly estimated m_dot follows the source paper's Eq.(1), using the
MEASURED OUTLET temperature and exhaust velocity: hence the measured target
enters a model boundary and is NOT a fully blind/out-of-sample prediction.

Zero parameters are calibrated to the Case A holdout. No pressure comparison
to measured ΔP in unverified units. Any error metric is diagnostic only.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from math import pi
from pathlib import Path

import numpy as np

from analyze_horizontal_bed_observations import load_case,EXPECTED
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed, BedState, advance_bed)
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry

R_AIR_J_KG_K=287.05
P_AIR_PA=101_325.0
PUBLISHED_BED_LENGTH_M=0.400
PUBLISHED_BED_DIAMETER_M=0.158
PUBLISHED_PARTICLE_DIAMETER_M_APPROX=0.020
PUBLISHED_ESTIMATED_POROSITY=0.39
# Deliberately assumed design choices. Do not represent as published facts.
ASSUMED_EXHAUST_PIPE_ID_M=0.052
ASSUMED_ROCK_RHO_KG_M3=3700.0
ASSUMED_ROCK_CP_J_KGK=1100.0
ASSUMED_WALL_UA_W_K=0.5
ASSUMED_BED_GAS_DENSITY_KG_M3=1.0
ASSUMED_GAS_VISCOSITY_PA_S=2.7e-5
ASSUMED_GAS_CONDUCTIVITY_W_MK=0.034


def _initial_state(bed:GasRockBed, first:dict)->BedState:
    # Source confirms 7 sensor locations 50 mm apart; the absolute offset
    # is not independently verified. Below, the symmetrical 50-350mm
    # assumption is EXPLICIT and should be varied in later UQ.
    zs=[0.05*k for k in range(1,8)]
    ts=[first[f"$T_{k}$"]+273.15 for k in range(1,8)]
    centres=[(i+0.5)*PUBLISHED_BED_LENGTH_M/bed.cells for i in range(bed.cells)]
    init=np.interp(centres,zs,ts).tolist()
    return BedState(tuple(init),tuple(init))


def _first_rising_crossing_s(times:list[float],values:list[float],threshold_C:float)->float|None:
    for i in range(1,len(times)):
        if values[i-1]<threshold_C<=values[i]:
            return times[i-1]+(times[i]-times[i-1])*(threshold_C-values[i-1])/(values[i]-values[i-1])
    return None


def exploratory_forward(
    case_id:str, *, input_dir:Path, cells:int=16,
    assumed_pipe_ID_m:float=ASSUMED_EXHAUST_PIPE_ID_M,
    assumed_rock_cp_J_kgK:float=ASSUMED_ROCK_CP_J_KGK,
    assumed_wall_UA_W_K:float=ASSUMED_WALL_UA_W_K,
    substeps_per_sample:int=1,
    bdf_relative_tolerance:float=1e-7,
) -> dict:
    if (not isinstance(substeps_per_sample,int) or isinstance(substeps_per_sample,bool)
            or substeps_per_sample<1 or substeps_per_sample>16):
        raise ValueError("substeps_per_sample must be an integer in [1,16]")
    if not 0<bdf_relative_tolerance<=1e-3:
        raise ValueError("relative tolerance must be in (0,1e-3]")
    if not 800<=assumed_rock_cp_J_kgK<=2300:
        raise ValueError("source reports approximate heterogeneous slag cp range 0.8-2.3 kJ/kgK")
    if not 0<=assumed_wall_UA_W_K<=10:
        raise ValueError("wall-UA screening must be finite nonnegative and within explicit scenario range")
    if not 0.035<=assumed_pipe_ID_m<=0.075:
        raise ValueError("pipe bore must be an explicitly bounded assumed source sensitivity")
    source=load_case(input_dir,case_id)
    records=source["rows"]
    geom=PackedBedGeometry(PUBLISHED_BED_LENGTH_M,PUBLISHED_BED_DIAMETER_M,
                            PUBLISHED_PARTICLE_DIAMETER_M_APPROX,
                            PUBLISHED_ESTIMATED_POROSITY)
    bed=GasRockBed(
        geometry=geom,cells=cells,gas_density_kg_m3=ASSUMED_BED_GAS_DENSITY_KG_M3,
        gas_cp_J_kgK=1005,gas_viscosity_Pa_s=ASSUMED_GAS_VISCOSITY_PA_S,
        gas_conductivity_W_mK=ASSUMED_GAS_CONDUCTIVITY_W_MK,
        rock_density_kg_m3=ASSUMED_ROCK_RHO_KG_M3,
        rock_cp_J_kgK=assumed_rock_cp_J_kgK,
        ambient_K=records[0]["$T_{0}$"]+273.15,
        wall_UA_W_K=assumed_wall_UA_W_K,
    )
    state=_initial_state(bed,records[0])
    time=[records[0]["Time exp."]]
    prediction=[records[0][r"$T_{out}$"]] # Initialization only; excluded from error.
    wall_loss_J=0.0
    pressure_model_Pa=[]
    energy_residual_rel=[]
    used_flows=[]
    for prev,row in zip(records,records[1:]):
        dt=row["Time exp."]-prev["Time exp."]
        if not 0<dt<=120:
            raise ValueError(f"unexpected data timestep {dt}")
        # From measured exhaust gas velocity and measured outlet temperature,
        # per experimental paper Eq.(1): not fully blind with respect to T_out.
        rho_ex=P_AIR_PA/(R_AIR_J_KG_K*(row[r"$T_{out}$"]+273.15))
        pipe_A=pi*assumed_pipe_ID_m**2/4
        mass_flow=max(0.0,rho_ex*row["Velocity"]*pipe_A)
        for _ in range(substeps_per_sample):
            step=advance_bed(
                bed,state,inlet_K=row[r"$T_{in}$"]+273.15,
                mass_flow_kg_s=mass_flow,dt_s=dt/substeps_per_sample,
                relative_tolerance=bdf_relative_tolerance)
            state=step.final_state
            wall_loss_J+=step.heat_loss_to_ambient_J
            energy_residual_rel.append(
                abs(step.energy_residual_J)/
                max(abs(step.heat_from_hot_gas_J),abs(step.stored_energy_change_J),1.0))
        time.append(row["Time exp."])
        prediction.append(step.final_outlet_temperature_K-273.15)
        pressure_model_Pa.append(step.pressure_drop_Pa)
        used_flows.append(mass_flow)
    observed=[r[r"$T_{out}$"] for r in records]
    errors=np.asarray(prediction[1:])-np.asarray(observed[1:])
    measured_break=_first_rising_crossing_s(time,observed,80.0)
    model_break=_first_rising_crossing_s(time,prediction,80.0)
    breakthrough_error=(None if measured_break is None or model_break is None
                        else model_break-measured_break)
    return {
        "case_id":case_id,"source_sha256":source["sha256"],
        "status":"EXPLORATORY_UNCALIBRATED_FORWARD_COMPARISON_NOT_VALIDATED",
        "data_used_as_input":"Tin(t), exhaust velocity(t), and measured Tout(t) for exhaust gas density",
        "measurement_leakage_caveat":"Measured Tout is in estimated gas mass flow; NOT blind holdout prediction",
        "reference_geometry":"Wolde et al. 2022 sec 2.1-2.2, 2025 identical quoted 7.45L rig",
        "model":asdict(bed),
        "assumed_exhaust_pipe_ID_m":assumed_pipe_ID_m,
        "rock_cp_J_kgK_assumed":assumed_rock_cp_J_kgK,
        "wall_UA_W_K_assumed":assumed_wall_UA_W_K,
        "substeps_per_sample":substeps_per_sample,
        "bdf_relative_tolerance":bdf_relative_tolerance,
        "time_s":time,"measured_Tout_C":observed,
        "model_Tout_C":prediction,
        "observed_first_80C_outlet_crossing_s":measured_break,
        "model_first_80C_outlet_crossing_s":model_break,
        "model_minus_measured_80C_breakthrough_s":breakthrough_error,
        "rmse_C":float(np.sqrt(np.mean(errors**2))),
        "mae_C":float(np.mean(np.abs(errors))),
        "bias_C":float(np.mean(errors)),
        "final_wall_loss_J":wall_loss_J,
        "max_relative_step_energy_residual":max(energy_residual_rel),
        "min_mdot_kg_s":min(used_flows),"max_mdot_kg_s":max(used_flows),
        "model_pressure_drop_Pa":pressure_model_Pa,
        "measured_pressure_channel":"UNITS_UNKNOWN; never overlay with Ergun in Pa",
        "validation_gate":"NOT_RUN",
        "blocked_reasons":[
            "estimated exhaust pipe bore and T_out-dependent mass flow",
            "unverified absolute TC positions and sensor response/delay",
            "fixed gas/slag properties and assumed insulation losses",
            "bed 1D neglects horizontal buoyancy and radial gradients",
            "no independent uncertainty budget or separate calibration/holdout",
            "pressure taps include duct components; raw pressure units unresolved",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    p.add_argument("--output",type=Path,default=Path("results/external_horizontal_bed/preliminary_forward_check.json"))
    args=p.parse_args()
    data={
      "status":"EXPLORATORY_NOT_PREDICTIVE_VALIDATION",
      "model_family":"1D two-temperature gas-solid bed, constant property, uncalibrated",
      "replay_conditions":"Published 2022 rig geometry; 2024 measured transient Tin, Tout+exhaust velocity",
      "cases":{
          cid:exploratory_forward(cid,input_dir=args.input_dir)
          for cid in ("B","A")
      },
      "never_call_this":"validated experimental performance or independent blind prediction",
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    for cid,result in data["cases"].items():
        print("FORWARD_CHECK",
              f"case={cid} RMSE_C={result['rmse_C']:.3f}",
              f"MAE_C={result['mae_C']:.3f}",
              f"model_minus_meas_80C_s={result['model_minus_measured_80C_breakthrough_s']}",
              f"max_step_energy_residual={result['max_relative_step_energy_residual']:.5g}",
              f"source={result['source_sha256'][:12]}")
    print("VALIDATION_STATUS=NOT_RUN; outlet target enters measured flow boundary")


if __name__=="__main__":
    main()
