import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hp_cycle import solve_hp_cycle


def test_first_law_closure():
    r = solve_hp_cycle()
    # q_cond must equal w_comp + q_evap to machine precision (energy balance)
    assert abs(r.q_cond - (r.w_comp + r.q_evap)) / r.q_cond < 1e-9


def test_cop_below_carnot_limit():
    r = solve_hp_cycle()
    T_evap_K = r.T_evap_C + 273.15
    T_cond_K = r.T_cond_C + 273.15
    cop_carnot = T_cond_K / (T_cond_K - T_evap_K)
    assert 0 < r.COP_heating < cop_carnot


def test_cop_cooling_is_cop_heating_minus_one():
    r = solve_hp_cycle()
    assert abs(r.COP_cooling - (r.COP_heating - 1)) < 1e-6


def test_isentropic_efficiency_increases_cop():
    r_low = solve_hp_cycle(eta_is=0.5)
    r_high = solve_hp_cycle(eta_is=0.9)
    assert r_high.COP_heating > r_low.COP_heating


def test_saturation_states_are_physical():
    r = solve_hp_cycle()
    assert r.P_evap_Pa < r.P_cond_Pa
    assert r.h2 > r.h1  # compression increases enthalpy
    assert r.h3 < r.h2  # condensation rejects heat
