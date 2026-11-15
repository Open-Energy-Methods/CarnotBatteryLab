"""2018 published nominal-point comparisons are NOT validation of vendor maps."""
import pytest
pytest.importorskip("CoolProp")
from carnot_battery_lab.physics.r718_injection_reference import (
    InjectionDesignInputs, solve_injection_design)
from carnot_battery_lab.physics.r718 import InfeasibleCycle
from carnot_battery_lab.physics.finite_hx import InfeasibleHX


def test_liquid_injection_cycle_mass_enthalpy_and_first_law():
    r=solve_injection_design()
    assert r.p_ratios==pytest.approx((3.2,2.0))
    assert r.m_injection_kg_s>0
    assert r.m_stage2_kg_s>r.m_stage1_kg_s
    assert abs(r.injection_mixing_residual_W)<1e-7*r.Q_condenser_W
    assert abs(r.first_law_residual_W)<1e-7*r.Q_condenser_W
    assert 1<r.COP_grid_no_pumps<10
    assert r.source_HX.min_approach_K>=r.inputs.source_pinch_K-1e-8
    assert r.sink_HX.min_approach_K>=r.inputs.sink_pinch_K-1e-8


def test_independent_nominal_stage2_flow_is_not_forced_equal_by_solver():
    r=solve_injection_design()
    assert r.inputs.m_stage1_kg_s==pytest.approx(0.196)
    assert r.published_stage2_flow_kg_s==pytest.approx(0.222)
    # Nominal 2018 figures are *comparison targets*, not fitted data.
    # This is a broad diagnostic band, not a pass/fail manufacturer certification.
    assert abs(r.m_stage2_kg_s/0.222-1)<0.25
    assert abs(r.volume_flow_stage1_m3_h/1231-1)<0.25
    assert abs(r.volume_flow_stage2_m3_h/468-1)<0.25


def test_injection_mixing_requires_superheated_stage2_suction():
    with pytest.raises(InfeasibleCycle,match="stage-two suction"):
        solve_injection_design(InjectionDesignInputs(T_stage2_in_C=136))


def test_higher_lift_source_not_hidden_as_80_degree_source():
    with pytest.raises(InfeasibleCycle,match="source heat transfer"):
        solve_injection_design(InjectionDesignInputs(source_in_C=80))
    r=solve_injection_design()
    assert r.source_in_C>=120
    assert r.source_out_C>100
    assert r.source_out_C<r.source_in_C


def test_insufficient_exchanger_ua_rejected():
    with pytest.raises(InfeasibleHX,match="insufficient"):
        solve_injection_design(InjectionDesignInputs(sink_UA_W_K=100))


def test_nominal_design_points_are_not_thermodynamic_laws():
    with pytest.raises(ValueError):
        InjectionDesignInputs(p_stage2_in_Pa=90000)
    with pytest.raises(ValueError):
        InjectionDesignInputs(eta_stage1=1.2)
