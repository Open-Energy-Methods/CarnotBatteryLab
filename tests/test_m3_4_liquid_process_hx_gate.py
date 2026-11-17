"""M3.4 independent gas/liquid HX thermodynamic necessity tests.

Every temperature, pressure and installed UA is a SYNTHETIC unit-test
assumption, not a verified plant design.
"""
from dataclasses import replace
import pytest
from carnot_battery_lab.physics.liquid_process_hx_gate import (
    ProcessLiquidHXContract,HXDomainError,
    minimum_saturated_water_pressure_Pa,
    screen_gas_to_liquid_hx_at_sample,screen_sampled_discharge_gas_to_liquid,
)

def test_water_nominal_1mw_110_to_150_requires_5_98kg_s():
    c=ProcessLiquidHXContract()
    assert abs(c.process_liquid_mass_flow_kg_s-5.980861244)<1e-6
    assert c.liquid_absolute_pressure_Pa is None
    assert c.installed_UA_W_K is None

def test_enthalpy_and_counterflow_terminal_temperatures():
    out=screen_gas_to_liquid_hx_at_sample(
        hot_gas_in_C=220.,hot_gas_mass_flow_kg_s=10.,
        hot_gas_cp_J_kgK=1000.)
    assert out["gas_out_after_full_required_heat_C"]==120.
    assert out["hot_in_minus_liquid_out_approach_K"]==70.
    assert out["hot_out_minus_liquid_in_approach_K"]==10.
    assert out["minimum_calculated_internal_counterflow_approach_K"]==10.
    assert out["thermodynamic_heat_and_pinch_necessary_condition"]
    assert out["status"]=="MODEL_THERMAL_POSSIBLE_LIQUID_PHASE_PRESSURE_UNKNOWN"
    assert out["1MW_industrial_process_liquid_service_qualified"] is False

def test_150C_liquid_requires_at_least_155C_gas_for_5K_pinch():
    r=screen_gas_to_liquid_hx_at_sample(
        hot_gas_in_C=151.,hot_gas_mass_flow_kg_s=100.,
        hot_gas_cp_J_kgK=1000.)
    assert r["status"]=="BLOCKED_HX_INTERNAL_PINCH_OR_INSUFFICIENT_GAS_ENTHALPY"
    assert not r["thermodynamic_heat_and_pinch_necessary_condition"]

def test_gas_200C_and_10kg_s_loses_too_much_temperature_at_1mw():
    r=screen_gas_to_liquid_hx_at_sample(
        hot_gas_in_C=200.,hot_gas_mass_flow_kg_s=10.,
        hot_gas_cp_J_kgK=1000.)
    assert r["gas_out_after_full_required_heat_C"]==100.
    assert r["hot_out_minus_liquid_in_approach_K"]==-10.
    assert r["required_counterflow_UA_W_K_if_thermodynamically_possible"] is None

def test_water_phase_requires_pressure_above_150C_saturation():
    p=minimum_saturated_water_pressure_Pa(150.)
    assert 4.5e5<p<5e5
    out=screen_gas_to_liquid_hx_at_sample(
        hot_gas_in_C=220.,hot_gas_mass_flow_kg_s=10.,
        hot_gas_cp_J_kgK=1000.,
        contract=ProcessLiquidHXContract(liquid_absolute_pressure_Pa=p*.9))
    assert out["status"]=="BLOCKED_PROCESS_WATER_NOT_CONFIRMED_LIQUID"

def test_unknown_installed_UA_not_claimed_and_assumed_UA_can_fail():
    c=ProcessLiquidHXContract(liquid_absolute_pressure_Pa=7e5)
    kw={"hot_gas_in_C":220.,"hot_gas_mass_flow_kg_s":10.,
        "hot_gas_cp_J_kgK":1000.}
    out=screen_gas_to_liquid_hx_at_sample(**kw,contract=c)
    assert out["status"]=="MODEL_THERMAL_POSSIBLE_INSTALLED_UA_UNKNOWN"
    assert out["actual_water_liquid_phase_at_process_supply_confirmed"]
    low=screen_gas_to_liquid_hx_at_sample(
        **kw,contract=replace(c,installed_UA_W_K=1000.))
    assert low["status"]=="BLOCKED_ASSUMED_INSTALLED_UA_INSUFFICIENT"
    high=screen_gas_to_liquid_hx_at_sample(
        **kw,contract=replace(c,installed_UA_W_K=100000.))
    assert high["status"]=="MODEL_ONLY_ASSUMED_COUNTERFLOW_HX_PASSES_NOT_PLANT_QUALIFIED"
    assert not high["1MW_industrial_process_liquid_service_qualified"]

def test_discharge_three_temperatures_block_when_one_drops_below_liquid_grade():
    row={"first_process_gas_out_K":424.15,
         "mean_process_gas_out_K":453.15,
         "end_process_gas_out_K":413.15}
    out=screen_sampled_discharge_gas_to_liquid(
        discharge_steps=[row],gas_mass_flow_kg_s=25.,
        gas_cp_J_kgK=1005.)
    assert not out["all_samples_necessary_thermal_gate"]
    assert out["status"]=="NO_FULL_GRADE_LIQUID_PROCESS_HX_AT_SAMPLED_DISCHARGE_STATES"
    assert not out["actual_process_liquid_heat_delivered_qualified"]

def test_positive_samples_cannot_claim_continuous_or_industrial_delivery():
    row={"first_process_gas_out_K":523.15,
         "mean_process_gas_out_K":503.15,
         "end_process_gas_out_K":513.15}
    out=screen_sampled_discharge_gas_to_liquid(
        discharge_steps=[row],gas_mass_flow_kg_s=25.,
        gas_cp_J_kgK=1005.)
    assert out["all_samples_necessary_thermal_gate"]
    assert out["status"]=="MODEL_ONLY_ALL_SAMPLES_PASSED_BUT_CONTINUOUS_UNVERIFIED"
    assert out["between_sample_temperature_minimum_unverified"]
    assert out["matched_architecture_efficiency"] is None

@pytest.mark.parametrize("args",[
    {"thermal_duty_W":-1.},{"liquid_return_C":160.},
    {"liquid_cp_J_kgK":0.},{"minimum_internal_approach_K":0.},
    {"installed_UA_W_K":-1.},{"liquid_absolute_pressure_Pa":-2.},
])
def test_bad_liquid_process_parameters_fail_closed(args):
    with pytest.raises(HXDomainError):ProcessLiquidHXContract(**args)

def test_cannot_implicitly_claim_measured_UA_without_value():
    with pytest.raises(HXDomainError,match="measured UA"):
        ProcessLiquidHXContract(installed_UA_is_measured=True)

def test_missing_discharge_sample_cannot_be_imputed():
    with pytest.raises(HXDomainError,match="missing"):
        screen_sampled_discharge_gas_to_liquid(
            discharge_steps=[{"first_process_gas_out_K":500.}],
            gas_mass_flow_kg_s=25.,gas_cp_J_kgK=1005.)
