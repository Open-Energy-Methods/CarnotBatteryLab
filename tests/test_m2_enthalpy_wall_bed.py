"""NIST-source air enthalpy consistency and variable-cp wall energy closure."""
from math import pi
import pytest
pytest.importorskip("scipy",reason="nonlinear enthalpy-wall solver requires physics optional deps")
from carnot_battery_lab.physics.ideal_dry_air import (
    air_cp_J_kgK,air_sensible_enthalpy_J_kg,
    air_mu_sutherland_Pa_s,air_k_powerlaw_W_mK)
from carnot_battery_lab.physics.enthalpy_wall_bed import (
    HypotheticalSlag,CylindricalSteelShell,EnthalpyWallBed,EnthalpyWallState,
    advance_enthalpy_wall,energy_J)

@pytest.mark.parametrize("T",[300.,400.,499.,501.,699.,701.,900.,1200.])
def test_d_enth_d_T_matches_NIST_cp_not_cp_times_delta_T(T):
    delta=1e-3
    numerical=(air_sensible_enthalpy_J_kg(T+delta)-
               air_sensible_enthalpy_J_kg(T-delta))/(2*delta)
    assert numerical==pytest.approx(air_cp_J_kgK(T),rel=1e-6)
    assert 950<air_cp_J_kgK(T)<1400


@pytest.mark.parametrize("cross",[500.,700.])
def test_shomate_piecewise_enthalpy_is_continuous(cross):
    h1=air_sensible_enthalpy_J_kg(cross-1e-5)
    h2=air_sensible_enthalpy_J_kg(cross+1e-5)
    assert abs(h2-h1)<.2  # 2e-5 K * ~1000 J/kg K


def test_air_property_domain_and_transport_scenario():
    assert air_cp_J_kgK(300.)==pytest.approx(1011.46,rel=.003)
    assert air_sensible_enthalpy_J_kg(298.15)==0.
    assert air_mu_sutherland_Pa_s(600.)>air_mu_sutherland_Pa_s(300.)
    assert air_k_powerlaw_W_mK(600.)>air_k_powerlaw_W_mK(300.)
    with pytest.raises(ValueError):
        air_cp_J_kgK(1501.)


def test_slag_specific_enthalpy_derivative_matches_its_cp():
    s=HypotheticalSlag(cp_reference_J_kgK=1100.,
                       cp_linear_slope_J_kgK2=.3)
    t=500.
    assert (s.h(t+.01)-s.h(t-.01))/.02==pytest.approx(s.cp(t),rel=1e-10)
    with pytest.raises(ValueError):
        HypotheticalSlag(cp_reference_J_kgK=10,cp_linear_slope_J_kgK2=-10)


def test_source_7mm_cylindrical_steel_shell_capacity_explicit():
    shell=CylindricalSteelShell()
    expected_volume=pi*((.158/2+.007)**2-(.158/2)**2)*.400
    assert shell.mass_kg==pytest.approx(expected_volume*7850)
    assert 5000<shell.thermal_capacity_J_K<7000


@pytest.mark.parametrize("cells",[4,8,16])
def test_variable_cp_plus_wall_self_consistent_first_law(cells):
    pytest.importorskip("scipy")
    bed=EnthalpyWallBed(cells=cells)
    start=EnthalpyWallState.uniform(bed,350.)
    r=advance_enthalpy_wall(bed,start,inlet_K=480.,
                            mass_flow_kg_s=.02,dt_s=30.,
                            relative_tolerance=1e-8)
    assert r.heat_from_inlet_gas_J>0
    assert r.stored_energy_change_J>0
    assert r.final_outlet_gas_K<=480.+1e-3
    assert abs(r.first_law_residual_J)<.0001*abs(r.heat_from_inlet_gas_J)
    assert r.solver_nfev>0
    # Shell temperature must participate in the transient via rock-wall flux.
    assert r.final_state.wall_K[0]>350.


def test_no_flow_no_wall_external_losses_energy_is_conserved():
    pytest.importorskip("scipy")
    bed=EnthalpyWallBed(cells=8,wall_to_ambient_UA_W_K=0.)
    state=EnthalpyWallState((400.,)*8,(350.,)*8,(320.,)*8)
    old=energy_J(bed,state)
    r=advance_enthalpy_wall(bed,state,inlet_K=350.,
                            mass_flow_kg_s=0,dt_s=60.)
    assert r.heat_from_inlet_gas_J==pytest.approx(0.,abs=1e-4)
    assert r.heat_lost_to_ambient_J==pytest.approx(0.,abs=1e-4)
    assert energy_J(bed,r.final_state)==pytest.approx(old,abs=.2)
    assert abs(r.first_law_residual_J)<.2


def test_hot_wall_rejects_gain_at_ambient_as_outgoing_loss():
    pytest.importorskip("scipy")
    bed=EnthalpyWallBed(cells=8,ambient_K=310.,
                        solid_to_wall_UA_W_K=0.,
                        wall_to_ambient_UA_W_K=8.)
    state=EnthalpyWallState((320.,)*8,(320.,)*8,(500.,)*8)
    r=advance_enthalpy_wall(bed,state,inlet_K=320.,
                            mass_flow_kg_s=0,dt_s=120.)
    assert r.heat_lost_to_ambient_J>0.
    assert r.stored_energy_change_J<0.
    assert abs(r.first_law_residual_J)<.1


def test_incompatible_source_wall_geometry_rejected():
    from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
    with pytest.raises(ValueError,match="match geometry"):
        EnthalpyWallBed(geometry=PackedBedGeometry(.4,.2,.02,.39))
