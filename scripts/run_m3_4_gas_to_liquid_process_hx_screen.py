"""M3.4 recomputable gas TES -> industrial 110/150C process liquid HX gate.

Input MUST be the existing original M3 R718 sequential source-verified model
artifact. Neither the gas-only temperature pass nor the raw model heat count
as contracted process water delivery. Keeps UA, water-loop pressure and
experimental HX properties genuinely UNKNOWN unless explicitly documented.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from carnot_battery_lab.physics.liquid_process_hx_gate import (
    ProcessLiquidHXContract,screen_sampled_discharge_gas_to_liquid,
)

SOURCE_CASE="proposed_industrial_110C_to_150C"
REF_110_K=383.15
REF_150_K=423.15

def evaluate(source:dict,*,source_sha256:str)->dict:
    if source.get("status")!="SEQUENTIAL_R718_THERMAL_TES_SERVICE_SCREEN_UNVALIDATED":
        raise ValueError("only original M3 R718 sequential thermal discharge model accepted")
    if source.get("proposed_service_gas_not_real_process_water_loop") is not True:
        raise ValueError("source gas may not masquerade as process-liquid service")
    if source.get("R718_80C_heat_source_compressor_hardware_qualified") is not False:
        raise ValueError("original model not verified for R718 compressor equipment")
    if not isinstance(source_sha256,str) or len(source_sha256)!=64:
        raise ValueError("source artifact SHA256 required")
    cases=source.get("service_candidates",{})
    case=cases.get(SOURCE_CASE)
    if not isinstance(case,dict):
        raise ValueError("industrial gas-service candidate absent")
    requested=case.get("service_request",{})
    if (abs(requested.get("return_K",0)-REF_110_K)>1e-7 or
        abs(requested.get("required_supply_K",0)-REF_150_K)>1e-7):
        raise ValueError("wrong liquid supply/return target")
    gas_m=requested.get("mass_flow_kg_s")
    bed=source.get("bed_hypothesis",{})
    gas_cp=bed.get("gas_cp_J_kgK")
    if gas_m is None or gas_cp is None:
        raise ValueError("missing original gas mass flow or heat capacity")
    steps=case.get("discharge_steps",[])
    # The industrial LIQUID process is a physically distinct stream; do not
    # inherit the original GAS process's 25 kg/s gas return temperature as water
    # mass flow, or its simplified gas-service grade as measured HX performance.
    contract=ProcessLiquidHXContract()
    result=screen_sampled_discharge_gas_to_liquid(
        discharge_steps=steps,gas_mass_flow_kg_s=gas_m,
        gas_cp_J_kgK=gas_cp,contract=contract)
    sample_status=[{
        "interval":x["interval"],
        "hot_gas_in_C":{k:v["gas_source_in_C"]
                        for k,v in x["samples"].items()},
        "model_grade_necessary_passed":x[
            "all_three_samples_thermal_necessary_gate"],
        "failed_sample_modes":[k for k,v in x["samples"].items()
                                if not v["thermodynamic_heat_and_pinch_necessary_condition"]]
    } for x in result["sampled_intervals"]]
    return {
        "research_status":"M3_4_LIQUID_PROCESS_HX_SAMPLED_PHYSICAL_NECESSITY_ONLY",
        "input_original_M3_model_sha256":source_sha256,
        "input_original_M3_model_published_by_this_repo":True,
        "source_candidate":SOURCE_CASE,
        "original_gas_flow_kg_s":gas_m,
        "original_gas_cp_constant_J_kgK":gas_cp,
        "counterflow_process_contract":{
            "return_C":contract.liquid_return_C,
            "supply_C":contract.liquid_supply_C,
            "required_thermal_W":contract.thermal_duty_W,
            "nominal_constant_cp_process_water_flow_kg_s":
                contract.process_liquid_mass_flow_kg_s,
            "internal_minimum_pinch_K":contract.minimum_internal_approach_K,
            "installed_liquid_process_UA_W_K":None,
            "actual_pressurized_process_water_absolute_Pa":None,
        },
        "source_gas_thermal_service_original_result":{
            "source_case_status":case.get("status"),
            "original_gas_qualified_heat_J_NOT_delivered_liquid_process_heat":
                case.get("qualified_process_heat_J"),
            "original_gas_heat_balance_not_verified_process_liquid_delivery":True,
        },
        "liquid_HX_energy_temperature_and_UA_screen":result,
        "source_model_sample_summary_NO_RAW_EXPERIMENTAL_DATA":sample_status,
        "all_requested_liquid_intervals_grade_qualified":False,
        "industrial_H_REF_service_qualified":False,
        "R718_machine_and_original_source_qualified":False,
        "packed_bed_experimental_breakthrough_and_dP_validated":False,
        "matched_architecture_RTE":None,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sequential-model",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path(
        "results/m3_4_gas_to_liquid_process_hx_necessary_condition.json"))
    a=p.parse_args()
    raw=a.sequential_model.read_bytes()
    source=json.loads(raw)
    result=evaluate(source,source_sha256=hashlib.sha256(raw).hexdigest())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("M3_4_ORIGINAL_GAS_TES_CANDIDATE",
          result["source_gas_thermal_service_original_result"])
    print("M3_4_SAMPLED_LIQUID_HX_HARD_GATE",
          result["liquid_HX_energy_temperature_and_UA_screen"]["status"])
    for row in result["source_model_sample_summary_NO_RAW_EXPERIMENTAL_DATA"]:
        print("M3_4_SAMPLED_PROCESS_HX",row)
    print("M3_4_ORIGINAL_110_150C_1MW_LIQUID_SERVICE_QUALIFIED=False")
    print("M3_4_FULL_ARCHITECTURE_RTE=None")

if __name__=="__main__":main()
