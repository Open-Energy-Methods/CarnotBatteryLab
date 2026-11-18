"""M3.8 isolated controller and mass-energy EOS regression tests."""
import pytest
pytest.importorskip("CoolProp")
from carnot_battery_lab.physics.real_air_control_volume import AirVolumeState,advance_air_volume
from carnot_battery_lab.physics.process_gas_bypass_control import GasBypassControllerAssumptions,advance_hx_with_predictive_gas_bypass
from carnot_battery_lab.physics.transient_liquid_hx import TransientHXAssumptions,HXDynamicState,required_process_water_flow_from_real_enthalpy


def test_sealed_heating_changes_pressure_not_mass():
    s=AirVolumeState.from_TP(1.,383.15,250000.)
    a=advance_air_volume(s,duration_s=10.,heat_into_gas_W=5000.)
    assert a["final_mass_kg"]==pytest.approx(s.mass_kg)
    assert a["final"]["rho_kg_m3"]==pytest.approx(a["initial"]["rho_kg_m3"])
    assert a["final"]["T_K"]>383.15
    assert a["final"]["P_Pa"]>250000.
    assert a["final_internal_energy_J"]-s.internal_energy_J==pytest.approx(50000.,abs=.01)
    assert abs(a["energy_balance_residual_J"])<.1


def test_open_air_cell_uses_enthalpy_flow_work():
    s=AirVolumeState.from_TP(2.,383.15,250000.)
    r=advance_air_volume(s,duration_s=2.,inlet_mass_flow_kg_s=.10,
                         outlet_mass_flow_kg_s=.05,inlet_T_K=450.)
    assert r["final_mass_kg"]==pytest.approx(s.mass_kg+.1)
    assert abs(r["mass_balance_residual_kg"])<1e-8
    assert abs(r["energy_balance_residual_J"])<.1
    assert r["inlet_enthalpy_J"]>r["outlet_enthalpy_J"]
    assert not r["coupled_variable_density_packed_bed_HX_implemented"]


def test_inlet_outlet_same_state_and_mass_preserves_pressure_temperature():
    s=AirVolumeState.from_TP(2.,383.15,250000.)
    r=advance_air_volume(s,duration_s=5.,inlet_mass_flow_kg_s=.05,
                         outlet_mass_flow_kg_s=.05)
    assert r["final"]["T_K"]==pytest.approx(383.15,abs=.001)
    assert r["final"]["P_Pa"]==pytest.approx(250000.,abs=.1)


def test_exhausted_inventory_rejected():
    s=AirVolumeState.from_TP(1.,383.15,250000.)
    with pytest.raises(ValueError,match="exhausted"):
        advance_air_volume(s,duration_s=100.,outlet_mass_flow_kg_s=1.)


def test_terminal_objective_preserves_contract_and_rate_limit():
    hx=TransientHXAssumptions(cells=6)
    state=HXDynamicState.initial(hx)
    flow=required_process_water_flow_from_real_enthalpy()[
        "original_1MW_real_water_required_flow_kg_s"]
    cfg=GasBypassControllerAssumptions(objective="terminal_temperature",
                         maximum_fraction_rate_per_s=.4/60.)
    r=advance_hx_with_predictive_gas_bypass(
        cfg,hx,state,hot_gas_inlet_mean_K=493.15,
        gas_total_mass_flow_kg_s=15.,gas_cp_J_kgK=1005.,
        gas_density_kg_m3=2.5,water_mass_flow_kg_s=flow,
        water_inlet_K=383.15,dt_s=10.,
        previous_gas_through_fraction=.5)
    assert r["requested_objective_value"]==423.15
    assert r["maximum_allowed_fraction_change_this_step"]==pytest.approx(.4/6.)
    assert abs(r["selected_through_hx_gas_fraction"]-.5)<=.4/6.+1e-12
    assert r["interval_mean_thermal_duty_error_W"]==pytest.approx(
        r["interval_water_enthalpy_heating_W"]-1e6)
    assert not r["model_only_interval_nominal_150C_control_gate"]
    assert not r["actual_1MW_process_water_delivered_qualified"]


@pytest.mark.parametrize("kwargs",[{"objective":"fake"},{"maximum_fraction_rate_per_s":-1.}])
def test_bad_terminal_settings(kwargs):
    with pytest.raises(ValueError):GasBypassControllerAssumptions(**kwargs)
