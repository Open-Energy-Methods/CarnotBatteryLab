"""M3.5 source-independent TES + gas-to-liquid HX evidence tests.

All gas loops, heater limits and fields below are deliberately SYNTHETIC.
No empirical heat-pump map, 1MW plant validation or RTE is claimed.
"""
from dataclasses import replace
import math
import pytest

pytest.importorskip("CoolProp")

from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.liquid_process_hx_gate import ProcessLiquidHXContract
from carnot_battery_lab.physics.independent_thermal_envelope import (
    IndependentThermalCase,simulate_independent_case,study_envelope,_steps,
)
from scripts.run_m3_5_independent_thermal_service_envelope import (
    declared_scenarios,compact_run_result,
)


def _case(**kw):
    x=dict(name="synthetic-test-only",charge_hot_gas_C=220.,
           charge_mass_flow_kg_s=25.,charge_duration_s=240.,
           discharge_mass_flow_kg_s=15.,discharge_duration_s=600.,
           integration_step_s=300.,initial_bed_C=95.,
           discharge_return_gas_C=110.,heater_max_electric_W=4.5e6,
           assumed_resistance_efficiency=1.)
    x.update(kw)
    return IndependentThermalCase(**x)


def test_declared_experiment_grid_frozen_and_independent_of_compressor_maps():
    cases=declared_scenarios()
    assert len(cases)==9
    assert len({c.name for c in cases})==len(cases)
    assert min(c.charge_duration_s for c in cases)==240.
    assert max(c.charge_duration_s for c in cases)==28800.
    assert {c.discharge_duration_s for c in cases}=={3600.,7200.}
    assert {c.charge_hot_gas_C for c in cases}=={150.,180.,220.,260.}
    assert all(c.initial_bed_C==95. for c in cases)
    assert all(c.discharge_return_gas_C==110. for c in cases)


def test_fractional_charge_step_fully_integrated_no_missing_time():
    s=list(_steps(650.,300.))
    assert s==[300.,300.,50.]
    assert sum(_steps(240.,600.))==240.
    assert list(_steps(600.,300.))==[300.,300.]


def test_150C_source_cannot_heat_water_to_150C_across_finite_5K_pinch():
    out=simulate_independent_case(GasRockBed(cells=8),
                                  _case(charge_hot_gas_C=150.))
    assert out["status"]=="PRECHARGE_PHYSICAL_NECESSARY_CONDITION_BLOCKED"
    assert out["blocker"]=="SOURCE_TEMPERATURE_BELOW_MINIMUM_PROCESS_HOT_TERMINAL"
    assert not out["charge_model_executed"]
    assert not out["nominal_full_duty_discharge_duration_screened"]
    assert out["actual_industrial_process_heat_qualified_J"]==0.


def test_180C_source_with_15kg_s_fails_cold_110C_water_terminal_at_1MW():
    out=simulate_independent_case(GasRockBed(cells=8),
                                  _case(charge_hot_gas_C=180.))
    assert out["status"]=="PRECHARGE_PHYSICAL_NECESSARY_CONDITION_BLOCKED"
    assert out["blocker"]=="SOURCE_TEMPERATURE_AND_DISCHARGE_FLOW_CANNOT_SUPPLY_1MW_WITH_FINITE_PINCH"
    assert out["optimistic_max_hot_gas_source_temperature_hx_gate_pass"] is False
    assert not out["charge_model_executed"]


def test_initial_heater_limit_hard_blocked_not_bypassed_by_integrating_long_time():
    r=simulate_independent_case(GasRockBed(cells=8),
                                 _case(heater_max_electric_W=1.e5))
    assert r["status"]=="PRECHARGE_PHYSICAL_NECESSARY_CONDITION_BLOCKED"
    assert r["blocker"]=="ASSUMED_HEATER_INITIAL_POWER_OVER_DECLARED_LIMIT"
    assert not r["charge_model_executed"]


def test_wakao_packed_bed_model_out_of_domain_hard_rejected():
    r=simulate_independent_case(GasRockBed(cells=8),
                  _case(discharge_mass_flow_kg_s=300.))
    assert r["blocker"]=="WAKAO_HEAT_TRANSFER_CORRELATION_OUTSIDE_RE_DOMAIN"
    assert not r["discharge_model_executed"]


def test_short_charge_records_bed_and_gas_energy_conservation_without_heat_claim():
    r=simulate_independent_case(GasRockBed(cells=8),_case())
    assert r["charge_model_executed"]
    assert r["discharge_model_executed"]
    assert not r["R600_R718_compressor_dependencies_used"]
    assert r["installed_process_liquid_hx_qualified"] is False
    assert r["simulated_process_heat_delivered_J"] is None
    assert r["actual_industrial_process_heat_qualified_J"]==0.
    assert r["architecture_or_electrical_round_trip_efficiency"] is None
    c=r["charging"]
    d=r["discharge"]
    assert c["total_model_heat_put_into_bed_from_source_gas_J"]>0.
    assert c["model_charge_heater_electricity_J_not_real_plant"]==pytest.approx(
        c["total_model_heat_put_into_bed_from_source_gas_J"])
    assert c["sampled_peak_electric_heater_power_W"]<4.5e6
    assert c["max_predicted_Ergun_charge_bed_pressure_drop_Pa_uncalibrated"]>0.
    assert d["model_discharge_max_bed_pressure_drop_Pa_Ergun_uncalibrated"]>0.
    assert abs(c["charge_integrated_first_law_residual_J"])<100.
    assert abs(d["combined_storage_first_law_residual_J"])<100.
    assert r["screened_full_duty_prefix_duration_s"]<=600.
    assert len(d["sampled_intervals"])==2


def test_loss_bearing_heater_eta_strictly_increases_model_electricity():
    b=GasRockBed(cells=8)
    reference=simulate_independent_case(b,_case())
    modified=simulate_independent_case(b,_case(
        assumed_resistance_efficiency=.8))
    assert modified["charging"][
        "model_charge_heater_electricity_J_not_real_plant"]==pytest.approx(
            reference["charging"][
                "model_charge_heater_electricity_J_not_real_plant"]/.8)
    assert modified["charging"][
        "total_model_heat_put_into_bed_from_source_gas_J"]==pytest.approx(
            reference["charging"][
                "total_model_heat_put_into_bed_from_source_gas_J"])
    assert not modified["matched_1MW_service_empirically_qualified"]


def test_positive_necessary_screen_from_artificially_preheated_small_bed():
    # Synthetic positive branch; initialization at 240C is itself a large
    # EXTERNALLY ASSUMED energy inventory, not an actual 95C charging result.
    g=PackedBedGeometry(length_m=.5,diameter_m=3.,
                        particle_diameter_m=.045,porosity=.4)
    b=GasRockBed(geometry=g,cells=12)
    scenario=_case(initial_bed_C=240.,charge_hot_gas_C=260.,
                   charge_duration_s=180.,discharge_duration_s=30.,
                   integration_step_s=30.)
    r=simulate_independent_case(b,scenario)
    assert r["nominal_full_duty_discharge_duration_screened"]
    assert r["screened_full_duty_prefix_duration_s"]==30.
    assert r["status"]=="MODEL_ONLY_FULL_DURATION_GAS_TO_LIQUID_NECESSARY_GATE"
    assert r["discharge"]["maximum_required_counterflow_UA_W_K_across_eligible_steps"]>0.
    assert r["discharge"]["max_interval_mean_additional_gas_cooler_thermal_W_if_1MW"]>0.
    assert r["missing_pressurised_liquid_water_pressure"]
    assert r["additional_gas_cooler_or_loop_balance_required"]
    assert not r["matched_1MW_service_empirically_qualified"]
    assert r["actual_industrial_process_heat_qualified_J"]==0.


def test_no_cooling_source_implied_to_be_installed_or_compressor_validated():
    r=simulate_independent_case(GasRockBed(cells=8),_case())
    assert r["working_gas_absolute_pressure_Pa"] is None
    assert not r["fluid_and_solid_calibration_from_experiment"]
    assert not r["actual_charge_heater_vendor_rating_verified"]
    assert r["model_only_compressor_independent_screen"]
    assert r["R600_R718_compressor_dependencies_used"] is False


@pytest.mark.parametrize("kw",[
    {"name":""},
    {"charge_mass_flow_kg_s":0.},
    {"charge_duration_s":-1.},
    {"charge_hot_gas_C":-300.},
    {"charge_hot_gas_C":90.},
    {"heater_max_electric_W":0.},
    {"assumed_resistance_efficiency":1.1},
    {"discharge_duration_s":float("nan")},
    {"integration_step_s":0.},
    {"discharge_mass_flow_kg_s":True},
    {"initial_bed_C":-300.},
    {"discharge_return_gas_C":80.},
])
def test_invalid_hypothesis_rejected(kw):
    with pytest.raises(ValueError):_case(**kw)


def test_cannot_morph_frozen_service_to_less_demanding_temperature():
    with pytest.raises(ValueError,match="original 1MW"):
        simulate_independent_case(
            GasRockBed(cells=8),_case(),
            contract=ProcessLiquidHXContract(liquid_supply_C=140.))


def test_duplicate_case_names_and_empty_case_grid_are_rejected():
    b=GasRockBed(cells=8)
    with pytest.raises(ValueError,match="unique"):
        study_envelope(b,[_case(),_case()])
    with pytest.raises(ValueError,match="1–50"):
        study_envelope(b,[])


def test_compact_model_report_never_promotes_possible_to_empirical_qualification():
    r=simulate_independent_case(GasRockBed(cells=8),_case())
    row=compact_run_result(r)
    assert row["actual_industrial_service_qualified"] is False
    assert row["requested_process_duration_h"]==pytest.approx(600./3600.)
    assert row["max_model_charge_Ergun_dP_kPa_UNCALIBRATED"]>0.
