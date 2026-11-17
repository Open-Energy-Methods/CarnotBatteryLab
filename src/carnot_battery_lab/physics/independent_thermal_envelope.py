"""M3.5 compressor-independent, hypothetical packed-bed charge/discharge envelope.

An imposed HOT GAS charge boundary is NOT an approved R718/R600 compressor.
A recirculating idealized electric heater tops up gas that has just exited
the bed: P_heater(t) = m_dot cp (T_hot,in - T_bed,out(t)) / eta.
The electric-heater/flow and maximum-power assumptions are declared,
not sourced from manufacturer equipment. Charging and discharge gas are
constant-property surrogate air, not water or hydrocarbon refrigerant.

Discharge return gas at 110 C is imposed, NOT the same stream as the
110->150 C pressurised process liquid. A physically necessary (not sufficient)
counterflow heat exchanger is screened at three gas outlet samples per step.
Even positive samples require an unmodelled remainder cooler or different
gas-return condition, a measured installed UA, a valid water pressure,
independent packed-bed tests and the real continuous gas T(t).
Never derive qualified architecture RTE or physical service from this screen.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Sequence

from .gas_rock_regenerator import (
    BedState,GasRockBed,advance_bed,bed_energy_J,
)
from .reverse_flow_discharge import advance_reverse_discharge
from .liquid_process_hx_gate import (
    ProcessLiquidHXContract,screen_gas_to_liquid_hx_at_sample,
)


def _pos(x:float)->bool:
    return (isinstance(x,(float,int)) and not isinstance(x,bool)
            and isfinite(x) and x>0)


@dataclass(frozen=True)
class IndependentThermalCase:
    name:str
    charge_hot_gas_C:float
    charge_mass_flow_kg_s:float
    charge_duration_s:float
    discharge_mass_flow_kg_s:float=25.
    discharge_duration_s:float=3600.
    integration_step_s:float=600.
    initial_bed_C:float=95.
    discharge_return_gas_C:float=110.
    heater_max_electric_W:float=4_500_000.
    assumed_resistance_efficiency:float=1.

    def __post_init__(self):
        if not self.name or not isinstance(self.name,str) or len(self.name)>80:
            raise ValueError("case must have a short stable name")
        for field in ("charge_mass_flow_kg_s","charge_duration_s",
                      "discharge_mass_flow_kg_s","discharge_duration_s",
                      "integration_step_s","heater_max_electric_W",
                      "assumed_resistance_efficiency"):
            if not _pos(getattr(self,field)):
                raise ValueError(f"invalid thermal case parameter {field}")
        if not 0<self.assumed_resistance_efficiency<=1:
            raise ValueError("heater efficiency outside (0,1]")
        for field in ("charge_hot_gas_C","initial_bed_C",
                      "discharge_return_gas_C"):
            value=getattr(self,field)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or (
                not isfinite(value) or value<=-273.15):
                raise ValueError(f"invalid temperature {field}")
        if self.charge_hot_gas_C<=self.initial_bed_C:
            raise ValueError("charging hot gas must be hotter than initial bed")
        if self.discharge_duration_s/self.integration_step_s>2000 or (
           self.charge_duration_s/self.integration_step_s>2000):
            raise ValueError("limit integration steps for a reproducible study")
        if self.discharge_return_gas_C<self.initial_bed_C:
            raise ValueError("baseline requires return gas no cooler than initial bed")


def _steps(duration_s:float,max_step_s:float):
    # No forgotten fractional last interval or extra zero-time integration.
    n=int(duration_s//max_step_s)
    for _ in range(n):
        yield max_step_s
    tail=duration_s-n*max_step_s
    if tail>1.e-9:
        yield tail


def _hydraulic_re(bed:GasRockBed,mass_flow:float)->float:
    return (mass_flow*bed.geometry.particle_diameter_m/
            (bed.geometry.cross_section_m2*bed.gas_viscosity_Pa_s))


def _reference(bed:GasRockBed,case:IndependentThermalCase,
               contract:ProcessLiquidHXContract)->dict:
    return {
        "research_stage":"M3_5_CONDITIONAL_MODEL_THERMAL_SOURCE_INDEPENDENT",
        "case":asdict(case),
        "bed":asdict(bed),
        "process_liquid_reference":{
          "liquid_return_C":contract.liquid_return_C,
          "liquid_supply_C":contract.liquid_supply_C,
          "liquid_cp_constant_J_kgK":contract.liquid_cp_J_kgK,
          "liquid_mass_flow_kg_s":contract.process_liquid_mass_flow_kg_s,
          "thermal_duty_W":contract.thermal_duty_W,
          "minimum_internal_approach_K":contract.minimum_internal_approach_K,
          "actual_water_pressure_Pa":None,
          "installed_UA_W_K":None,
        },
        "required_process_energy_J":contract.thermal_duty_W*
                                     case.discharge_duration_s,
        "assumed_electric_resistance_charge_heater_only":True,
        "actual_charge_heater_vendor_rating_verified":False,
        "R600_R718_compressor_dependencies_used":False,
        "gas_thermophysical_properties_constant_and_uncalibrated":True,
        "working_gas_absolute_pressure_Pa":None,
        "fluid_and_solid_calibration_from_experiment":False,
        "installed_process_liquid_hx_qualified":False,
        "model_only_compressor_independent_screen":True,
        "matched_1MW_service_empirically_qualified":False,
        "architecture_or_electrical_round_trip_efficiency":None,
    }


def simulate_independent_case(
    bed:GasRockBed,case:IndependentThermalCase,*,
    contract:ProcessLiquidHXContract=ProcessLiquidHXContract()
)->dict:
    """Prescribed thermal source -> conservative bed -> reverse-flow gas ->
    1MW process-water HX necessary condition, not completed plant flow sheet.

    1MW duty and 110/150 C contract are frozen here to the project benchmark.
    Heat attributed to useful process heating is *always 0 qualified joules*:
    sampled hypothetical passage is a physical possibility screen only.
    """
    if (contract.thermal_duty_W!=1e6 or
        contract.liquid_return_C!=110. or
        contract.liquid_supply_C!=150. or
        contract.liquid_absolute_pressure_Pa is not None or
        contract.installed_UA_W_K is not None):
        raise ValueError("M3.5 accepts original 1MW 110->150C contract with unknown actual liquid hardware only")
    b=_reference(bed,case,contract)
    state=BedState.uniform(bed,case.initial_bed_C)
    bed_start_J=bed_energy_J(bed,state)
    charge_source_K=case.charge_hot_gas_C+273.15
    gas_return_K=case.discharge_return_gas_C+273.15
    min_hot_in_C=contract.liquid_supply_C+contract.minimum_internal_approach_K
    peak_charge_electric_W=(case.charge_mass_flow_kg_s*bed.gas_cp_J_kgK*
                            (charge_source_K-state.fluid_temperature_K[-1])/
                            case.assumed_resistance_efficiency)
    charge_re=_hydraulic_re(bed,case.charge_mass_flow_kg_s)
    discharge_re=_hydraulic_re(bed,case.discharge_mass_flow_kg_s)
    b["optimistic_uniform_hot_bed_sensible_energy_above_initial_J"]=(
        bed_energy_J(bed,BedState.uniform(bed,case.charge_hot_gas_C))
        -bed_start_J)
    b["charging_source_initial_instantaneous_electric_power_W"]=peak_charge_electric_W
    b["charging_source_declared_max_electric_power_W"]=case.heater_max_electric_W
    b["charge_wakao_particle_Re"]=charge_re
    b["discharge_wakao_particle_Re"]=discharge_re
    b["source_grade_necessary_C"]=min_hot_in_C
    # A passive bed initially below the imposed source temperature cannot
    # deliver hotter gas than that source in this reduced-order model. Check
    # BOTH source-temperature and discharge-flow enthalpy upper bounds first.
    hypothetical_source_limited_hx=screen_gas_to_liquid_hx_at_sample(
        hot_gas_in_C=case.charge_hot_gas_C,
        hot_gas_mass_flow_kg_s=case.discharge_mass_flow_kg_s,
        hot_gas_cp_J_kgK=bed.gas_cp_J_kgK,contract=contract)
    b["optimistic_max_hot_gas_source_temperature_hx_gate_pass"]=(
        hypothetical_source_limited_hx[
          "thermodynamic_heat_and_pinch_necessary_condition"])
    b["optimistic_source_max_hot_gas_hx_required_UA_W_K"]=(
        hypothetical_source_limited_hx[
          "required_counterflow_UA_W_K_if_thermodynamically_possible"])
    reason=None
    if case.charge_hot_gas_C+1e-9<min_hot_in_C:
        reason="SOURCE_TEMPERATURE_BELOW_MINIMUM_PROCESS_HOT_TERMINAL"
    elif not hypothetical_source_limited_hx[
        "thermodynamic_heat_and_pinch_necessary_condition"]:
        reason="SOURCE_TEMPERATURE_AND_DISCHARGE_FLOW_CANNOT_SUPPLY_1MW_WITH_FINITE_PINCH"
    elif peak_charge_electric_W>case.heater_max_electric_W*(1.+1e-12):
        reason="ASSUMED_HEATER_INITIAL_POWER_OVER_DECLARED_LIMIT"
    elif not all(15<=r<=8500 for r in (charge_re,discharge_re)):
        reason="WAKAO_HEAT_TRANSFER_CORRELATION_OUTSIDE_RE_DOMAIN"
    if reason:
        return {**b,"status":"PRECHARGE_PHYSICAL_NECESSARY_CONDITION_BLOCKED",
                "blocker":reason,
                "charge_model_executed":False,
                "discharge_model_executed":False,
                "screened_full_duty_prefix_duration_s":0.,
                "nominal_full_duty_discharge_duration_screened":False,
                "simulated_process_heat_delivered_J":None,
                "actual_industrial_process_heat_qualified_J":0.}

    charge_heat_J=0.
    charge_wall_loss_J=0.
    charge_blower_J=0.
    charge_max_ergun_Pa=0.
    peak_charge_W=peak_charge_electric_W
    charge_max_abs_step_residual_J=0.
    for dt_s in _steps(case.charge_duration_s,case.integration_step_s):
        step=advance_bed(bed,state,inlet_K=charge_source_K,
                         mass_flow_kg_s=case.charge_mass_flow_kg_s,dt_s=dt_s)
        state=step.final_state
        if step.heat_from_hot_gas_J<-1e-5:
            raise RuntimeError("charge heat flowed from stored bed to nominal hot source")
        # Do not silently presume a recirculating heater smaller than its
        # instantaneous required power. This checks initial/final samples;
        # intra-step extrema remain unverified.
        hottest_needed=max(
            (charge_source_K-step.first_temperature_K),
            (charge_source_K-step.final_outlet_temperature_K),0.)
        electric_W=(case.charge_mass_flow_kg_s*bed.gas_cp_J_kgK*
                    hottest_needed/case.assumed_resistance_efficiency)
        peak_charge_W=max(peak_charge_W,electric_W)
        if peak_charge_W>case.heater_max_electric_W*(1.+1e-10):
            raise RuntimeError("assumed charge heater power exceeded declared bound")
        charge_heat_J+=step.heat_from_hot_gas_J
        charge_wall_loss_J+=step.heat_loss_to_ambient_J
        charge_blower_J+=step.blower_electric_W*dt_s
        charge_max_ergun_Pa=max(charge_max_ergun_Pa,step.pressure_drop_Pa)
        charge_max_abs_step_residual_J=max(
            charge_max_abs_step_residual_J,abs(step.energy_residual_J))
    charged=state
    charged_U=bed_energy_J(bed,charged)
    charge_residual=charged_U-bed_start_J-charge_heat_J+charge_wall_loss_J
    if abs(charge_residual)>1e-5*max(1.,abs(charge_heat_J)):
        raise RuntimeError("source-independent charging violated bed conservation")

    charge_original_thermal_J=charge_heat_J
    charge_ideal_resistance_electric_J=(
        charge_original_thermal_J/case.assumed_resistance_efficiency)
    charge_record={
        "charge_gas_inlet_C":case.charge_hot_gas_C,
        "charge_duration_s":case.charge_duration_s,
        "total_model_heat_put_into_bed_from_source_gas_J":
            charge_original_thermal_J,
        "assumed_resistance_heater_eta":case.assumed_resistance_efficiency,
        "model_charge_heater_electricity_J_not_real_plant":
            charge_ideal_resistance_electric_J,
        "model_charge_blower_electricity_J_Ergun_uncalibrated":charge_blower_J,
        "sampled_peak_electric_heater_power_W":peak_charge_W,
        "declared_assumed_electric_heater_limit_W":case.heater_max_electric_W,
        "total_wall_heat_loss_J":charge_wall_loss_J,
        "charge_start_bed_energy_J":bed_start_J,
        "charge_end_bed_energy_J":charged_U,
        "charge_integrated_first_law_residual_J":charge_residual,
        "max_step_first_law_residual_J":charge_max_abs_step_residual_J,
        "max_predicted_Ergun_charge_bed_pressure_drop_Pa_uncalibrated":
            charge_max_ergun_Pa,
        "postcharge_first_gas_cell_C":charged.fluid_temperature_K[0]-273.15,
        "postcharge_last_gas_cell_C":charged.fluid_temperature_K[-1]-273.15,
        "postcharge_max_solid_C":max(charged.solid_temperature_K)-273.15,
        "postcharge_mean_solid_C":sum(charged.solid_temperature_K)/
              bed.cells-273.15,
    }

    gas_extracted_J=0.
    discharge_wall_J=0.
    discharge_blower_J=0.
    max_discharge_ergun_Pa=0.
    thermal_prefix_s=0.
    prefix_active=True
    first_bad_interval=None
    records=[]
    max_required_UA=0.
    max_cooler_W=0.
    for i,dt_s in enumerate(
        _steps(case.discharge_duration_s,case.integration_step_s),1):
        r=advance_reverse_discharge(
            bed,state,return_gas_K=gas_return_K,
            mass_flow_kg_s=case.discharge_mass_flow_kg_s,
            dt_s=dt_s,minimum_process_delivery_K=min_hot_in_C+273.15)
        state=r.final_state
        gas_extracted_J+=r.signed_heat_to_process_gas_J
        discharge_wall_J+=r.ambient_loss_J
        discharge_blower_J+=r.fan_electric_J_model
        max_discharge_ergun_Pa=max(
            max_discharge_ergun_Pa,r.model_pressure_drop_Pa_not_calibrated)
        temps_C={
           "initial":r.first_outlet_K-273.15,
           "time_mean":r.time_mean_outlet_K-273.15,
           "final":r.final_outlet_K-273.15,
        }
        checks={k:screen_gas_to_liquid_hx_at_sample(
            hot_gas_in_C=t,
            hot_gas_mass_flow_kg_s=case.discharge_mass_flow_kg_s,
            hot_gas_cp_J_kgK=bed.gas_cp_J_kgK,contract=contract)
            for k,t in temps_C.items()}
        eligible=all(x["thermodynamic_heat_and_pinch_necessary_condition"]
                     for x in checks.values())
        required_UA=(max(x["required_counterflow_UA_W_K_if_thermodynamically_possible"]
                         for x in checks.values()) if eligible else None)
        model_additional_gas_cooler_thermal_W=(
           max(0.,r.signed_heat_to_process_gas_J/dt_s-contract.thermal_duty_W)
           if eligible else None)
        if eligible:
            max_required_UA=max(max_required_UA,required_UA)
            max_cooler_W=max(max_cooler_W,model_additional_gas_cooler_thermal_W)
        if eligible and prefix_active:
            thermal_prefix_s+=dt_s
        else:
            prefix_active=False
            if first_bad_interval is None:
                first_bad_interval=i
        records.append({
            "interval_index":i,
            "step_duration_s":dt_s,
            "outlet_gas_sample_C":temps_C,
            "required_hot_gas_source_minimum_C":min_hot_in_C,
            "model_only_all_three_samples_thermal_pinch_necessary_pass":
                eligible,
            "sample_maximum_required_counterflow_UA_W_K_if_pass":
                required_UA,
            "minimum_hot_and_cold_endpoint_pinch_by_sample_K":{
                k:v["minimum_calculated_internal_counterflow_approach_K"]
                for k,v in checks.items()},
            "model_gas_heat_extracted_from_bed_J_SIGNED":
                r.signed_heat_to_process_gas_J,
            "assumed_1MW_process_liquid_heat_J_if_conditional":(
                contract.thermal_duty_W*dt_s if eligible else None),
            "extra_gas_cooler_duty_W_to_enforce_110C_return_only_if_pass":
                model_additional_gas_cooler_thermal_W,
            "gas_return_110C_requires_unmodelled_extra_cooler_or_different_loop":
                True,
            "model_pressure_drop_Pa_Ergun_uncalibrated":
                r.model_pressure_drop_Pa_not_calibrated,
            "bed_energy_residual_J":r.bed_first_law_residual_J,
        })
    discharge_end_U=bed_energy_J(bed,state)
    discharge_residual=(
        discharge_end_U-charged_U+gas_extracted_J+discharge_wall_J)
    if abs(discharge_residual)>1e-5*max(
        1.,abs(gas_extracted_J),abs(charged_U-discharge_end_U)):
        raise RuntimeError("source-independent discharge violated bed conservation")
    total_residual=(
        discharge_end_U-bed_start_J-charge_heat_J+charge_wall_loss_J+
        gas_extracted_J+discharge_wall_J)
    if abs(total_residual)>1e-5*max(
        1.,abs(charge_heat_J),abs(gas_extracted_J)):
        raise RuntimeError("source-independent combined cycle violated first law")
    screened_full=abs(thermal_prefix_s-case.discharge_duration_s)<=1e-8
    return {
        **b,
        "status":("MODEL_ONLY_FULL_DURATION_GAS_TO_LIQUID_NECESSARY_GATE"
                  if screened_full else
                  "MODEL_ONLY_PROCESS_THERMAL_GRADE_OR_DUTY_UNMET"),
        "charge_model_executed":True,
        "discharge_model_executed":True,
        "charging":charge_record,
        "post_charge_bed_state":{
            "fluid_temperature_K":list(charged.fluid_temperature_K),
            "solid_temperature_K":list(charged.solid_temperature_K),
        },
        "discharge": {
            "requested_duration_s":case.discharge_duration_s,
            "screened_full_duty_prefix_duration_s":thermal_prefix_s,
            "first_failed_step_number":first_bad_interval,
            "all_sampled_intervals_necessary_grade_pass":screened_full,
            "discharge_total_model_heat_into_gas_J_SIGNED":gas_extracted_J,
            "model_discharge_blower_electricity_J_Ergun_uncalibrated":
                discharge_blower_J,
            "model_discharge_wall_loss_J":discharge_wall_J,
            "model_discharge_max_bed_pressure_drop_Pa_Ergun_uncalibrated":
                max_discharge_ergun_Pa,
            "min_process_water_required_massflow_kg_s":
                contract.process_liquid_mass_flow_kg_s,
            "maximum_required_counterflow_UA_W_K_across_eligible_steps":
                max_required_UA if max_required_UA>0 else None,
            "max_interval_mean_additional_gas_cooler_thermal_W_if_1MW":
                max_cooler_W if max_required_UA>0 else None,
            "bed_energy_after_discharge_J":discharge_end_U,
            "discharge_integrated_first_law_residual_J":discharge_residual,
            "combined_storage_first_law_residual_J":total_residual,
            "sampled_intervals":records,
        },
        "screened_full_duty_prefix_duration_s":thermal_prefix_s,
        "nominal_full_duty_discharge_duration_screened":screened_full,
        "continuous_between_samples_guarantee":False,
        "missing_actual_installed_water_hx_UA":True,
        "missing_pressurised_liquid_water_pressure":True,
        "additional_gas_cooler_or_loop_balance_required":True,
        "simulated_process_heat_delivered_J":None,
        "actual_industrial_process_heat_qualified_J":0.,
    }


def study_envelope(
    bed:GasRockBed,cases:Sequence[IndependentThermalCase],*,
    contract:ProcessLiquidHXContract=ProcessLiquidHXContract()
)->dict:
    if not cases or len(cases)>50:
        raise ValueError("study must comprise 1–50 declared cases")
    if len({c.name for c in cases})!=len(cases):
        raise ValueError("case names must be unique and stable")
    entries={x.name:simulate_independent_case(
        bed,x,contract=contract) for x in cases}
    model_passes=[
        k for k,v in entries.items()
        if v["nominal_full_duty_discharge_duration_screened"]]
    return {
        "research_milestone":"M3_5_COMPRESSOR_INDEPENDENT_THERMAL_ENVELOPE",
        "original_contract":"1MW_gross_liquid_110_to_150C",
        "cases":entries,
        "case_count":len(entries),
        "model_only_possible_thermal_grade_cases":model_passes,
        "model_only_observation_no_independent_compressor_data":True,
        "actual_industrial_qualified_cases":[],
        "matched_service_architecture_ranking":None,
        "round_trip_efficiency":None,
        "remaining_disqualifications":[
            "Prescribed high-temperature gas boundary has no validated equipment",
            "Gas constant properties, 1D packed bed, uncalibrated Wakao and Ergun",
            "Only first/mean/final discharge samples tested, not a continuously bounded HX inlet",
            "Real installed process-water HX UA and loop absolute pressure unknown",
            "An independent gas cooler or different return-gas thermodynamics is required",
            "No experimental packed-bed breakthrough or measured differential pressure",
            "No validated real compressor, electrical charging integration or repeated cyclic operation",
        ],
    }
