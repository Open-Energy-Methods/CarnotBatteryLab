"""Mass-flow sensitivity and pressure unit safety are deterministic tests."""
import pytest
from math import pi
from carnot_battery_lab.validation.flow_pressure_audit import (
    ExhaustScenario,PressureCalibration,EvidenceMissing,
    sensitivity_scenarios,convert_pressure_channel,native_pressure_diagnostics)


def test_exhaust_air_mass_flux_uses_source_published_geometry_relation():
    s=ExhaustScenario(.052,101325,100,5)
    assert s.mass_flow_kg_s==pytest.approx(
        (101325/(287.05*373.15))*(pi*.052**2/4)*5)


def test_unknown_exhaust_id_is_quadratic_not_arbitrary_calibration():
    r=sensitivity_scenarios(Tout_C=110,velocity_m_s=5,
                           diameters_m=(.045,.052,.060))
    assert r["max_over_min_mdot"]==pytest.approx((.060/.045)**2)
    assert r["validation_status"]=="NOT_INDEPENDENT"
    assert r["measurement_dependency"].startswith("T_out")


def test_pressures_remain_unconverted_when_source_calibration_missing():
    cal=PressureCalibration(channel_name="CSV $\\Delta P$")
    with pytest.raises(EvidenceMissing,match="verified_unit_conversion"):
        convert_pressure_channel((.3,.4,.5),cal)
    assert "transducer_calibration_source" in cal.missing()
    assert "verified_pressure_tap_boundaries" in cal.missing()


def test_compensated_pressure_is_not_calibration_without_source():
    cal=PressureCalibration("synthetic",pressure_unit_to_Pa=1000,
        offset_in_native_units=.1,calibration_source_reference="synthetic-test",
        taps_span_only_bed=False,pipe_minor_loss_correction_Pa=50,
        pressure_uncertainty_Pa=5)
    assert cal.missing()==()
    assert convert_pressure_channel((.2,.3),cal)==pytest.approx((50,150))


def test_pipe_correction_missing_rejected():
    cal=PressureCalibration("test",pressure_unit_to_Pa=1000,
        offset_in_native_units=0,calibration_source_reference="dummy",
        taps_span_only_bed=False,pressure_uncertainty_Pa=5)
    assert "independently_measured_pipe_fitting_loss" in cal.missing()


def test_native_negative_pressure_is_preserved_not_silently_clipped():
    x=native_pressure_diagnostics((-.01,0.1,.3,.4),(3.0,4.0,5.0,6.0))
    assert x["nonpositive_pressure_readings"]==1
    assert x["cannot_compare_with_Ergun_Pa"] is True


def test_nonnumeric_input_fails_closed():
    with pytest.raises(ValueError):
        ExhaustScenario(.052,static_pressure_Pa=-10)
    with pytest.raises(ValueError):
        sensitivity_scenarios(Tout_C=100,velocity_m_s=5,
                              diameters_m=(.06,.04))
