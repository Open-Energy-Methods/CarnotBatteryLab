"""Independent analytic HX checks; require no thermophysical library."""
import math
import pytest
from carnot_battery_lab.physics.finite_hx import InfeasibleHX,required_ua_counterflow


def test_constant_hot_temperature_matches_exact_lmtd():
    r=required_ua_counterflow(duty_W=1e6,hot_temperature_K=lambda _: 450,
        cold_in_K=350,cold_out_K=410,minimum_approach_K=5,
        installed_UA_W_per_K=1e6,segments=300)
    lmtd=(100-40)/math.log(100/40)
    assert r.required_UA_W_per_K == pytest.approx(1e6/lmtd,rel=1e-5)
    assert r.min_approach_K == pytest.approx(40)


def test_internal_pinch_discovered_not_just_terminals():
    # At both terminals Th-Tc=30 K, but at midpoint only 2 K.
    def th(x):
        return (400-40*x) - 28*math.sin(math.pi*x)
    with pytest.raises(InfeasibleHX,match="pinch"):
        required_ua_counterflow(duty_W=1e5,hot_temperature_K=th,
            cold_in_K=330,cold_out_K=370,minimum_approach_K=5,
            installed_UA_W_per_K=1e6,segments=100)


def test_inadequate_ua_and_zero_temperature_rejected():
    with pytest.raises(InfeasibleHX,match="insufficient"):
        required_ua_counterflow(duty_W=1e6,hot_temperature_K=lambda _: 450,
            cold_in_K=350,cold_out_K=410,minimum_approach_K=5,
            installed_UA_W_per_K=100,segments=100)
    with pytest.raises(InfeasibleHX):
        required_ua_counterflow(duty_W=1e6,hot_temperature_K=lambda _: float("nan"),
            cold_in_K=350,cold_out_K=410,minimum_approach_K=5,
            installed_UA_W_per_K=1e6)


def test_isothermal_cold_stream():
    r=required_ua_counterflow(duty_W=1e5,hot_temperature_K=lambda x: 390-10*x,
        cold_in_K=360,cold_out_K=360,minimum_approach_K=5,
        installed_UA_W_per_K=1e6)
    assert r.required_UA_W_per_K>0
