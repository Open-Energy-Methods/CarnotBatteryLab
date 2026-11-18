"""M3.7 independent CoolProp dry-air EOS sensitivity audit, NOT coupled bed EOS.

Original M3.5/M3.6 gas/rock bed and heat exchanger assume constant cp=1005
J/kgK, rho=2.5 kg/m3 and viscosity=2.35e-5 Pa*s without a justified gas
absolute pressure. This script records how physically resolved dry-air
enthalpy, cp(T,P), rho(T,P), viscosity and conductivity vary at *explicitly
assumed* P. It NEVER changes or 'corrects' bed/HX energy in post-processing
and never calls an EOS sensitivity run a physically coupled plant simulation.
A fully variable-property BED requires the gas mass and pressure inventories,
compressible continuity, heat-transfer and hydraulic closure.
"""
from __future__ import annotations
import math
from dataclasses import asdict
from hashlib import sha256
import json

from .gas_rock_regenerator import GasRockBed
from .packed_bed import ergun_pressure_drop_Pa


def air_state(T_K:float,P_Pa:float)->dict:
    if (isinstance(T_K,bool) or isinstance(P_Pa,bool) or
        not math.isfinite(T_K) or not math.isfinite(P_Pa) or
        not 300.<T_K<650. or not 50_000.<P_Pa<2_000_000.):
        raise ValueError("M3.7 EOS dry-air diagnostic valid only at 300-650K and 0.5-20bara")
    from CoolProp.CoolProp import PropsSI
    keys={"specific_enthalpy_J_kg":"H","cp_J_kgK":"C",
          "density_kg_m3":"D","dynamic_viscosity_Pa_s":"V",
          "thermal_conductivity_W_mK":"L"}
    values={name:float(PropsSI(key,"T",T_K,"P",P_Pa,"HEOS::Air"))
            for name,key in keys.items()}
    if any(not math.isfinite(x) or x<=0 for x in (
        values["cp_J_kgK"],values["density_kg_m3"],
        values["dynamic_viscosity_Pa_s"],
        values["thermal_conductivity_W_mK"])):
        raise ValueError("invalid dry-air EOS")
    values.update({"gas_temperature_K":T_K,
                   "assumed_gas_absolute_pressure_Pa":P_Pa,
                   "prandtl_from_EOS":(
                       values["cp_J_kgK"]*
                       values["dynamic_viscosity_Pa_s"]/
                       values["thermal_conductivity_W_mK"]),
                   "real_gas_loop_pressure_measured":False})
    return values


def air_gas_loop_property_sensitivity(
    bed:GasRockBed|None=None, *,
    assumed_pressures_Pa:tuple[float,...]=(
        101_325.,250_000.,500_000.),
    gas_mass_flow_kg_s:float=15.,
    temperatures_C:tuple[float,...]=(110.,150.,180.,200.,220.,260.),
)->dict:
    if bed is None:bed=GasRockBed()
    if not temperatures_C or not assumed_pressures_Pa or not (
        isinstance(gas_mass_flow_kg_s,(int,float)) and
        not isinstance(gas_mass_flow_kg_s,bool) and
        math.isfinite(gas_mass_flow_kg_s) and gas_mass_flow_kg_s>0):
        raise ValueError("empty or invalid property sensitivity grid")
    if len(set(temperatures_C))!=len(temperatures_C):
        raise ValueError("duplicate gas temperatures")
    if len(set(assumed_pressures_Pa))!=len(assumed_pressures_Pa):
        raise ValueError("duplicate assumed pressure")
    rows=[]
    for pressure in assumed_pressures_Pa:
        ref=air_state(110.+273.15,pressure)
        by_temp={}
        for c in temperatures_C:
            row=air_state(c+273.15,pressure)
            density=row["density_kg_m3"]
            mu=row["dynamic_viscosity_Pa_s"]
            u=gas_mass_flow_kg_s/(density*bed.geometry.cross_section_m2)
            hydraulic=ergun_pressure_drop_Pa(bed.geometry,u,density,mu)
            row.update({
                "constant_cp_reference_J_kgK":bed.gas_cp_J_kgK,
                "constant_density_reference_kg_m3":bed.gas_density_kg_m3,
                "eos_density_over_model_constant_density":
                    density/bed.gas_density_kg_m3,
                "eos_cp_over_model_constant_cp":
                    row["cp_J_kgK"]/bed.gas_cp_J_kgK,
                "original_constant_cp_enthalpy_rise_above_110C_J_kg":
                    bed.gas_cp_J_kgK*(c-110.),
                "eos_air_enthalpy_rise_above_110C_J_kg":
                    row["specific_enthalpy_J_kg"]-
                    ref["specific_enthalpy_J_kg"],
                "eos_bed_ergun_pressure_drop_Pa_uncalibrated":
                    hydraulic,
                "model_gas_mass_inventory_not_updated_from_eos":True,
                "gas_bed_EOS_mass_energy_hydraulic_closure_qualified":False,
            })
            by_temp[str(c)]=row
        rows.append({
            "assumed_pressure_Pa":pressure,
            "pointwise_states":by_temp,
            "gas_absolute_pressure_is_assumed_not_measured":True,
        })
    cfg={"assumed_pressures_Pa":assumed_pressures_Pa,
         "temperatures_C":temperatures_C,"mass_flow_kg_s":gas_mass_flow_kg_s,
         "model_bed":asdict(bed)}
    return {
        "research_stage":"M3_7_DRY_AIR_EOS_SENSITIVITY_NOT_COUPLED",
        "scenario_sha256":sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),
        "gas_mass_flow_kg_s_hypothesis":gas_mass_flow_kg_s,
        "model_constant_gas_cp_J_kgK":bed.gas_cp_J_kgK,
        "model_constant_gas_density_kg_m3":bed.gas_density_kg_m3,
        "original_model_gas_absolute_pressure_Pa":None,
        "gas_EOS_fluids":"HEOS::Air",
        "pressure_scenarios":rows,
        "temperature_dependent_dry_air_properties_evaluated":True,
        "variable_density_or_cp_implemented_in_Carnot_bed":False,
        "variable_density_or_cp_implemented_in_coupled_HX":False,
        "original_gas_pressure_and_actual_machine_unknown":True,
        "real_gas_pressure_temperature_and_flow_measurement":False,
        "model_only_uncertainty_identification_not_physical_validation":True,
        "physical_1MW_liquid_process_qualified":False,
        "R718_R600_compressor_map_qualified":False,
        "architecture_round_trip_efficiency":None,
    }
