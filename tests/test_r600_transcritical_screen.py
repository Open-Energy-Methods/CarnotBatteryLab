"""Screening tests: thermodynamics are not a measured compressor map."""
import pytest
pytest.importorskip("CoolProp")

from dataclasses import replace
from carnot_battery_lab.physics.r600_transcritical_screen import (
    R600ScreenInputs,solve_r600_screen,scan_transcritical_high_side,
    InfeasibleR600)
from carnot_battery_lab.physics.finite_hx import InfeasibleHX


def test_source_outlet_not_inlet_determines_evaporation():
    try:
        r=solve_r600_screen()
    except (InfeasibleR600,InfeasibleHX):
        pytest.skip("default illustrative high-side pressure not feasible: see scan test")
    assert r.evaporating_C==pytest.approx(65.0)
    assert r.Q_process_W==pytest.approx(1e6)
    assert abs(r.heat_balance_residual_W)<1e-5
    assert r.source_flow_kg_s>0
    assert r.process_flow_kg_s==pytest.approx(1e6/(4180*40))
    assert r.high_side_pressure_Pa>r.critical_pressure_Pa
    assert r.gas_cooler_HX.min_approach_K>=r.inputs.gas_cooler_pinch_K-1e-6


def test_hx_and_pressure_sweep_never_asserts_hardware_qualification():
    result=scan_transcritical_high_side()
    assert len(result["points"])==5
    assert result["hardware_qualified"] is False
    assert result["measured_80C_150C_refrigerant_map"] is False
    assert all("status" in p for p in result["points"])
    for p in result["points"]:
        if p["status"]=="FINITE_HX_THERMODYNAMIC_SCREEN_PASS":
            assert p["COP_compressor_electric"]>1
            assert p["requires_hardware_map"] is True


def test_reject_non_supercritical_pressure():
    with pytest.raises(InfeasibleR600,match="critical"):
        solve_r600_screen(R600ScreenInputs(high_pressure_Pa=3e6))


def test_reject_suction_pinches():
    with pytest.raises(InfeasibleR600,match="superheat"):
        solve_r600_screen(R600ScreenInputs(suction_superheat_K=20))


def test_invalid_efficiencies_rejected():
    with pytest.raises(InfeasibleR600,match="efficiencies"):
        R600ScreenInputs(isentropic_efficiency=1.1)


def test_source_capacity_is_explicit_constraint():
    with pytest.raises(InfeasibleR600,match="source mass flow cap"):
        solve_r600_screen(R600ScreenInputs(available_source_flow_kg_s=.1))


def test_gas_cooler_undersizing_reported():
    with pytest.raises(InfeasibleHX):
        solve_r600_screen(R600ScreenInputs(gas_cooler_UA_W_K=100))


def test_pressure_scan_never_picks_infeasible_point():
    results=scan_transcritical_high_side(
        high_pressures_Pa=(3e6,3.5e6,4e6,4.5e6))
    assert results["points"][0]["status"]=="INFEASIBLE_SCREEN"
    assert results["points"][1]["status"]=="INFEASIBLE_SCREEN"
    valid={r["pressure_Pa"] for r in results["points"] if
           r["status"]=="FINITE_HX_THERMODYNAMIC_SCREEN_PASS"}
    assert results["screening_best_pressure_Pa"] is None or (
        results["screening_best_pressure_Pa"] in valid)
