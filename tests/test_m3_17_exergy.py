"""M3.17 exergy equations: unit identities + coupled numerical audit."""
import math
import pytest
from carnot_battery_lab.physics.exergy_audit import (
    LEDGER_KEYS,finite_nonnegative_transport,close_exergy_ledger)

def test_passive_thermal_entropy_nonnegative():
    for hot,cold in [(450.,300.),(330.,300.),(300.,330.)]:
        q=10.*(hot-cold)
        assert finite_nonnegative_transport(q,hot,cold)>=0
    assert finite_nonnegative_transport(0.,300.,300.)==0.
    with pytest.raises(ValueError):finite_nonnegative_transport(1.,0.,300.)

def test_heater_exergy_independent_state_balance():
    T0=300.; gasT=400.; electric=1000.
    D=electric*T0/gasT
    r=close_exergy_ledger(
        T0_K=T0,inventory_energy_change_J=electric,
        inventory_entropy_change_J_K=electric/gasT,
        heater_electric_J=electric,heater_to_gas_J=electric,
        blower_electric_J=0.,blower_to_gas_J=0.,
        process_heat_J=0.,product_entropy_change_J_K=0.,
        cooler_heat_J=0.,cooler_sink_K=380.,
        ambient_energy_by_temperature=[],identified_components_J={"heater":D})
    assert r["total_exergy_destruction_J"]==pytest.approx(D)
    assert r["unresolved_gas_hydraulics_and_numerical_exergy_J"]==pytest.approx(0.,abs=1e-9)
    assert r["exergy_entropy_closure_residual_J"]==pytest.approx(0.,abs=1e-9)

def test_zero_exergy_cooler_at_environment_and_constant_pressure_water():
    T0=298.15
    r=close_exergy_ledger(T0_K=T0,inventory_energy_change_J=-1000.,
       inventory_entropy_change_J_K=-1000./350.,
       heater_electric_J=0.,heater_to_gas_J=0.,blower_electric_J=0.,blower_to_gas_J=0.,
       process_heat_J=0.,product_entropy_change_J_K=0.,
       cooler_heat_J=1000.,cooler_sink_K=T0,
       ambient_energy_by_temperature=[],identified_components_J={})
    assert r["cooler_export_to_assumed_sink_exergy_J"]==0.
    assert r["total_exergy_destruction_J"]>=0.

def test_inconsistent_entropy_vs_energy_rejected():
    with pytest.raises(RuntimeError):
        close_exergy_ledger(T0_K=300.,inventory_energy_change_J=500.,
        inventory_entropy_change_J_K=1.,
        heater_electric_J=1000.,heater_to_gas_J=1000.,
        blower_electric_J=0.,blower_to_gas_J=0.,process_heat_J=0.,
        product_entropy_change_J_K=0.,cooler_heat_J=0.,cooler_sink_K=350.,
        ambient_energy_by_temperature=[],identified_components_J={})

def test_ledger_contract():
    assert len(LEDGER_KEYS)==10 and len(set(LEDGER_KEYS))==10

@pytest.mark.parametrize("use_loss,exergy_probe",[(False,False),(False,True),(True,True)])
def test_coupled_exergy_mass_energy_and_no_legacy_regression(use_loss,exergy_probe):
    pytest.importorskip("CoolProp");pytest.importorskip("numpy");pytest.importorskip("scipy")
    from dataclasses import replace
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    from carnot_battery_lab.physics.thermal_retention import MainHeatLoss
    c=ClosedCycle()
    c=replace(c,charge_s=80.,discharge_s=60.,train=replace(c.train,bed_cells=2,hx_cells=2))
    a=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=2,
            process_duty_W=1000.,cooler_cap_W=0.,exergy_audit=exergy_probe,
            main_heat_loss=MainHeatLoss(.6,.2,.2) if use_loss else None)
    for row in a["cycle_records"]:
        for phase in ("charge","discharge"):
            s=row[phase]
            assert abs(s["electrical_boundary_residual_J"])<.2
            if not exergy_probe:
                assert s["exergy_audit"] is None
                continue
            x=s["exergy_audit"]
            assert x is not None
            assert abs(x["exergy_entropy_closure_residual_J"])<.2
            assert x["electric_input_exergy_J"]==pytest.approx(s["heater_electric_J"]+s["blower_electric_J"])
            assert x["process_water_exergy_export_J"]==pytest.approx(0. if phase=="charge" else x["process_water_exergy_export_J"])
            assert x["total_entropy_generation_J_K"]>0.
            assert "gas_to_rock" in x["identified_exergy_destruction_J"]
            assert not x["allocation_is_complete"] and x["Carnot_battery_RTE"] is None

def test_exergy_probe_reference_temperature_guard():
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    with pytest.raises(ValueError):run_closed_cycle(ClosedCycle(),exergy_environment_K=0.)
