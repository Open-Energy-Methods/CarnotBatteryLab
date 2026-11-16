"""Source/units and fail-closed manufacturer-document evidence tests.

All fixtures synthetic model-demand *requests*, never manufacturer maps.
"""
from copy import deepcopy
import pytest
from scripts.audit_m1_9_manufacturer_map_sources import (
    audit_primary_machine_evidence,_pressure_bar_cases,EVIDENCE,OUTREACH,
    SABROE_NOTE30_URL,
)


def _stage(fluid="R600 n-butane",pressure=4e6,ratio=5.6):
    low=pressure/ratio
    return {
        "refrigerant":fluid,"stage":"single_stage",
        "suction_pressure_Pa":low,
        "discharge_pressure_Pa":pressure,
        "stage_pressure_ratio":ratio,
        "suction_temperature_C":75.,
        "discharge_temperature_C":170.,
        "suction_volumetric_flow_m3_s":.21,
    }


def _req():
    direct=[
        {"stage":"stage1","stage_pressure_ratio":4.6587,
         "suction_pressure_Pa":25042.,
         "suction_temperature_C":75.},
        {"stage":"stage2","stage_pressure_ratio":4.6587,
         "suction_pressure_Pa":116662.,
         "suction_temperature_C":114.},
    ]
    pressures=(4e6,4.5e6,5e6,5.5e6,6e6)
    scan={str(int(x)):{"compressor_stage_demands":[_stage(pressure=x)]}
          for x in pressures}
    return {
        "evidence_status":
            "M1_4_SCIENTIFIC_REQUIREMENTS_AND_LITERATURE_CROSSWALK_ONLY",
        "equipment_qualified":False,
        "input_contract":{
            case:{
                "source_inlet_C":80.,"source_outlet_C":70.,
                "process_return_C":110.,"process_supply_C":150.,
            } for case in ("r718","r600")
        },
        "r718_80C_source_110_150C_direct_liquid_screen":{
            "compressor_stage_demands":direct,
        },
        "r600_80C_source_110_150C_transcritical_screen":{
            "map_requirements_for_numerically_feasible_points":scan,
        },
    }


def test_original_h_ref_r600_above_sabroe_hpc_hpo_reduced_R600_control_limit():
    r=audit_primary_machine_evidence(_req())
    assert r["number_of_scenario_r600_pressures_checked"]==5
    assert r["HPC_HPO_R600_robust_controller_incompatibilities"]==5
    assert all(
        x["HPC_HPO_R600_documented_UniSAB_high_shutdown_comparison"][
            "model_robustly_exceeds_both_pressure_reference_interpretations"]
        for x in r["r600_nominal_model_demand_vs_Sabroe_UniSAB_controller"])
    assert r["physical_hardware_qualified"] is False
    assert r["matched_service_Carnot_battery_RTE"] is None


def test_r718_two_stage_specific_other_test_rig_peaks_not_map():
    out=audit_primary_machine_evidence(_req())
    values=out["R718_2020_separate_rig_stage_ratio_check"]
    assert len(values)==2
    assert [x["SINTEF_2020_other_rig_reported_individual_peak_ratio"]
            for x in values]==[2.4,2.]
    assert all(x["demand_exceeds_different_rig_individual_peak_ratio"]
               for x in values)
    assert out["R718_2024_SINTEF_inlet_1_to_2bara_includes_model_stage1_0_25bara"] is False
    assert out["target_R718_manufacturer_machine_map_accepted"] is False


def test_pressure_reference_units_are_not_silently_equated():
    # 36 bar manufacturer high shutdown: hypothetical 36.9 bara target
    # exceeds 36 bara but does not exceed 36 barg @ 1.01325 bara.
    row=_pressure_bar_cases(_stage(pressure=3.69e6),36.)
    assert row["model_above_control_shutdown_if_published_bar_is_absolute"]
    assert not row[
        "model_above_control_shutdown_if_published_bar_is_gauge_with_nominal_atmosphere"]
    assert not row["model_robustly_exceeds_both_pressure_reference_interpretations"]
    assert row["control_setting_mechanical_design_rating"] is False


def test_hpx_general_setting_does_not_imply_approved_r600_machine():
    r=audit_primary_machine_evidence(_req())
    hp=[x["HPX_65bar_design_GENERIC_not_R600_specific_comparison"]
        for x in r["r600_nominal_model_demand_vs_Sabroe_UniSAB_controller"]]
    assert hp[0]["manufacturer_controller_source_value_bar_UNSPECIFIED_REF"]==57.5
    assert not hp[0]["model_robustly_exceeds_both_pressure_reference_interpretations"]
    assert hp[-1]["model_robustly_exceeds_both_pressure_reference_interpretations"]
    assert all(not p["R600_approval_and_full_performance_map_validated"]
               for p in hp)


def test_439_measured_global_experimental_points_cannot_be_pure_r600():
    r=audit_primary_machine_evidence(_req())
    ost=[x for x in EVIDENCE if x["id"]==
         "brendel_2026_439_experimental_not_R600"][0]
    assert ost["total_published_observations_all_fluids"]==439
    assert ost["pure_r600_observations_reported_in_table_1"]==0
    assert not r["OST_2026_439_point_campaign_contains_pure_nbutane_by_table_1"]
    assert not r["OST_2026_439_campaign_contains_any_full_M1_5_R600_machine_map"]


def test_sources_and_contact_provenance_not_mislabeled_as_data_received():
    r=audit_primary_machine_evidence(_req())
    assert len(EVIDENCE)==6
    assert len(OUTREACH)==4
    assert all(x["source_url"].startswith("https://") for x in EVIDENCE)
    assert all(x["contact_source"].startswith("https://") for x in OUTREACH)
    assert SABROE_NOTE30_URL==EVIDENCE[0]["source_url"]
    assert r["outreach_messages_sent"] is False
    assert r["outreach_reply_received"] is False
    assert r["source_manufacturer_endorsement_or_data_access"] is False


@pytest.mark.parametrize("change",[
    lambda x:x.update({"evidence_status":"M1_5_MACHINE_ACCEPTED"}),
    lambda x:x.update({"equipment_qualified":True}),
    lambda x:x["input_contract"]["r718"].update({"source_outlet_C":75.}),
    lambda x:x["input_contract"]["r600"].update({"process_supply_C":160.}),
    lambda x:x["r600_80C_source_110_150C_transcritical_screen"].update({
        "map_requirements_for_numerically_feasible_points":{}}),
])
def test_changed_scientific_basis_cannot_become_positive_vendor_evidence(change):
    d=_req()
    change(d)
    with pytest.raises(ValueError):
        audit_primary_machine_evidence(d)


def test_scan_pressure_key_mismatch_rejected():
    d=_req()
    d["r600_80C_source_110_150C_transcritical_screen"][
        "map_requirements_for_numerically_feasible_points"]["4000000"][
            "compressor_stage_demands"][0]["discharge_pressure_Pa"]=5e6
    with pytest.raises(ValueError,match="stage pressure"):
        audit_primary_machine_evidence(d)


def test_other_machine_stage_ratio_not_clipped_or_renamed_as_compliance():
    d=_req()
    d["r718_80C_source_110_150C_direct_liquid_screen"][
        "compressor_stage_demands"][0]["stage_pressure_ratio"]=2.2
    out=audit_primary_machine_evidence(d)
    assert not out["R718_2020_separate_rig_stage_ratio_check"][0][
        "demand_exceeds_different_rig_individual_peak_ratio"]
    assert out["target_R718_manufacturer_machine_map_accepted"] is False
