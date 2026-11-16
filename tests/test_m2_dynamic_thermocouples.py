"""Independent exact sensor-step benchmarks and common-layout restrictions."""
from math import exp
import pytest
from carnot_battery_lab.validation.dynamic_thermocouples import (
    ThermocoupleHypothesis,first_order_ramp_step,mixed_equilibrium_K,
    sample_cell_centres,simulate_probe_history,uncalibrated_scenario_envelope,
    preregistered_scenarios,
)

def test_sensor_step_has_exact_constant_input_exponential():
    initial=300.
    eq=400.
    tau=60.
    result=first_order_ramp_step(initial,eq,eq,60.,tau)
    assert result==pytest.approx(400.+(300.-400.)*exp(-1),abs=1e-11)


def test_sensor_linear_ramp_matches_independent_integral_special_case():
    # Initial model bead equals forcing at t=0. tau=dt so integral of
    # linear forcing yields 1/e of the input delta.
    assert first_order_ramp_step(300.,300.,400.,60.,60.)==pytest.approx(
        300.+100/exp(1),abs=1e-10)


def test_zero_tau_tracks_forcing_no_lookahead():
    assert first_order_ramp_step(320.,320.,450.,40.,0.)==450.


def test_nearly_zero_interval_numerically_stable():
    y=first_order_ramp_step(300.,300.,400.,1e-6,100.)
    assert 300.<y<300.+1e-6


def test_one_global_offset_creates_correlated_probe_positions():
    s=ThermocoupleHypothesis(.05,.4,25.)
    assert len(s.positions_m)==7
    assert s.positions_m[0]==pytest.approx(.05)
    assert s.positions_m[-1]==pytest.approx(.35)
    assert all(z2-z1==pytest.approx(.05) for z1,z2 in zip(s.positions_m,s.positions_m[1:]))
    with pytest.raises(ValueError,match="first-position"):
        ThermocoupleHypothesis(.11,.5,25.)
    with pytest.raises(ValueError,match="gas-contact"):
        ThermocoupleHypothesis(.05,1.2,25.)


def test_linear_spatial_sample_exact_on_linear_temperature_profile():
    # Two cell centres at 0.1 m and 0.3 m (L=0.4).
    values=(300.,500.)
    assert sample_cell_centres(values,.2,.4)==pytest.approx(400.)
    assert sample_cell_centres(values,0.,.4)==300.
    assert sample_cell_centres(values,.4,.4)==500.


def test_mixed_phase_contact_hypothesis_uses_single_position_each_probe():
    s=ThermocoupleHypothesis(.05,.25,0.)
    a=mixed_equilibrium_K([400.]*8,[300.]*8,s)
    assert len(a)==7
    assert all(x==pytest.approx(325.) for x in a)


def test_two_independently_predicted_fields_with_shared_lag_response():
    s=ThermocoupleHypothesis(.05,.5,30.)
    times=(0.,30.,60.)
    gas=([320.]*8,[420.]*8,[420.]*8)
    solid=([300.]*8,[300.]*8,[300.]*8)
    result=simulate_probe_history(times,gas,solid,s)
    assert len(result)==7
    for history in result:
        assert history[0]==pytest.approx(310.)
        assert history[0]<history[1]<history[2]<360.
    # Calculation does not require measured targets.


def test_unfitted_sensor_scenario_envelope_does_not_pass_experiment():
    times=(0.,30.,60.)
    gas=([320.]*8,[400.]*8,[400.]*8)
    solid=([300.]*8,[300.]*8,[300.]*8)
    bound=uncalibrated_scenario_envelope(times,gas,solid)
    assert len(bound["scenarios"])==27
    assert bound["experimental_validation_pass"] is False
    assert len(bound["low_K"])==7
    assert all(a<=b for low,high in zip(bound["low_K"],bound["high_K"])
               for a,b in zip(low,high))
    assert bound["not_a_calibrated_uncertainty_or_joint_confidence_interval"] is True


def test_time_decrease_is_rejected():
    s=ThermocoupleHypothesis(.05,.5,60.)
    with pytest.raises(ValueError,match="increasing"):
        simulate_probe_history((0.,60.,50.),([300.]*8,)*3,
                               ([300.]*8,)*3,s)


def test_no_model_parameter_fitted_to_measured_sensor_target():
    scenarios=preregistered_scenarios()
    assert {x.first_position_m for x in scenarios}=={0.,.05,.10}
    assert {x.response_tau_s for x in scenarios}=={0.,30.,180.}
    assert {x.gas_contact_fraction for x in scenarios}=={.25,.5,.75}
