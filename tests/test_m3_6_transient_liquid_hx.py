"""M3.6 adverse original 1MW 110->150C gas-water-heat-exchanger tests.

All thermodynamic equipment states are SYNTHETIC hypotheses. Never count
assumed 2MPa water pressure or 40kW/K UA as actually installed equipment.
"""
import math
from dataclasses import replace
import pytest
pytest.importorskip("CoolProp")

from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.transient_liquid_hx import (
    TransientHXAssumptions,HXDynamicState,advance_transient_hx,
    eos_interpolation_check,
)
from carnot_battery_lab.physics.coupled_transient_process_loop import (
    CoupledHXTrial,simulate_coupled_transient_hx,
)

def _hx(**kw):
    return TransientHXAssumptions(**kw)

def _step(a=None,state=None,**kw):
    a=a or _hx()
    state=state or HXDynamicState.initial(a)
    x=dict(gas_inlet_mean_K=493.15,gas_flow_kg_s=15.,
           gas_cp_J_kgK=1005.,gas_density_kg_m3=2.5,
           water_flow_kg_s=1e6/(4180.*40.),
           water_inlet_K=383.15,dt_s=60.)
    x.update(kw)
    return advance_transient_hx(a,state,**x)

def test_dynamic_x_fluid_states_and_energy_ledger_at_cold_start():
    a=_hx()
    s=_step(a=a)
    assert len(s["state"].gas_cell_K)==8
    assert len(s["state"].water_cell_K)==8
    assert len(s["state"].wall_cell_K)==8
    assert s["water_outlet_start_K"]==pytest.approx(383.15)
    assert s["liquid_outlet_lower_than_required_at_start"]
    assert s["model_nominal_water_supply_and_1MW_in_step"] is False
    assert s["water_outlet_end_K"]>s["water_outlet_start_K"]
    assert s["net_boundary_gas_heat_into_HX_J"]>0.
    assert s["net_boundary_liquid_heat_from_HX_J"]>0.
    assert s["gas_holdup_change_J"]>0.
    assert s["wall_holdup_change_J"]>0.
    assert s["max_liquid_temperature_K_numerical_solver_nodes"]<480.
    assert s["numerical_integrator_steps"]>2
    for name in ("independent_gas_energy_residual_J",
                 "independent_wall_energy_residual_J",
                 "independent_water_energy_residual_J",
                 "overall_HX_energy_residual_J"):
        assert abs(s[name])<200.
    assert s["assumed_hx_pressure_pump_audit"]["assumed_model_liquid_single_phase"]
    assert s["water_actual_pressure_measured"] is False
    assert s["installed_UA_measured"] is False
    assert s["physically_qualified_1MW_liquid_process"] is False

def test_earlier_transient_hx_state_is_reused_not_reset():
    one=_step()
    two=_step(state=one["state"])
    assert two["water_outlet_start_K"]==one["water_outlet_end_K"]
    assert two["water_outlet_end_K"]>one["water_outlet_end_K"]

def test_cold_start_always_fails_first_minute_strict_contract():
    a=_hx()
    s=_step(a=a)
    assert s["liquid_outlet_lower_than_required_at_start"]
    assert not s["model_nominal_water_supply_and_1MW_in_step"]

def test_lower_UA_cannot_instantly_heat_process_water():
    base=_step()
    low=_step(a=_hx(installed_overall_UA_W_K=1000.))
    assert low["water_outlet_end_K"]<base["water_outlet_end_K"]

def test_real_eos_interpolation_error_is_bounded_against_original_CoolProp():
    r=eos_interpolation_check()
    assert r["water_pressure_Pa_ASSUMED"]==2e6
    assert r["property_lookup_does_not_extrapolate"]
    assert r["water_saturation_K"]>423.15
    for x in r["direct_EOS_comparison"]:
        assert abs(x["interpolated_enthalpy_minus_original_EOS_J_kg"])<15.
        assert abs(x["relative_cp_interpolation_error"])<1e-3

def test_low_assumed_water_pressure_cannot_be_a_150C_liquid():
    a=_hx(assumed_liquid_inlet_absolute_pressure_Pa=400000.)
    with pytest.raises(ValueError,match="insufficient"):
        _step(a=a)

def test_unknown_liquid_pressure_not_falsely_measured_after_success():
    out=_step()
    p=out["assumed_hx_pressure_pump_audit"]
    assert not p["measured_installed_pressure_or_pump_curve_available"]
    assert p["assumed_hx_water_pressure_drop_Pa_uncalibrated"]>0.
    assert p["assumed_hx_gas_pressure_drop_Pa_uncalibrated"]>0.
    assert p["assumed_min_liquid_pressure_Pa"]<2e6
    assert p["assumed_hx_liquid_pump_electric_W_uncalibrated"]>0. if "assumed_hx_liquid_pump_electric_W_uncalibrated" in p else p["assumed_liquid_hx_pump_electric_W_uncalibrated"]>0.

def test_null_saturated_water_phase_not_hidden_by_gas_grade():
    a=_hx(assumed_liquid_inlet_absolute_pressure_Pa=4e5)
    with pytest.raises(ValueError):
        _step(a=a,gas_inlet_mean_K=550.)

def test_wrong_hx_cells_or_invalid_equipment_fail_closed():
    with pytest.raises(ValueError):_hx(cells=1)
    with pytest.raises(ValueError):_hx(installed_overall_UA_W_K=-1.)
    with pytest.raises(ValueError):_hx(assumed_liquid_inlet_absolute_pressure_Pa=-1.)
    with pytest.raises(ValueError):_hx(assumed_auxiliary_efficiency=1.2)
    with pytest.raises(ValueError):_hx(wall_total_heat_capacity_J_K=0.)

def test_mismatch_between_state_and_dynamic_geometry_is_rejected():
    a=_hx(cells=4)
    with pytest.raises(ValueError,match="geometry"):
        _step(a=a,state=HXDynamicState.initial(_hx(cells=8)))

@pytest.mark.parametrize("kw",[
    {"gas_flow_kg_s":0.},{"water_flow_kg_s":-1.},
    {"water_inlet_K":0.},{"dt_s":-1.},
    {"gas_inlet_mean_K":float("nan")},
    {"gas_cp_J_kgK":0.},
])
def test_nonphysical_flows_and_boundary_inputs_cannot_start(kw):
    with pytest.raises(ValueError):
        _step(**kw)

def test_coupled_cold_initial_hx_has_unqualified_first_process_minute():
    trial=CoupledHXTrial(charge_duration_s=1200.,
                         process_duration_s=120.,transient_step_s=60.)
    r=simulate_coupled_transient_hx(GasRockBed(cells=8),trial)
    assert not r["model_only_thermal_duty_possible"]
    d=r["coupled_discharge_HX_energy"]
    assert d["first_failed_total_step_index"]==1
    assert r["whole_architecture_RTE"] is None
    assert not r["real_process_water_HX_qualified"]
    assert r["charging"]["model_charging_heat_J"]>0
    assert abs(d["bed_HX_gas_cooler_system_first_law_residual_J"])<500.
    assert d["qualified_real_1MW_process_water_J"]==0.
    assert len(r["sampled_thermocouple_like_model_trace_NOT_observations"])==2

def test_warmup_s_consumes_real_bed_heat_and_not_free_service():
    trial=CoupledHXTrial(charge_duration_s=1800.,
                         hx_warmup_duration_s=120.,
                         process_duration_s=120.,transient_step_s=60.)
    r=simulate_coupled_transient_hx(GasRockBed(cells=8),trial)
    rows=r["sampled_thermocouple_like_model_trace_NOT_observations"]
    assert len(rows)==4
    assert all(row["warmup_not_counted_for_process"] for row in rows[:2])
    assert all(not row["warmup_not_counted_for_process"] for row in rows[2:])
    assert r["coupled_discharge_HX_energy"][
        "warmup_liquid_energy_NOT_counted_as_process_J"]>0.
    assert r["coupled_discharge_HX_energy"][
        "sampled_model_thermal_grade_prefix_s"]<=120.
    assert abs(r["coupled_discharge_HX_energy"][
        "bed_HX_gas_cooler_system_first_law_residual_J"])<500.
    assert not r["physical_energy_service_qualified"]

def test_extra_uninstalled_cooler_load_is_derived_and_energy_balanced():
    trial=CoupledHXTrial(charge_duration_s=1800.,
                         process_duration_s=120.,transient_step_s=60.)
    r=simulate_coupled_transient_hx(GasRockBed(cells=8),trial)
    d=r["coupled_discharge_HX_energy"]
    qcond=d["gas_cooler_thermal_energy_required_J_uninstalled"]-d[
        "gas_reheater_thermal_energy_required_J_uninstalled"]
    assert d["bed_integrated_heat_to_gas_J"]==pytest.approx(
        d["HX_gas_boundary_energy_J"]+qcond,abs=200.)
    assert not d["actual_installed_UA_and_water_pressure_known"]
    assert r["whole_architecture_RTE"] is None

def test_non_original_service_even_if_easier_cannot_be_substituted():
    from carnot_battery_lab.physics.liquid_process_hx_gate import ProcessLiquidHXContract
    with pytest.raises(ValueError,match="1MW"):
        simulate_coupled_transient_hx(
            GasRockBed(cells=8),CoupledHXTrial(process_duration_s=60.),
            requested_process=ProcessLiquidHXContract(liquid_supply_C=140.))

def test_invalid_warmup_time_and_duration_rejected():
    with pytest.raises(ValueError):CoupledHXTrial(hx_warmup_duration_s=-10.)
    with pytest.raises(ValueError):CoupledHXTrial(hx_warmup_duration_s=61.)
    with pytest.raises(ValueError):CoupledHXTrial(process_duration_s=61.)
