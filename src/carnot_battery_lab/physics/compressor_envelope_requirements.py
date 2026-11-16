"""M1.4: compressor-side REQUIREMENTS from existing real-fluid screening states.

A model-demand vector is NOT a manufacturer's performance/operating envelope.
The component calculation merely exports what a future measured map must cover:
suction P/T, discharge P/T, stage pressure ratio, inlet volumetric flow,
refrigerant mass flow and stage shaft work, at every operating time point.

All data are in SI. No R718 or R600 machine is certified by this module.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from math import isfinite
from typing import TYPE_CHECKING

from .r718 import R718Inputs, R718Result, solve_r718

# The foundation test matrix intentionally omits optional CoolProp. R600
# solver imports CoolProp at module load, so keep its type-only dependency
# behind TYPE_CHECKING and import the solver only in real-fluid test paths.
if TYPE_CHECKING:
    from .r600_transcritical_screen import R600ScreenResult


@dataclass(frozen=True)
class CompressorStageDemand:
    refrigerant: str
    stage: str
    suction_pressure_Pa: float
    discharge_pressure_Pa: float
    suction_temperature_C: float
    discharge_temperature_C: float
    stage_pressure_ratio: float
    refrigerant_mass_flow_kg_s: float
    suction_density_kg_m3: float
    suction_volumetric_flow_m3_s: float
    shaft_power_W_idealized: float

    def __post_init__(self) -> None:
        values=(self.suction_pressure_Pa,self.discharge_pressure_Pa,
                self.stage_pressure_ratio,self.refrigerant_mass_flow_kg_s,
                self.suction_density_kg_m3,self.suction_volumetric_flow_m3_s,
                self.shaft_power_W_idealized)
        if not all(isfinite(x) and x>0 for x in values):
            raise ValueError("invalid nonpositive or nonfinite compressor demand")
        if (not isfinite(self.suction_temperature_C) or
                not isfinite(self.discharge_temperature_C) or
                self.discharge_pressure_Pa<=self.suction_pressure_Pa or
                self.stage_pressure_ratio<=1):
            raise ValueError("invalid compressor pressure/temperature demand")


def _suction_density(pressure_Pa: float, temperature_C: float,
                     fluid: str) -> float:
    from CoolProp.CoolProp import PropsSI
    density=float(PropsSI("Dmass","P",pressure_Pa,
                          "T",temperature_C+273.15,fluid))
    if not isfinite(density) or density<=0:
        raise ValueError("invalid real-fluid compressor suction density")
    return density


def _stage(refrigerant: str, stage_name: str, *,
           suction_pressure_Pa: float, discharge_pressure_Pa: float,
           suction_temperature_C: float, discharge_temperature_C: float,
           refrigerant_mass_flow_kg_s: float, shaft_power_W: float,
           fluid: str) -> CompressorStageDemand:
    density=_suction_density(suction_pressure_Pa,suction_temperature_C,fluid)
    return CompressorStageDemand(
        refrigerant,stage_name,suction_pressure_Pa,discharge_pressure_Pa,
        suction_temperature_C,discharge_temperature_C,
        discharge_pressure_Pa/suction_pressure_Pa,refrigerant_mass_flow_kg_s,
        density,refrigerant_mass_flow_kg_s/density,shaft_power_W)


def r718_stage_demands(result: R718Result) -> tuple[CompressorStageDemand,...]:
    """Exact model state pairs, never stitch independently measured maxima."""
    pts={p.tag:p for p in result.state_points}
    m=result.refrigerant_mass_flow_kg_s
    pairs=(("stage1","suction","stage1_out"),
           ("stage2","stage2_in","discharge")) if (
        result.inputs.arrangement=="two_stage") else (
        ("single_stage","suction","discharge"),)
    out=[]
    for name,a,b in pairs:
        suction=pts[a]
        discharge=pts[b]
        out.append(_stage(
            "R718 water",name,suction_pressure_Pa=suction.pressure_Pa,
            discharge_pressure_Pa=discharge.pressure_Pa,
            suction_temperature_C=suction.temperature_K-273.15,
            discharge_temperature_C=discharge.temperature_K-273.15,
            refrigerant_mass_flow_kg_s=m,
            shaft_power_W=m*(discharge.enthalpy_J_kg-suction.enthalpy_J_kg),
            fluid=result.inputs.backend))
    if abs(sum(x.shaft_power_W_idealized for x in out)-
           result.W_compressor_shaft_W)>1e-7*result.W_compressor_shaft_W:
        raise RuntimeError("R718 compressor stage energy sum mismatch")
    for stage,ratio in zip(out,result.stage_pressure_ratios):
        if abs(stage.stage_pressure_ratio-ratio)>1e-9:
            raise RuntimeError("R718 compressor pressure-ratio state mismatch")
    return tuple(out)


def r600_stage_demands(result: R600ScreenResult)->tuple[CompressorStageDemand,...]:
    """Single-stage butane hypothesis, explicitly missing the prototype IHX."""
    return (_stage(
        "R600 n-butane","single_stage",
        suction_pressure_Pa=result.evaporator_pressure_Pa,
        discharge_pressure_Pa=result.high_side_pressure_Pa,
        suction_temperature_C=result.suction_C,
        discharge_temperature_C=result.discharge_C,
        refrigerant_mass_flow_kg_s=result.mass_flow_kg_s,
        shaft_power_W=result.W_shaft_W,fluid=result.inputs.fluid),)


def source_and_process_requirements(*, q_source_W:float,
                                    process_duty_W:float,
                                    source_in_C:float=80.,
                                    source_out_C:float=70.,
                                    process_return_C:float=110.,
                                    process_supply_C:float=150.,
                                    source_cp_J_kgK:float=4180.,
                                    process_cp_J_kgK:float=4180.,
                                    assumed_max_source_flow_kg_s:float=25.)->dict:
    """Hydraulic heat capacities are assumed service BOUNDARIES, not site data."""
    values=(q_source_W,process_duty_W,source_cp_J_kgK,
            process_cp_J_kgK,assumed_max_source_flow_kg_s)
    if (not all(isfinite(x) and x>0 for x in values)
        or not all(isfinite(x) for x in (
            source_in_C,source_out_C,process_return_C,process_supply_C))
        or source_in_C<=source_out_C
        or process_supply_C<=process_return_C):
        raise ValueError("invalid source/sink heat-capacity scenario")
    available=assumed_max_source_flow_kg_s*source_cp_J_kgK*(
        source_in_C-source_out_C)
    return {
        "source_in_C":source_in_C,"source_out_C":source_out_C,
        "sink_return_C":process_return_C,"sink_supply_C":process_supply_C,
        "required_source_heat_W":q_source_W,
        "source_flow_required_kg_s":q_source_W/(
            source_cp_J_kgK*(source_in_C-source_out_C)),
        "assumed_source_flow_cap_kg_s":assumed_max_source_flow_kg_s,
        "source_heat_available_at_assumed_cap_W":available,
        "source_heat_below_assumed_cap":q_source_W<=available*(1+1e-10),
        "required_process_heat_W":process_duty_W,
        "required_process_water_flow_kg_s":process_duty_W/(
            process_cp_J_kgK*(process_supply_C-process_return_C)),
        "hydraulics_are_assumed_not_site_verified":True,
    }


def r718_requirements_report(result:R718Result)->dict:
    demand=r718_stage_demands(result)
    return {
        "fluid":"R718 water",
        "cycle":"two_stage_intercooled_model" if len(demand)==2 else "single_stage_model",
        "equipment_map_qualified":False,
        "compressor_stage_demands":[asdict(p) for p in demand],
        "combined_shaft_W":result.W_compressor_shaft_W,
        "heat_source_and_sink":source_and_process_requirements(
            q_source_W=result.Q_source_W,
            process_duty_W=result.Q_process_W,
            source_in_C=result.inputs.source_inlet_C,
            source_out_C=result.inputs.source_outlet_C,
            process_return_C=result.inputs.process_return_C,
            process_supply_C=result.inputs.process_supply_C,
            source_cp_J_kgK=result.inputs.source_cp_J_kgK,
            process_cp_J_kgK=result.inputs.process_cp_J_kgK,
            assumed_max_source_flow_kg_s=(
                result.inputs.available_source_flow_kg_s
                if result.inputs.available_source_flow_kg_s is not None
                else 25.)),
        "test_required":"manufacturer/vendor multipoint stage maps including "
            "speed, surge/choke, suction state, corrected volumetric capacity, "
            "efficiency and discharge-temperature/oil limits at every point",
        "measured_compressor_operating_envelope":None,
    }


def r600_requirements_report(result:R600ScreenResult)->dict:
    demand=r600_stage_demands(result)
    return {
        "fluid":"R600 n-butane",
        "cycle":"single_stage_transcritical_without_experimental_IHX",
        "equipment_map_qualified":False,
        "compressor_stage_demands":[asdict(p) for p in demand],
        "combined_shaft_W":result.W_shaft_W,
        "heat_source_and_sink":source_and_process_requirements(
            q_source_W=result.Q_source_W,process_duty_W=result.Q_process_W,
            source_in_C=result.inputs.source_inlet_C,
            source_out_C=result.inputs.source_outlet_C,
            process_return_C=result.inputs.process_return_C,
            process_supply_C=result.inputs.process_supply_C,
            source_cp_J_kgK=result.inputs.source_cp_J_kgK,
            process_cp_J_kgK=result.inputs.process_cp_J_kgK,
            assumed_max_source_flow_kg_s=result.inputs.available_source_flow_kg_s),
        "test_required":"real 80-to-70 C R600 compressor speed/flow/pressure/temperature "
            "map for the actual suction-gas-cooled IHX topology; A3 safety qualification",
        "measured_compressor_operating_envelope":None,
    }


def r718_charge_trajectory_demands(charge, hp_inputs:R718Inputs,
                                   bed, control)->dict:
    """Reconstruct compressor map requirements at EVERY completed HP/TES step.

    No partial charge is silently promoted to a complete operating trajectory.
    Boundary data are the recorded TES-responsive gas hot supply and mean
    return. Repeat the exact steady thermodynamic calculation, not a
    continuous interpolation or manufacturer map.
    """
    records=[]
    for index,step in enumerate(charge.steps,1):
        case=replace(
            hp_inputs,useful_process_heat_W=control.heat_into_gas_W,
            process_return_C=step.mean_return_C,
            process_supply_C=step.hot_gas_in_C,
            process_cp_J_kgK=bed.gas_cp_J_kgK,
            available_process_flow_kg_s=None)
        solved=solve_r718(case)
        stages=r718_stage_demands(solved)
        if len(stages)!=len(step.compressor_stage_ratios) or any(
            abs(p.stage_pressure_ratio-q)>1e-7
            for p,q in zip(stages,step.compressor_stage_ratios)):
            raise RuntimeError("TES-responsive R718 charge envelope reconstruction failed")
        records.append({
            "step":index,"elapsed_s":step.elapsed_s,
            "bed_return_C":step.mean_return_C,
            "hot_gas_supply_C":step.hot_gas_in_C,
            "condenser_saturation_C":step.condenser_saturation_C,
            "compressor_stages":[asdict(x) for x in stages],
        })
    return {
        "charge_completed":charge.completed,
        "charge_termination_reason":charge.termination_reason,
        "points":records,
        "entire_requested_trajectory_qualified":False,
        "needs_stage_maps_over_all_points_not_only_initial_point":True,
        "equipment_map_qualified":False,
        "evidence_class":"TES_STATE_RESPONSIVE_NUMERICAL_COMPRESSOR_DEMANDS",
    }
