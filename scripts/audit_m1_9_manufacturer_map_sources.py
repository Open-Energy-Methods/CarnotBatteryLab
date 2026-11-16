"""M1.9 — primary-source vendor safety-control and experimental-map acquisition gate.

This is an independent DOCUMENTED-COMPONENT prescreen for modelled H-REF
compressor demands. It is NOT a manufacturer performance map and never returns
hardware qualification. All pressure high-shutdown numbers from the UniSAB
controller are *configurable controller limits*, not independently measured
mechanical design ratings. Their reference pressure convention is not
explicitly established in the notes. We show both plausible absolute/gauge
interpretations rather than silently equating them with absolute model Pa.

Cited independent source:
Johnson Controls Sabroe UniSAB 4 Engineering Guide rev 005,
Notes item 30 (HPC/HPO R600 reduced shutdown 36 bar; HPX 65 bar design
general high shutdown 57–57.5 bar, R600 variant not established).
IIR GL2020 10.18462/iir.gl.2020.1019 (Verpe stage maxima 2.4 / 2.0;
different approximately atmospheric steam test rig).
IIR GL2024 10.18462/iir.gl2024.1286 (Dowdell R718 1–2 bara inlet).
OST 10.1016/j.ijrefrig.2025.11.012 Table 1 (439 off-target
HFO/mix measured test points but no listed pure R600 observations).
"""
from __future__ import annotations
from hashlib import sha256
import json, math
from pathlib import Path

SERVICE={
    "waste_source_inlet_C":80.,
    "waste_source_outlet_C":70.,
    "process_liquid_inlet_C":110.,
    "process_liquid_outlet_C":150.,
    "gross_process_heat_W":1_000_000.,
}
BAR_PA=100_000.
NOMINAL_ATMOSPHERE_PA=101_325.
SABROE_NOTE30_URL=(
    "https://docs.johnsoncontrols.com/industrialrefrigeration/r/Sabroe/"
    "en-US/UniSAB-4-Engineering-Guide/005/Warnings-and-shutdowns/"
    "Analog-warnings-and-shutdowns/Notes?contentId=ED6PJOpwsqeb9wnpJtanEA"
)
EVIDENCE=(
    {
        "id":"sabroe_unisab4_revision005_note30_hpc_hpo_r600",
        "category":"MANUFACTURER_CONTROLLER_HIGH_DISCHARGE_SHUTDOWN",
        "source_url":SABROE_NOTE30_URL,
        "component":"HPC/HPO compressor using R600 and UniSAB 4",
        "fluid":"R600 n-butane",
        "high_warning_bar_as_published":35.5,
        "high_shutdown_bar_as_published":36.0,
        "published_pressure_reference":"NOT_EXPLICITLY_VERIFIED_ABS_OR_GAUGE",
        "physical_design_pressure_or_rated_map_known":False,
        "actual_suction_flow_or_speed_map_known":False,
        "manufacturer_specific_variant_identified_for_H_REF":False,
    },
    {
        "id":"sabroe_unisab4_revision005_note30_hpx",
        "category":"MANUFACTURER_CONTROLLER_SHUTDOWN_GENERAL_HPX",
        "source_url":SABROE_NOTE30_URL,
        "component":"HPX 65 bar design pressure model variant",
        "fluid":"NOT_R600_SPECIFIC",
        "high_warning_bar_as_published":57.0,
        "high_shutdown_bar_as_published":57.5,
        "published_pressure_reference":"NOT_EXPLICITLY_VERIFIED_ABS_OR_GAUGE",
        "physical_design_pressure_or_rated_map_known":False,
        "actual_suction_flow_or_speed_map_known":False,
        "manufacturer_specific_variant_identified_for_H_REF":False,
    },
    {
        "id":"verpe_2020_two_stage_r718_measured_peak_pr",
        "category":"INDEPENDENT_RIG_MAXIMA_NOT_FULL_MAP",
        "source_url":"https://doi.org/10.18462/iir.gl.2020.1019",
        "component":"2019/2020 SINTEF approximate atmospheric steam rig",
        "fluid":"R718 water",
        "stage_peak_pressure_ratios":[2.4,2.0],
        "published_nominal_suction_Pa":None,
        "multistage_map_and_holdouts_available":False,
        "simultaneous_maxima_established":False,
    },
    {
        "id":"dowdell_2024_sintef_friendship_r718",
        "category":"MEASURED_DIFFERENT_SUCTION_PRESSURE_R718",
        "source_url":"https://doi.org/10.18462/iir.gl2024.1286",
        "component":"two-stage steam turbo compressor, solar-assisted HTHP",
        "fluid":"R718 water",
        "published_inlet_pressure_range_bar_a":[1.,2.],
        "maximum_second_stage_discharge_bar_a":5.3,
        "full_25kPa_steam_compressor_map_available":False,
    },
    {
        "id":"brendel_2026_439_experimental_not_R600",
        "category":"EXPERIMENTAL_PUBLICATION_WITH_NO_PURE_R600_IN_TABLE_1",
        "source_url":"https://doi.org/10.1016/j.ijrefrig.2025.11.012",
        "component":"Bitzer 2DES-3Y reciprocating 439-condition measured campaign",
        "fluid":"MIXED_HFO_AND_OTHER_REFRIGERANTS_NOT_PURE_R600",
        "total_published_observations_all_fluids":439,
        "pure_r600_observations_reported_in_table_1":0,
        "overall_all_fluid_suction_pressure_range_kPa":[41.,922.],
        "capacity_and_machine_identity_differ_from_H_REF":True,
    },
    {
        "id":"verdnik_rieberer_2022_transcritical_r600",
        "category":"MEASURED_HIGHTEMP_DIFFERENT_SOURCE_AND_IHX",
        "source_url":"https://doi.org/10.1016/j.ijrefrig.2022.05.010",
        "component":"Graz lab transcritical single-stage IHX and suction-gas-cooled reciprocating compressor",
        "fluid":"R600 n-butane",
        "reported_source_inlet_C":60.,
        "reported_sink_outlet_C":160.,
        "reported_thermal_kW":24.2,
        "source_only_main_boundary_not_target":True,
        "calibrated_full_stage_map_accessed":False,
    },
)
OUTREACH=(
    {
        "id":"TU_GRAZ_R600","contacts":[
            "manuel.verdnik@tugraz.at","rene.rieberer@tugraz.at"],
        "contact_source":"https://online.tugraz.at/tug_online/fdb_detail.ansicht?cvfanr=F60024&cvorgnr=&sprache=2",
        "ask":"Original measured transcritical R600 compressor points across 40-60 bar "
              "including source-boundary temperatures, compressor speed, mass/actual "
              "suction volume, shaft/electric meter, IHX and suction-gas cooler "
              "topology, design/thermal/oil limits, uncertainties and held-out runs.",
    },
    {
        "id":"SINTEF_R718","contacts":["christian.schlemminger@sintef.no"],
        "contact_source":"https://heatpumpingtechnologies.org/content/uploads/sites/70/2024/04/annex58finalwebinarpresentations.pdf",
        "ask":"Original 2019/2020 and 2024 measured steam stage maps, including "
              "R718 suction at 25 kPa absolute, stage ratio 4.66 (if studied), "
              "speed/actual inlet volume/shaft power/stability and sensor "
              "uncertainty; clarify all work at atmospheric inlet and any "
              "alternative machinery rated for subatmospheric steam.",
    },
    {
        "id":"OST_BRANDEL_439","contacts":["leon.brendel@ost.ch"],
        "contact_source":"https://doi.org/10.1016/j.ijrefrig.2025.11.012",
        "ask":"Clarify original 439-observation Excel supplementary availability and "
              "confirm Table 1 has no pure R600; ask about separately tested "
              "R600 pressure/flow/shaft/speed observations at 7.2 bar suction "
              "and 40-60 bar high side with measurement uncertainties.",
    },
    {
        "id":"SABROE_MANUFACTURER",
        "contacts":[],
        "contact_source":"https://www.sabroe.com/contact-us",
        "ask":"Confirm pressure-unit reference, R600 HPC/HPO 35.5/36 bar controller "
              "warning/shutdown applicability, exact HPX 65 bar design "
              "R600 approval and pressure/speed/temperature envelopes, "
              "oil/discharge limits, A3 qualification and original maps.",
        "official_contact_route":"official website form / manufacturer engineering team",
    },
)

def _finite_positive(x)->bool:
    return isinstance(x,(float,int)) and not isinstance(x,bool) and (
        math.isfinite(x) and x>0)

def _check_target(d:dict)->None:
    if not isinstance(d,dict) or d.get("evidence_status")!=(
        "M1_4_SCIENTIFIC_REQUIREMENTS_AND_LITERATURE_CROSSWALK_ONLY"):
        raise ValueError("expected unchanged independent M1.4 model-demand contract")
    req=d.get("input_contract",{})
    for case in ("r718","r600"):
        inputs=req.get(case,{})
        for key,expected in (
            ("source_inlet_C",80.),("source_outlet_C",70.),
            ("process_return_C",110.),("process_supply_C",150.)):
            if not isinstance(inputs,dict) or inputs.get(key)!=expected:
                raise ValueError(f"wrong target source/sink contract {case} {key}")
    # The pressure-screen data are modelled hypotheses, not measured points.
    if d.get("equipment_qualified") is not False:
        raise ValueError("source model must not already claim hardware validity")

def _pressure_bar_cases(record:dict, limit_bar:float)->dict:
    """Conservative countercheck for two unspecified control-pressure units.

    Both absolute and gauge interpretations are exercised; the gauge case
    assumes 1.01325 bar atmosphere as a PROXIMITY CALCULATION, not a
    manufacturer's stated unit or a universal plant assumption.
    """
    dis=record["discharge_pressure_Pa"]
    if not _finite_positive(dis):raise ValueError("invalid model pressure")
    maximum_absolute_if_gauge=(limit_bar*BAR_PA+NOMINAL_ATMOSPHERE_PA)
    return {
        "model_discharge_pressure_Pa_absolute":dis,
        "manufacturer_controller_source_value_bar_UNSPECIFIED_REF":limit_bar,
        "model_above_control_shutdown_if_published_bar_is_absolute":
            dis>limit_bar*BAR_PA,
        "model_above_control_shutdown_if_published_bar_is_gauge_with_nominal_atmosphere":
            dis>maximum_absolute_if_gauge,
        "model_robustly_exceeds_both_pressure_reference_interpretations":
            dis>maximum_absolute_if_gauge,
        "control_setting_mechanical_design_rating":False,
        "R600_approval_and_full_performance_map_validated":False,
    }

def audit_primary_machine_evidence(requirements:dict)->dict:
    _check_target(requirements)
    r600=requirements["r600_80C_source_110_150C_transcritical_screen"][
        "map_requirements_for_numerically_feasible_points"]
    rows=[]
    for high,case in sorted(r600.items(),key=lambda pair:int(pair[0])):
        if len(case["compressor_stage_demands"])!=1:
            raise ValueError("expected H-REF original single-stage R600 hypothesis")
        stage=case["compressor_stage_demands"][0]
        if abs(float(high)-stage["discharge_pressure_Pa"])>1:
            raise ValueError("stage pressure not equal to pressure-scan key")
        rows.append({
            "demand_high_pressure_Pa":stage["discharge_pressure_Pa"],
            "demand_suction_pressure_Pa":stage["suction_pressure_Pa"],
            "demand_suction_temperature_C":stage["suction_temperature_C"],
            "demand_suction_actual_m3_s":stage["suction_volumetric_flow_m3_s"],
            "demand_stage_pressure_ratio":stage["stage_pressure_ratio"],
            "HPC_HPO_R600_documented_UniSAB_high_shutdown_comparison":
                _pressure_bar_cases(stage,36.0),
            "HPX_65bar_design_GENERIC_not_R600_specific_comparison":
                _pressure_bar_cases(stage,57.5),
            "Sabroe_HPC_HPO_this_controller_H_REF_operating_point_eligible":False,
            "Sabroe_HPX_R600_variant_qualification_known":False,
            "R600_manufacturer_map_M1_5_accepted":False,
        })
    if not rows:raise ValueError("R600 scan has no reported nominal points")
    r718=requirements["r718_80C_source_110_150C_direct_liquid_screen"][
        "compressor_stage_demands"]
    if len(r718)!=2:raise ValueError("expected original two-stage steam model")
    ratios=(2.4,2.0)
    ratio_results=[]
    for stage,upper in zip(r718,ratios):
        if not _finite_positive(stage["stage_pressure_ratio"]):
            raise ValueError("steam ratio invalid")
        ratio_results.append({
            "stage":stage["stage"],
            "demand_suction_pressure_Pa":stage["suction_pressure_Pa"],
            "demand_suction_temperature_C":stage["suction_temperature_C"],
            "demand_pressure_ratio":stage["stage_pressure_ratio"],
            "SINTEF_2020_other_rig_reported_individual_peak_ratio":upper,
            "demand_exceeds_different_rig_individual_peak_ratio":
                stage["stage_pressure_ratio"]>upper,
            "same_verified_equipment_and_intercooling_topology":False,
            "full_original_steam_speed_flow_map_provided":False,
        })
    steam_initial=r718[0]["suction_pressure_Pa"]
    return {
        "status":"M1_9_PRIMARY_SOURCE_MANUFACTURER_CONTROL_CROSSWALK_NOT_REAL_MAP",
        "primary_source_register":list(EVIDENCE),
        "source_discovery_requests":list(OUTREACH),
        "outreach_messages_sent":False,
        "outreach_reply_received":False,
        "source_manufacturer_endorsement_or_data_access":False,
        "r600_nominal_model_demand_vs_Sabroe_UniSAB_controller":rows,
        "number_of_scenario_r600_pressures_checked":len(rows),
        "HPC_HPO_R600_robust_controller_incompatibilities":sum(
            q["HPC_HPO_R600_documented_UniSAB_high_shutdown_comparison"][
                "model_robustly_exceeds_both_pressure_reference_interpretations"]
            for q in rows),
        "R718_2020_separate_rig_stage_ratio_check":ratio_results,
        "R718_2024_SINTEF_inlet_1_to_2bara_includes_model_stage1_0_25bara":
            100_000<=steam_initial<=200_000,
        "R718_model_first_stage_suction_Pa":steam_initial,
        "OST_2026_439_point_campaign_contains_pure_nbutane_by_table_1":False,
        "OST_2026_439_campaign_contains_any_full_M1_5_R600_machine_map":False,
        "target_R600_manufacturer_machine_map_accepted":False,
        "target_R718_manufacturer_machine_map_accepted":False,
        "all_process_and_TES_charge_demand_points_externally_rated":False,
        "source_pressure_reference_not_invented":True,
        "published_controller_shutdown_not_equivalent_to_equipment_design_pressure":True,
        "external_data_retrieval_or_author_reply_required_for_validation":True,
        "physical_hardware_qualified":False,
        "whole_service_1MW_qualified":False,
        "matched_service_Carnot_battery_RTE":None,
    }

def main()->None:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--requirements",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_9_primary_compressor_source_and_vendor_limit_audit.json"))
    args=p.parse_args()
    data=args.requirements.read_bytes()
    req=json.loads(data)
    report=audit_primary_machine_evidence(req)
    report["m1_4_model_demand_sha256"]=sha256(data).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("M1_9_EVIDENCE_CLASS",report["status"])
    print("M1_9_R600_MODEL_CASES",report["number_of_scenario_r600_pressures_checked"],
          "CONTROLLER_LIMIT_EXCEEDED",
          report["HPC_HPO_R600_robust_controller_incompatibilities"])
    print("M1_9_R718_RATIO_NEGATIVE_SCREEN",
          report["R718_2020_separate_rig_stage_ratio_check"])
    print("M1_9_R718_2024_SINTEF_1_2bar_INLET_OVERLAP",
          report["R718_2024_SINTEF_inlet_1_to_2bara_includes_model_stage1_0_25bara"])
    print("M1_9_MANUFACTURER_MAPS_ACQUIRED=False; MATCHED_SERVICE=False")

if __name__=="__main__":
    main()
