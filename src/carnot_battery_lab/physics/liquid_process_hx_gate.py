"""M3.4 physically explicit liquid-process HX necessary-condition screen.

Bridge from M3 simulated reverse-flow HOT GAS to contracted 110->150 C
pressurised LIQUID process. DO NOT treat the 'process gas' as process water.

One time sample is a static counterflow differential-enthalpy surrogate:
constant cp gas/liquid, no internal phase changes, gas pressure effects,
installed exchanger characterization, vessel pressure design or control.
Frozen nominal 1MW demand. A positive thermal screen is NOT delivered
industrial heat; a negative sampled grade is an independently useful physical
necessary-condition failure.

A complete accepted HX needs actual gas inlet history T(t), m(t), measured
water pressure, verified hot/cold process thermophysical properties, and a
measured installed UA/hydraulic pressure loss. We preserve these as unknowns.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite,log,expm1
from typing import Sequence

Q_REF_W=1_000_000.
COLD_RETURN_C=110.
COLD_SUPPLY_C=150.


class HXDomainError(ValueError):
    pass


def _positive(v)->bool:
    return (isinstance(v,(float,int)) and not isinstance(v,bool)
            and isfinite(v) and v>0)


@dataclass(frozen=True)
class ProcessLiquidHXContract:
    thermal_duty_W:float=Q_REF_W
    liquid_return_C:float=COLD_RETURN_C
    liquid_supply_C:float=COLD_SUPPLY_C
    liquid_cp_J_kgK:float=4180.
    minimum_internal_approach_K:float=5.
    # Unknown by default. Never invent measured water loop pressure or UA.
    liquid_absolute_pressure_Pa:float|None=None
    installed_UA_W_K:float|None=None
    installed_UA_is_measured:bool=False

    def __post_init__(self):
        v=(self.thermal_duty_W,self.liquid_cp_J_kgK,
           self.minimum_internal_approach_K)
        if (not all(_positive(x) for x in v)
            or not all(isfinite(x) for x in (
                self.liquid_return_C,self.liquid_supply_C))
            or self.liquid_supply_C<=self.liquid_return_C
            or self.liquid_return_C<=-273.15):
            raise HXDomainError("invalid required process-liquid service")
        if (self.liquid_absolute_pressure_Pa is not None and
            not _positive(self.liquid_absolute_pressure_Pa)):
            raise HXDomainError("liquid pressure must be positive absolute Pa")
        if self.installed_UA_W_K is not None and not _positive(
            self.installed_UA_W_K):
            raise HXDomainError("installed UA must be positive W/K when supplied")
        if self.installed_UA_is_measured and self.installed_UA_W_K is None:
            raise HXDomainError("measured UA must have a value")

    @property
    def process_liquid_mass_flow_kg_s(self)->float:
        return self.thermal_duty_W/(self.liquid_cp_J_kgK*
                (self.liquid_supply_C-self.liquid_return_C))


def _lmtd(a:float,b:float)->float:
    if not _positive(a) or not _positive(b):
        raise HXDomainError("zero, crossed or negative counterflow terminal approach")
    if abs(a-b)<=1e-9*max(a,b):
        return (a+b)/2.
    # Stable for nearly equal endpoints.
    return b*((a/b)-1.)/log(a/b)


def minimum_saturated_water_pressure_Pa(supply_C:float)->float:
    """Pressure required to remain single-phase liquid at hot outlet.

    Uses CoolProp and temperature alone; *not* actual process water pressure.
    """
    if not isfinite(supply_C) or not 0<supply_C<374.:
        raise HXDomainError("invalid saturation-pressure temperature")
    try:
        from CoolProp.CoolProp import PropsSI
    except ImportError as exc:
        raise HXDomainError("CoolProp required for liquid phase pressure") from exc
    p=float(PropsSI("P","T",supply_C+273.15,"Q",0,"HEOS::Water"))
    if not _positive(p):
        raise HXDomainError("invalid saturation-pressure property")
    return p


def screen_gas_to_liquid_hx_at_sample(*,
     hot_gas_in_C:float,hot_gas_mass_flow_kg_s:float,
     hot_gas_cp_J_kgK:float,
     contract:ProcessLiquidHXContract=ProcessLiquidHXContract())->dict:
    """Counterflow hot gas cools as 1MW process water warms by 40K.

    Temperatures use Celsius differences. Gas is assumed single-phase
    constant-cp and pressure independent. Hot gas outlet after transferring
    1MW is fixed by *conservation*, not a free independent choice:
       Tgas,out = Tgas,in - Q/(m_g cp_g).
    Endpoint temperatures linear in transferred heat for constant cp, so the
    true minimum counterflow approach is at one endpoint. A sampled hot-gas
    temperature is not a continuous time-history guarantee.
    """
    if not all(_positive(x) for x in
               (hot_gas_mass_flow_kg_s,hot_gas_cp_J_kgK)):
        raise HXDomainError("hot-side mass flow and cp must be positive")
    if not isfinite(hot_gas_in_C) or hot_gas_in_C<=-273.15:
        raise HXDomainError("invalid hot gas source temperature")
    hot_gas_out_C=(hot_gas_in_C-contract.thermal_duty_W/
                   (hot_gas_mass_flow_kg_s*hot_gas_cp_J_kgK))
    if hot_gas_out_C<=-273.15:
        raise HXDomainError("gas outlet extrapolates below absolute zero")
    dT_hot_end_K=hot_gas_in_C-contract.liquid_supply_C
    dT_cold_end_K=hot_gas_out_C-contract.liquid_return_C
    lowest=min(dT_hot_end_K,dT_cold_end_K)
    sat_p=minimum_saturated_water_pressure_Pa(contract.liquid_supply_C)
    p_is_liquid=(contract.liquid_absolute_pressure_Pa is not None and
                 contract.liquid_absolute_pressure_Pa>sat_p)
    grade=lowest+1e-9>=contract.minimum_internal_approach_K
    flow_required=(
        contract.thermal_duty_W/(
          hot_gas_cp_J_kgK*(hot_gas_in_C-contract.liquid_return_C-
                            contract.minimum_internal_approach_K))
        if hot_gas_in_C>contract.liquid_supply_C+
           contract.minimum_internal_approach_K else None)
    ua_req=None
    if grade:
        ua_req=contract.thermal_duty_W/_lmtd(dT_hot_end_K,dT_cold_end_K)
    if not grade:
        status="BLOCKED_HX_INTERNAL_PINCH_OR_INSUFFICIENT_GAS_ENTHALPY"
    elif contract.liquid_absolute_pressure_Pa is None:
        status="MODEL_THERMAL_POSSIBLE_LIQUID_PHASE_PRESSURE_UNKNOWN"
    elif not p_is_liquid:
        status="BLOCKED_PROCESS_WATER_NOT_CONFIRMED_LIQUID"
    elif contract.installed_UA_W_K is None:
        status="MODEL_THERMAL_POSSIBLE_INSTALLED_UA_UNKNOWN"
    elif ua_req is None or contract.installed_UA_W_K+1e-9<ua_req:
        status="BLOCKED_ASSUMED_INSTALLED_UA_INSUFFICIENT"
    else:
        status="MODEL_ONLY_ASSUMED_COUNTERFLOW_HX_PASSES_NOT_PLANT_QUALIFIED"
    return {
        "status":status,
        "required_process_heat_W":contract.thermal_duty_W,
        "required_process_liquid_mass_flow_kg_s":
            contract.process_liquid_mass_flow_kg_s,
        "target_liquid_return_C":contract.liquid_return_C,
        "target_liquid_supply_C":contract.liquid_supply_C,
        "gas_source_in_C":hot_gas_in_C,
        "gas_out_after_full_required_heat_C":hot_gas_out_C,
        "hot_in_minus_liquid_out_approach_K":dT_hot_end_K,
        "hot_out_minus_liquid_in_approach_K":dT_cold_end_K,
        "minimum_calculated_internal_counterflow_approach_K":lowest,
        "nominal_required_minimum_approach_K":contract.minimum_internal_approach_K,
        "thermodynamic_heat_and_pinch_necessary_condition":bool(grade),
        "minimum_gas_mass_flow_kg_s_at_this_temperature_if_duty_possible":
            flow_required,
        "required_counterflow_UA_W_K_if_thermodynamically_possible":ua_req,
        "installed_UA_W_K_from_unverified_input":contract.installed_UA_W_K,
        "installed_UA_was_reported_as_measured_by_caller":
            contract.installed_UA_is_measured,
        "saturated_water_pressure_at_process_supply_Pa":sat_p,
        "actual_process_loop_pressure_Pa":contract.liquid_absolute_pressure_Pa,
        "water_liquid_phase_possible_at_ASSUMED_pressure":bool(p_is_liquid),
        "actual_process_water_pressure_verified_from_measurements":False,
        "wall_heat_capacity_and_transient_HX_dynamics_included":False,
        "source_gas_heat_capacity_temperature_resolved":False,
        "real_HX_and_cooling_loop_test_data_validated":False,
        "1MW_industrial_process_liquid_service_qualified":False,
        "hardware_and_coupled_compressor_qualified":False,
        "architectural_RTE":None,
    }


def screen_sampled_discharge_gas_to_liquid(*,
    discharge_steps:Sequence[dict],gas_mass_flow_kg_s:float,
    gas_cp_J_kgK:float,
    contract:ProcessLiquidHXContract=ProcessLiquidHXContract())->dict:
    """Independent downstream liquid-HX *necessary* screen, never heat credit.

    Need ALL initial/mean/final modeled gas temperatures at EACH interval.
    Mean, initial and final samples do not bound the true continuous
    discharge curve between measurements, so positive check cannot certify.
    A single failing sample is a physically useful negative screen.
    """
    if not discharge_steps:
        raise HXDomainError("no discharge intervals to screen")
    records=[]
    for index,row in enumerate(discharge_steps):
        vals=[row.get(k) for k in (
            "first_process_gas_out_K",
            "mean_process_gas_out_K",
            "end_process_gas_out_K")]
        if len(vals)!=3 or any(v is None or not _positive(v) for v in vals):
            raise HXDomainError("missing original modeled gas outlet sample")
        modes=("initial","time_mean","final")
        checks={}
        for name,t in zip(modes,vals):
            checks[name]=screen_gas_to_liquid_hx_at_sample(
                hot_gas_in_C=t-273.15,
                hot_gas_mass_flow_kg_s=gas_mass_flow_kg_s,
                hot_gas_cp_J_kgK=gas_cp_J_kgK,
                contract=contract)
        records.append({"interval":index+1,
                        "samples":checks,
                        "all_three_samples_thermal_necessary_gate":all(
                            v["thermodynamic_heat_and_pinch_necessary_condition"]
                            for v in checks.values())})
    return {
        "status":("NO_FULL_GRADE_LIQUID_PROCESS_HX_AT_SAMPLED_DISCHARGE_STATES"
                  if not all(row["all_three_samples_thermal_necessary_gate"]
                             for row in records)
                  else "MODEL_ONLY_ALL_SAMPLES_PASSED_BUT_CONTINUOUS_UNVERIFIED"),
        "original_process_contract":"110_to_150_C_liquid_at_1MW",
        "screened_intervals":len(records),
        "sampled_intervals":records,
        "all_samples_necessary_thermal_gate":all(
            row["all_three_samples_thermal_necessary_gate"]
            for row in records),
        "unverified_sampled_gas_state_used_for_process_liquid_HX":True,
        "between_sample_temperature_minimum_unverified":True,
        "installed_HX_UA_and_water_pressure_independently_measured":False,
        "R718_R600_compressor_hardware_qualified":False,
        "experimental_packed_bed_data_qualified":False,
        "actual_process_liquid_heat_delivered_qualified":False,
        "matched_architecture_efficiency":None,
    }
