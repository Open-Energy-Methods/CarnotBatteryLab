"""M3.7 adversarial tests: uninstalled gas bypass and CoolProp Air EOS.

Everything numerical. Synthetic initial thermal states NEVER constitute
measured process-heat delivery or source-compatible pressure qualification.
"""
from dataclasses import replace
import math
import pytest
pytest.importorskip("CoolProp")

from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.transient_liquid_hx import (
    HXDynamicState,TransientHXAssumptions,
    required_process_water_flow_from_real_enthalpy,
)
from carnot_battery_lab.physics.process_gas_bypass_control import (
    GasBypassControllerAssumptions,advance_hx_with_predictive_gas_bypass,
)
from carnot_battery_lab.physics.coupled_transient_process_loop import (
    CoupledHXTrial,simulate_coupled_transient_hx,
)
from carnot_battery_lab.physics.air_eos_sensitivity import (
    air_state,air_gas_loop_property_sensitivity,
)


def _step(*,state=None,settings=None,previous_fraction=1.,
          gas_inlet_C=220.,mass_flow=15.):
    hx=TransientHXAssumptions(cells=6)
    if state is None:
        state=HXDynamicState.initial(hx)
    flow=required_process_water_flow_from_real_enthalpy()[
        "original_1MW_real_water_required_flow_kg_s"]
    return advance_hx_with_predictive_gas_bypass(
        settings or GasBypassControllerAssumptions(),
        hx,state,
        hot_gas_inlet_mean_K=gas_inlet_C+273.15,
        gas_total_mass_flow_kg_s=mass_flow,gas_cp_J_kgK=1005.,
        gas_density_kg_m3=2.5,water_mass_flow_kg_s=flow,
        water_inlet_K=383.15,dt_s=60.,
        previous_gas_through_fraction=previous_fraction)


def test_cold_start_gas_valve_cannot_immediately_claim_150C_water():
    out=_step()
    assert out["gas_mass_balance_residual_kg_s"]==pytest.approx(0,abs=1e-12)
    assert out["hx_step"]["water_outlet_start_K"]==pytest.approx(383.15)
    assert out["min_accepted_node_water_outlet_C"]==pytest.approx(110.)
    assert out["model_only_interval_nominal_150C_control_gate"] is False
    assert not out["real_valve_and_control_equipment_qualified"]
    assert not out["actual_1MW_process_water_delivered_qualified"]
    assert out["trial_q_at_full_fraction_W"]>0


def test_explicit_full_gas_startup_is_debited_and_never_certified():
    hx=TransientHXAssumptions(cells=6)
    flow=required_process_water_flow_from_real_enthalpy()[
        "original_1MW_real_water_required_flow_kg_s"]
    settings=GasBypassControllerAssumptions(startup_full_flow_seconds=120.)
    out=advance_hx_with_predictive_gas_bypass(
        settings,hx,HXDynamicState.initial(hx),
        hot_gas_inlet_mean_K=493.15,gas_total_mass_flow_kg_s=15.,
        gas_cp_J_kgK=1005.,gas_density_kg_m3=2.5,
        water_mass_flow_kg_s=flow,water_inlet_K=383.15,
        dt_s=60.,elapsed_discharge_time_s=0.)
    assert out["model_only_gas_bypass_control_status"]==(
        "STARTUP_FULL_HOT_GAS_FLOW_NO_PROCESS_CREDIT")
    assert out["selected_through_hx_gas_fraction"]==1.
    assert out["bypassed_gas_mass_flow_kg_s"]==0.
    assert out["number_of_ODE_trial_solves_including_monotonicity"]==1
    assert not out["model_only_interval_nominal_150C_control_gate"]
    assert not out["actual_1MW_process_water_delivered_qualified"]


def test_valve_fraction_sums_to_exact_original_gas_mass_flow():
    o=_step()
    f=o["selected_through_hx_gas_fraction"]
    assert .1<=f<=1.
    assert o["through_hx_gas_mass_flow_kg_s"]==pytest.approx(f*15.)
    assert o["bypassed_gas_mass_flow_kg_s"]==pytest.approx((1-f)*15.)
    assert o["through_hx_gas_mass_flow_kg_s"]+o[
        "bypassed_gas_mass_flow_kg_s"]==pytest.approx(15.)


def test_cannot_control_to_easier_than_exact_original_1MW_contract():
    hx=TransientHXAssumptions(cells=6)
    with pytest.raises(ValueError,match="1MW"):
        _step(settings=GasBypassControllerAssumptions(
            interval_mean_duty_target_W=900_000.))


def test_outlet_gas_slew_cap_cannot_be_silently_ignored():
    x=_step(settings=GasBypassControllerAssumptions(
        maximum_fraction_step_change=.01),previous_fraction=.10)
    assert x["selected_through_hx_gas_fraction"]<=.11+1e-12
    assert abs(x["gas_mass_balance_residual_kg_s"])<1e-10
    assert not x["real_valve_and_control_equipment_qualified"]


def test_controller_actual_hx_state_has_energy_closure_for_each_candidate():
    x=_step()
    h=x["hx_step"]
    for key in ("independent_gas_energy_residual_J",
                "independent_water_energy_residual_J",
                "independent_wall_energy_residual_J",
                "overall_HX_energy_residual_J"):
        assert abs(h[key])<500
    assert h["water_outlet_flow_average_heat_W"]==pytest.approx(
        x["interval_water_enthalpy_heating_W"])
    assert x["number_of_ODE_trial_solves_including_monotonicity"]>=5
    assert not x["true_continuous_150C_control_certified"]


def test_gas_bypass_coupled_to_entire_bed_hx_cooler_conserves_energy():
    trial=CoupledHXTrial(charge_duration_s=1800.,
        hx_warmup_duration_s=120.,process_duration_s=120.,
        transient_step_s=60.)
    r=simulate_coupled_transient_hx(
        GasRockBed(cells=8),trial,
        gas_bypass_controller=GasBypassControllerAssumptions())
    assert r["model_only_hypothetical_gas_bypass_control"]["enabled"]
    assert not r["physical_energy_service_qualified"]
    assert r["whole_architecture_RTE"] is None
    d=r["coupled_discharge_HX_energy"]
    assert abs(d["bed_HX_gas_cooler_system_first_law_residual_J"])<500.
    for row in r["sampled_thermocouple_like_model_trace_NOT_observations"]:
        ctl=row["assumed_model_predictive_gas_bypass_control"]
        assert ctl is not None
        assert abs(ctl["mass_balance_residual_kg_s"])<1e-8
        assert 0.<=ctl["bypassed_fraction"]<1
        assert not ctl["real_valve_qualified"]


@pytest.mark.parametrize("change",[
    {"minimum_hx_gas_fraction":0.},
    {"minimum_hx_gas_fraction":1.},
    {"maximum_fraction_step_change":2.},
    {"interval_mean_duty_target_W":-10.},
    {"permitted_nodal_water_outlet_error_K":float("nan")},
    {"maximum_bisection_steps":0},
    {"startup_full_flow_seconds":-1.},
])
def test_invalid_controller_settings_fail_closed(change):
    with pytest.raises(ValueError):GasBypassControllerAssumptions(**change)


def test_air_eos_cp_enthalpy_and_density_change_with_temperature():
    low=air_state(383.15,250000.)
    high=air_state(533.15,250000.)
    assert low["density_kg_m3"]>high["density_kg_m3"]
    assert high["specific_enthalpy_J_kg"]>low["specific_enthalpy_J_kg"]
    assert high["cp_J_kgK"]>low["cp_J_kgK"]*.99
    assert low["prandtl_from_EOS"]>0
    assert high["dynamic_viscosity_Pa_s"]>low["dynamic_viscosity_Pa_s"]
    assert not high["real_gas_loop_pressure_measured"]


def test_air_eos_pressure_sensitivity_not_a_fake_actual_pressure():
    a=air_state(473.15,101325.)
    b=air_state(473.15,500000.)
    assert b["density_kg_m3"]>a["density_kg_m3"]
    x=air_gas_loop_property_sensitivity(
        assumed_pressures_Pa=(101325.,250000.,500000.))
    assert x["original_model_gas_absolute_pressure_Pa"] is None
    assert x["temperature_dependent_dry_air_properties_evaluated"]
    assert not x["variable_density_or_cp_implemented_in_Carnot_bed"]
    assert not x["variable_density_or_cp_implemented_in_coupled_HX"]
    assert x["architecture_round_trip_efficiency"] is None
    assert len(x["pressure_scenarios"])==3
    r=x["pressure_scenarios"][1]["pointwise_states"]["260.0"]
    assert r["eos_bed_ergun_pressure_drop_Pa_uncalibrated"]>0
    assert r["gas_bed_EOS_mass_energy_hydraulic_closure_qualified"] is False


@pytest.mark.parametrize("T,P",[(280.,250000.),(700.,250000.),
                                (423.15,0.),(423.15,3000000.)])
def test_air_eos_outside_declared_property_domain_fails(T,P):
    with pytest.raises(ValueError):air_state(T,P)
