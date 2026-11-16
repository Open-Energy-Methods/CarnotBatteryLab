"""Synthetic M2 sensitivity and STRUCTURAL identifiability audit, not an experiment.

Uses the previously verified constant-property two-temperature bed with a
target-independent ideal-gas exhaust boundary, in a short synthetic forcing
scenario. There are NO measured T_out, gas-flow calibrations or pressure
targets. Parameters/ranges are illustrative scenario values, not empirical
confidence bounds, and are never fitted to 2024 experimental curves.

Key exact model symmetries:
  exhaust m_dot = p*pi*D^2/(4*R*T_model_out) * (v_measured * velocity_scale)
  -> D^2 * velocity_scale cannot be separately identified from this boundary.
  C_s = rho_rock * cp_rock * (1-eps) * V
  -> rho_rock and cp_rock separately cannot be identified from temperature
     histories in the present constant-property model.

This is MODEL structural identifiability only. Real devices could have
additional independent measurements that break these degeneracies.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,replace
from math import isfinite,exp,log,sqrt
from statistics import mean
import numpy as np

from ..physics.packed_bed import PackedBedGeometry
from ..physics.gas_rock_regenerator import GasRockBed,BedState,bed_energy_J
from .exhaust_flow_coupling import ExhaustCouplingSettings,step_from_velocity


@dataclass(frozen=True)
class SyntheticInputs:
    pipe_inner_diameter_m:float=.052
    exhaust_velocity_scale:float=1.
    rock_density_kg_m3:float=3700.
    rock_cp_J_kgK:float=1100.
    porosity:float=.39
    wall_UA_W_K:float=.5
    gas_conductivity_W_mK:float=.034

    def __post_init__(self):
        vals=tuple(asdict(self).values())
        if not all(isfinite(x) for x in vals):
            raise ValueError("all synthetic parameters must be finite")
        if not all(x>0 for x in vals):
            raise ValueError("positive synthetic parameters required")
        if not .25<=self.porosity<=.55:
            raise ValueError("porosity outside declared hypothetical screening range")
        if not .03<=self.pipe_inner_diameter_m<=.08:
            raise ValueError("assumed pipe diameter must be within explicit bounds")


def forward_synthetic(
    parameters:SyntheticInputs=SyntheticInputs(),
    *,cells:int=12,steps:int=24,dt_s:float=45.
)->dict:
    if isinstance(cells,bool) or cells<4 or isinstance(steps,bool) or steps<4 or (
        not isfinite(dt_s) or dt_s<=0):
        raise ValueError("invalid synthetic time/grid definition")
    bed=GasRockBed(
        geometry=PackedBedGeometry(.400,.158,.020,parameters.porosity),
        cells=cells,gas_density_kg_m3=1.,
        gas_cp_J_kgK=1005.,gas_viscosity_Pa_s=2.7e-5,
        gas_conductivity_W_mK=parameters.gas_conductivity_W_mK,
        rock_density_kg_m3=parameters.rock_density_kg_m3,
        rock_cp_J_kgK=parameters.rock_cp_J_kgK,
        ambient_K=303.15,wall_UA_W_K=parameters.wall_UA_W_K,
    )
    settings=ExhaustCouplingSettings(
        pipe_inner_diameter_m=parameters.pipe_inner_diameter_m,
        relative_flow_tolerance=2e-5,
        bdf_relative_tolerance=1e-6,
        max_iterations=30,damping=.75,
    )
    state=BedState.uniform(bed,30.)
    initial_energy=bed_energy_J(bed,state)
    outlet=[]
    total_gas_J=0.
    total_loss_J=0.
    fan_J=0.
    mean_flow=[]
    pressure=[]
    residual_max=0.
    for _ in range(steps):
        sample=step_from_velocity(
            bed,state,inlet_temperature_K=430.,
            measured_exhaust_velocity_m_s=5.*parameters.exhaust_velocity_scale,
            dt_s=dt_s,settings=settings)
        b=sample.bed_step
        state=b.final_state
        outlet.append(float(sample.predicted_exhaust_temperature_K))
        mean_flow.append(float(sample.mass_flow_kg_s))
        pressure.append(float(b.pressure_drop_Pa))
        fan_J+=b.blower_electric_W*dt_s
        total_gas_J+=b.heat_from_hot_gas_J
        total_loss_J+=b.heat_loss_to_ambient_J
        residual_max=max(residual_max,abs(b.energy_residual_J))
    stored=bed_energy_J(bed,state)-initial_energy
    end_to_end_residual=stored-total_gas_J+total_loss_J
    if abs(end_to_end_residual)>max(abs(total_gas_J),1.)*5e-6:
        raise RuntimeError("synthetic first-law audit failed")
    return {
        "T_out_K":outlet,"final_T_out_K":outlet[-1],
        "mean_mass_flow_kg_s":mean(mean_flow),
        "mean_model_Ergun_Pa_NOT_VALIDATED":mean(pressure),
        "stored_energy_increase_J":stored,
        "gas_net_heat_J":total_gas_J,
        "ambient_heat_loss_J":total_loss_J,
        "fan_electric_J_NOT_CALIBRATED":fan_J,
        "end_to_end_first_law_residual_J":end_to_end_residual,
        "largest_step_energy_residual_J":residual_max,
        "analysis_class":"SYNTHETIC_UNCALIBRATED_MODEL_ONLY",
    }


PARAMETERS=tuple(SyntheticInputs.__dataclass_fields__)
LOG_PARAMETER_STEP=.04


def synthetic_local_sensitivity(
    base:SyntheticInputs=SyntheticInputs(), *,
    cells:int=12,steps:int=24,dt_s:float=45.,log_step:float=LOG_PARAMETER_STEP
)->dict:
    if not isfinite(log_step) or not 0<log_step<=.1:
        raise ValueError("positive bounded log-parameter perturbation required")
    reference=forward_synthetic(base,cells=cells,steps=steps,dt_s=dt_s)
    columns=[]
    parameter_metrics={}
    for name in PARAMETERS:
        x=getattr(base,name)
        low=replace(base,**{name:x*exp(-log_step)})
        high=replace(base,**{name:x*exp(log_step)})
        a=forward_synthetic(low,cells=cells,steps=steps,dt_s=dt_s)
        b=forward_synthetic(high,cells=cells,steps=steps,dt_s=dt_s)
        col=(np.asarray(b["T_out_K"])-np.asarray(a["T_out_K"]))/(2*log_step)
        columns.append(col)
        parameter_metrics[name]={
            "low_assumed_value":getattr(low,name),
            "high_assumed_value":getattr(high,name),
            "log_temperature_sensitivity_RMS_K":float(sqrt(mean(col*col))),
            "end_temperature_log_derivative_K":float(col[-1]),
            "stored_energy_log_derivative_J":float(
                (b["stored_energy_increase_J"]-a["stored_energy_increase_J"])/(2*log_step)),
            "only_modelled_pressure_comparison_Pa":float(
                (b["mean_model_Ergun_Pa_NOT_VALIDATED"]-
                 a["mean_model_Ergun_Pa_NOT_VALIDATED"])/(2*log_step)),
        }
    jac=np.column_stack(columns)
    singular_values=np.linalg.svd(jac,compute_uv=False)
    relative_tolerance=.001
    condition=(float("inf") if singular_values[-1]<=singular_values[0]*relative_tolerance
               else float(singular_values[0]/singular_values[-1]))
    ranked=sorted(parameter_metrics,key=lambda k:
                  parameter_metrics[k]["log_temperature_sensitivity_RMS_K"],reverse=True)
    return {
        "status":"SYNTHETIC_MODEL_STRUCTURAL_IDENTIFIABILITY_ONLY_NO_EXPERIMENTAL_FIT",
        "baseline":asdict(base),
        "input_temperature_K":430.,
        "initial_temperature_K":303.15,
        "assumed_exhaust_velocity_m_s":5.,
        "cells":cells,"steps":steps,"step_duration_s":dt_s,
        "parameter_perturbation_log":log_step,
        "baseline_output":reference,
        "parameter_metrics":parameter_metrics,
        "rank_by_RMS_log_temperature_sensitivity":ranked,
        "outlet_temperature_sensitivity_matrix_K":
            jac.tolist(),
        "singular_values_K":singular_values.tolist(),
        "effective_SVD_rank_relative_1e_minus3":
            int(np.sum(singular_values>singular_values[0]*relative_tolerance)),
        "condition_is_infinite_if_near_structural_alias":condition,
        "analytic_exact_model_aliases":[
            "D_exhaust^2 * velocity_calibration_scale in ideal-gas exhaust boundary",
            "rock_density * rock_cp in constant-property rock energy equation",
        ],
        "actual_instrument_confidence_interval_available":False,
        "actual_experiment_fitted":False,
        "source_2024_case_B_C_D_used":False,
        "external_physical_validation_pass":False,
        "limitations":[
            "Model-only locally linear sensitivity around hypothetical source/velocity state",
            "Parameter ranges are sensitivity perturbations not measured uncertainty distributions",
            "Outlet temperature alone cannot isolate D from velocity scale or rho_s from cp_s",
            "Ergun hydraulic output uncalibrated and is not used in SVD measurement matrix",
            "Spatial convergence of this synthetic operating point is not established",
        ],
    }


def exact_reparameterisation_aliases(base:SyntheticInputs=SyntheticInputs(),factor:float=1.1)->dict:
    if not isfinite(factor) or factor<=0:
        raise ValueError("positive alias factor required")
    bore_velocity=replace(
        base,pipe_inner_diameter_m=base.pipe_inner_diameter_m*factor,
        exhaust_velocity_scale=base.exhaust_velocity_scale/factor**2)
    rock_products=replace(
        base,rock_density_kg_m3=base.rock_density_kg_m3*factor,
        rock_cp_J_kgK=base.rock_cp_J_kgK/factor)
    return {
        "pipe_diameter_and_velocity_scale_pair":asdict(bore_velocity),
        "rock_density_and_cp_pair":asdict(rock_products),
        "same_D_squared_velocity_product":bool(abs(
            base.pipe_inner_diameter_m**2*base.exhaust_velocity_scale-
            bore_velocity.pipe_inner_diameter_m**2*bore_velocity.exhaust_velocity_scale)<1e-14),
        "same_rock_volumetric_heat_capacity":bool(abs(
            base.rock_density_kg_m3*base.rock_cp_J_kgK-
            rock_products.rock_density_kg_m3*rock_products.rock_cp_J_kgK)<1e-7),
        "identified_parameters_individually_from_outlet_data":False,
    }
