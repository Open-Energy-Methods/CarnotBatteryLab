import math
import pytest
from carnot_battery_lab.physics.thermodynamics import (
    thermal_stream_exergy_J_per_kg,
    specific_physical_flow_exergy_delta_J_per_kg,
    electricity_per_useful_heat_kWh_per_kWh,
    electrical_round_trip_efficiency,
)


def test_flow_exergy_zero_over_identical_boundaries():
    assert thermal_stream_exergy_J_per_kg(450,450,293.15,1000) == 0


def test_flow_exergy_constant_cp_matches_h_entropy_identity():
    t1,t2,t0,cp=420.0,360.0,293.15,1500.0
    expected=(cp*(t1-t2)) - t0*(cp*math.log(t1/t2))
    assert thermal_stream_exergy_J_per_kg(t1,t2,t0,cp) == pytest.approx(expected)
    assert specific_physical_flow_exergy_delta_J_per_kg(cp*(t1-t2),cp*math.log(t1/t2),t0) == pytest.approx(expected)


def test_temperature_domain_failure():
    with pytest.raises(ValueError):thermal_stream_exergy_J_per_kg(-1,300,293.15,1000)
    with pytest.raises(ValueError):thermal_stream_exergy_J_per_kg(300,350,293.15,1000)


def test_thermal_and_electric_round_trip_are_distinct():
    assert electricity_per_useful_heat_kWh_per_kWh(1,2) == .5
    assert electrical_round_trip_efficiency(1,2) == .5
    with pytest.raises(ValueError):electrical_round_trip_efficiency(10,0)
