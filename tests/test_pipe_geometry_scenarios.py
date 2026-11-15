"""Pipe-schedule hypotheses never become an unverified instrument calibration."""
import pytest
from carnot_battery_lab.validation.pipe_geometry_scenarios import nominal_scenario_table


def test_schedule_scenarios_match_nominal_dimension_relation():
    result=nominal_scenario_table()
    options=result["scenarios"]
    assert options[0]["conditional_nominal_bore_mm"]==pytest.approx(52.48)
    assert options[1]["conditional_nominal_bore_mm"]==pytest.approx(49.22)
    assert result["flow_ratio_larger_over_smaller"]==pytest.approx((52.48/49.22)**2)
    assert result["measurement_status"]=="SCENARIO_ONLY_NOT_INSTRUMENT_GEOMETRY_VERIFIED"
    assert result["this_assumption_is_UNVERIFIED"] is True
    assert all(not x["actual_probe_pipe_schedule_verified"] for x in options)
    assert result["cannot_calibrate_pressure_channel"]


def test_zero_velocity_no_mass_flow_or_calibrated_pipe_id():
    result=nominal_scenario_table(velocity_m_s=0)
    assert result["flow_ratio_larger_over_smaller"] is None
    assert all(x["conditional_exhaust_mass_flow_kg_s"]==0 for x in result["scenarios"])


def test_invalid_scenario_conditions_rejected():
    with pytest.raises(ValueError):
        nominal_scenario_table(velocity_m_s=-1)
    with pytest.raises(ValueError):
        nominal_scenario_table(measured_exhaust_C=-274)
