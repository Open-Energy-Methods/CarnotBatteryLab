"""Standalone M3 thermal charge/discharge accounting: no industrial validation."""
import pytest
pytest.importorskip("scipy")
from dataclasses import replace
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed,BedState,advance_bed,bed_energy_J)
from carnot_battery_lab.physics.reverse_flow_discharge import (
    reverse_bed_state,advance_reverse_discharge,thermal_soc,
    thermal_exergy_change_J,CycleConditions,
    simulate_charge_discharge_cycle,simulate_repeated_cycles)


def bed(wall_UA=.0,cells=8):
    return GasRockBed(
        geometry=PackedBedGeometry(.4,.158,.02,.39),cells=cells,
        gas_density_kg_m3=1.,rock_density_kg_m3=3700.,
        rock_cp_J_kgK=1100.,ambient_K=303.15,
        wall_UA_W_K=wall_UA,blower_efficiency=.7)


def test_reversal_is_involution_with_exact_thermal_inventory():
    b=bed()
    s=BedState(tuple(float(300+i) for i in range(8)),
               tuple(float(350+2*i) for i in range(8)))
    t=reverse_bed_state(s)
    assert reverse_bed_state(t)==s
    assert bed_energy_J(b,s)==pytest.approx(bed_energy_J(b,t),abs=1e-7)


def test_discharge_matches_independent_reverse_state_advance_and_first_law():
    b=bed()
    s=BedState(tuple(360.+i for i in range(8)),
               tuple(385.+i for i in range(8)))
    direct=advance_bed(b,reverse_bed_state(s),
                       inlet_K=303.15,mass_flow_kg_s=.01,dt_s=30)
    discharge=advance_reverse_discharge(
        b,s,return_gas_K=303.15,mass_flow_kg_s=.01,
        dt_s=30,minimum_process_delivery_K=340.,
        dead_state_K=303.15)
    expected=reverse_bed_state(direct.final_state)
    assert discharge.final_state.fluid_temperature_K==pytest.approx(
        expected.fluid_temperature_K,abs=1e-7)
    assert discharge.final_state.solid_temperature_K==pytest.approx(
        expected.solid_temperature_K,abs=1e-7)
    assert discharge.signed_heat_to_process_gas_J==pytest.approx(
        -direct.heat_from_hot_gas_J,abs=1e-5)
    assert discharge.bed_energy_change_J<0
    assert discharge.signed_heat_to_process_gas_J>0
    assert discharge.qualified_process_heat_J>0
    assert abs(discharge.bed_first_law_residual_J)<.1
    assert discharge.fan_electric_J_model>0
    assert discharge.useful_heat_exergy_J>0


def test_unqualified_heat_not_misreported_as_process_service():
    b=bed()
    s=BedState.uniform(b,45.)
    r=advance_reverse_discharge(b,s,return_gas_K=303.15,
                                mass_flow_kg_s=.01,dt_s=45,
                                minimum_process_delivery_K=350.)
    assert r.signed_heat_to_process_gas_J>0
    assert r.qualified_process_heat_J==0
    assert r.rejected_grade_heat_J==pytest.approx(
        r.signed_heat_to_process_gas_J,rel=1e-8)


def test_zero_flow_is_rejected_as_no_service():
    with pytest.raises(ValueError,match="positive"):
        advance_reverse_discharge(bed(),BedState.uniform(bed(),80.),
            return_gas_K=303.15,mass_flow_kg_s=0,dt_s=30,
            minimum_process_delivery_K=350.)


def test_exergy_zero_if_process_inlet_equals_outlet():
    assert thermal_exergy_change_J(mass_flow_kg_s=.02,cp_J_kgK=1005.,
        dt_s=30,source_inlet_K=320,source_outlet_mean_K=320,
        dead_state_K=300)==pytest.approx(0.,abs=1e-8)


def test_soc_is_unclipped_and_keeps_state_reference_auditable():
    b=bed()
    assert thermal_soc(b,BedState.uniform(b,30.),
                       empty_temperature_K=303.15,
                       full_temperature_K=430.)==pytest.approx(0)
    assert thermal_soc(b,BedState.uniform(b,156.85),
                       empty_temperature_K=303.15,
                       full_temperature_K=430.)==pytest.approx(1.)
    # This value is outside the nominated reference full-charge state.
    assert thermal_soc(b,BedState.uniform(b,170.),
                       empty_temperature_K=303.15,
                       full_temperature_K=430.)>1


def test_synthetic_cycle_energy_audit_without_false_roundtrip():
    b=bed(wall_UA=.3)
    s=BedState.uniform(b,30.)
    cond=CycleConditions(charge_steps=8,discharge_steps=8,dt_s=30)
    r=simulate_charge_discharge_cycle(b,s,cond)
    assert r["charge_gas_thermal_input_J"]>0
    assert r["model_Ergun_blower_electric_J_not_calibrated"]>0
    assert abs(r["first_law_cycle_residual_J"])<.2
    assert r["thermal_round_trip_efficiency_claim"] is None
    assert r["electricity_round_trip_efficiency_claim"] is None
    assert len(r["discharge_trace"])==8
    assert r["physical_experiment_validation_pass"] is False


def test_repeated_cyclic_state_requires_independent_terminal_closure():
    b=bed(wall_UA=.2)
    cond=CycleConditions(charge_steps=5,discharge_steps=5,dt_s=30)
    r=simulate_repeated_cycles(
        b,BedState.uniform(b,30.),cond,cycles=2,
        cyclic_state_max_abs_K_threshold=1e-8)
    assert len(r["cycles"])==2
    assert r["nominal_cyclic_state_screen_pass"] is False
    assert r["system_round_trip_efficiency"] is None
    assert r["service_matching_established"] is False
    assert all(abs(c["first_law_cycle_residual_J"])<.2 for c in r["cycles"])


def test_invalid_service_threshold_rejected():
    with pytest.raises(ValueError,match="threshold"):
        advance_reverse_discharge(bed(),BedState.uniform(bed(),80.),
            return_gas_K=330.,mass_flow_kg_s=.01,dt_s=30,
            minimum_process_delivery_K=320.)
