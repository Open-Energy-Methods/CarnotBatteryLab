"""Real-fluid checks run in separate CoolProp CI job; not synthetic truth."""
import pytest
CoolProp=pytest.importorskip("CoolProp",reason="install -e '.[physics]' for real-fluid suite")
from CoolProp.CoolProp import PropsSI
from carnot_battery_lab.physics.r718 import R718Inputs,InfeasibleCycle,solve_r718
from carnot_battery_lab.physics.finite_hx import InfeasibleHX


def test_coolprop_if97_documented_water_state():
    # Documented values, https://coolprop.org/fluid_properties/IF97.html
    # This is an external reference, not an experiment or independent EOS implementation.
    assert PropsSI('C','T',500,'P',101325,'IF97::Water') == pytest.approx(1981.5422965970472,rel=1e-7)
    assert PropsSI('P','T',500,'Q',0,'IF97::Water') == pytest.approx(2638897.7562732203,rel=1e-7)


def test_r718_two_stage_finite_source_and_condenser_hx():
    r=solve_r718(R718Inputs())
    assert len(r.state_points)==6
    assert 1<r.COP_heating_electric<15
    assert r.stage_pressure_ratios[0]==pytest.approx(r.stage_pressure_ratios[1])
    assert all(x<r.inputs.max_stage_pressure_ratio for x in r.stage_pressure_ratios)
    assert r.Q_process_W==pytest.approx(1e6)
    assert r.Q_source_W+r.W_compressor_shaft_W == pytest.approx(r.Q_process_W+r.Q_intercool_rejected_W,rel=1e-9)
    assert r.W_compressor_electric_W>r.W_compressor_shaft_W>0
    assert r.Q_intercool_rejected_W>0
    assert r.condenser.min_approach_K>=r.inputs.minimum_hx_approach_K-1e-8
    assert r.evaporator.min_approach_K>=r.inputs.minimum_hx_approach_K-1e-8
    assert r.intercooler is not None
    assert r.source_mass_flow_kg_s>0
    assert r.process_mass_flow_kg_s>0
    assert r.compressor_entropy_generation_W_K>=0


def test_fixed_80C_source_is_not_75C_evaporating():
    r=solve_r718(R718Inputs())
    sat_T=PropsSI('T','P',r.low_pressure_Pa,'Q',1,'HEOS::Water')-273.15
    assert sat_T==pytest.approx(65,abs=0.02)
    assert sat_T!=pytest.approx(75,abs=1)


def test_single_stage_limit_rejected_at_high_lift():
    with pytest.raises(InfeasibleCycle,match="pressure ratio"):
        solve_r718(R718Inputs(arrangement="single"))


def test_hx_or_source_constraints_cannot_be_bypassed():
    with pytest.raises(InfeasibleHX,match="insufficient"):
        solve_r718(R718Inputs(condenser_UA_W_K=100))
    with pytest.raises(InfeasibleHX):
        solve_r718(R718Inputs(source_UA_W_K=100))
    with pytest.raises(InfeasibleHX,match="pinch"):
        solve_r718(R718Inputs(minimum_hx_approach_K=6))


def test_heos_if97_distinct_eos_formulations_close():
    heos=solve_r718(R718Inputs(backend="HEOS::Water"))
    if97=solve_r718(R718Inputs(backend="IF97::Water"))
    assert heos.COP_heating_electric == pytest.approx(if97.COP_heating_electric,rel=0.02)
    assert heos.Q_source_W == pytest.approx(if97.Q_source_W,rel=0.02)


def test_discharge_and_compressor_limits_are_declared_not_silent():
    with pytest.raises(InfeasibleCycle,match="discharge"):
        solve_r718(R718Inputs(max_discharge_C=90))
    with pytest.raises(InfeasibleCycle,match="pressure ratio"):
        solve_r718(R718Inputs(max_stage_pressure_ratio=2.0))


def test_increased_source_outlet_exposes_hot_end_pinch():
    # With 10 K suction superheat, 68+10 C exceeds the 80-5 C hot-end limit.
    with pytest.raises(InfeasibleHX,match="pinch"):
        solve_r718(R718Inputs(source_outlet_C=73))


def test_reduced_superheat_and_adequate_flow_allow_higher_evaporation_temperature():
    # Compare both points with adequate source-flow available.
    a=solve_r718(R718Inputs(suction_superheat_K=6,available_source_flow_kg_s=40))
    b=solve_r718(R718Inputs(source_outlet_C=73,suction_superheat_K=6,available_source_flow_kg_s=40))
    assert b.low_pressure_Pa>a.low_pressure_Pa
    assert b.COP_heating_electric>a.COP_heating_electric


def test_finite_source_and_process_mass_flow_availability():
    with pytest.raises(InfeasibleCycle,match="source heat capacity insufficient"):
        solve_r718(R718Inputs(available_source_flow_kg_s=5))
    with pytest.raises(InfeasibleCycle,match="process flow availability insufficient"):
        solve_r718(R718Inputs(available_process_flow_kg_s=5))


def test_screening_manifest_frozen_inputs(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    target=tmp_path/'r718.json'
    subprocess.run([sys.executable,str(root/'scripts/run_r718_reference.py'), '--output',str(target)],
                   cwd=root,check=True,capture_output=True,text=True)
    data=json.loads(target.read_text())
    assert data['scientific_status'].startswith('numerical_screen_unvalidated')
    assert len(data['model_assumptions_sha256'])==64
    assert len(data['study_manifest']['case_sha256'])==64
    assert data['study_manifest']['case_id']=='industrial-heat-150c-reference'
    assert data['inputs']['source_outlet_C']==70.0


def test_hotter_source_return_can_exceed_available_flow():
    with pytest.raises(InfeasibleCycle,match="source heat capacity insufficient"):
        solve_r718(R718Inputs(source_outlet_C=73,suction_superheat_K=6))
