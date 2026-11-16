"""Mixed-phase TC source semantics and non-calibrating possible-position bounds."""
import pytest
from carnot_battery_lab.validation.sensor_phase_envelopes import (
    SensorLayoutEvidence, UnqualifiedSensorEvidence,
    sensor_phase_position_envelope,envelope_exceedance_C,diagnostic_summary)


def test_unknown_absolute_offset_admits_only_geometrically_possible_positions():
    e=SensorLayoutEvidence()
    assert e.maximum_initial_offset_m==pytest.approx(.1)
    assert e.axial_possible_interval_m(0)==pytest.approx((0,.1))
    assert e.axial_possible_interval_m(6)==pytest.approx((.3,.4))


def test_sensor_not_auto_assigned_to_fluid_or_rock():
    e=SensorLayoutEvidence()
    # Bed 4 cells, fluid hotter than solid. T1 may be in cell 0 or 1.
    bound=sensor_phase_position_envelope(
        (200.,190.,180.,170.),(30.,40.,50.,60.),0,e)
    assert bound.lower_model_temperature_C==pytest.approx(30)
    assert bound.upper_model_temperature_C==pytest.approx(200)
    assert bound.sampled_cell_indices==(0,1)
    assert bound.status.startswith("UNQUALIFIED")


def test_unknown_axial_offset_not_fit_from_measured_target():
    gas=(210.,200.,190.,180.)
    rock=(20.,30.,40.,50.)
    a=sensor_phase_position_envelope(gas,rock,0)
    assert envelope_exceedance_C(40.,a)==0
    assert envelope_exceedance_C(-10.,a)==pytest.approx(30)
    assert envelope_exceedance_C(230.,a)==pytest.approx(20)


def test_known_independent_offset_restricts_possible_cell():
    layout=SensorLayoutEvidence(exact_initial_offset_m=.075)
    a=sensor_phase_position_envelope((210.,200.,190.,180.),
                                     (20.,30.,40.,50.),0,layout)
    assert a.axial_possible_m==pytest.approx((.075,.075))
    assert a.sampled_cell_indices==(0,)


def test_summary_does_not_claim_validation_when_all_observations_inside():
    a=sensor_phase_position_envelope((100.,100.),(30.,30.),0)
    report=diagnostic_summary([(50.,a),(60.,a)])
    assert report["outside_model_extrema_fraction"]==0
    assert report["scientific_status"].endswith("NOT_MODEL_VALIDATION")
    assert report["not_a_measurement_uncertainty_interval"] is True


def test_invalid_sensor_placement_or_phase_assumption_rejected():
    with pytest.raises(UnqualifiedSensorEvidence):
        SensorLayoutEvidence(number_of_sensors=11,published_spacing_m=.05)
    with pytest.raises(UnqualifiedSensorEvidence):
        SensorLayoutEvidence(sheath_contacts_gas_and_solid=False)
    with pytest.raises(UnqualifiedSensorEvidence):
        SensorLayoutEvidence(exact_initial_offset_m=.2)
    with pytest.raises(UnqualifiedSensorEvidence):
        SensorLayoutEvidence().axial_possible_interval_m(7)
