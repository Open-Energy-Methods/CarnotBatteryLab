"""Cross-grid internal gas/solid comparison uses common x, not cell index."""
import pytest
from carnot_battery_lab.validation.internal_field_convergence import (
    assess_internal_field_refinement,SOURCE_SHA,EXPECTED_POSITIONS)


def _mock_runs():
    out={}
    for n in (32,64,128,256,512):
        # Deterministically shrinking phase errors at all fixed x positions.
        gas={f"x{i*5:02d}cm":[300.+i+j+(100./n) for j in range(12)]
             for i in range(1,8)}
        rock={f"x{i*5:02d}cm":[280.+i+j+(.8*100./n) for j in range(12)]
              for i in range(1,8)}
        out[n]={
            "source_sha256":SOURCE_SHA,
            "outlet_temperature_target_used_in_physics":False,
            "internal_fields_do_not_use_post_initial_measured_TC":True,
            "internal_sample_positions_m":list(EXPECTED_POSITIONS),
            "model_time_s":list(range(12)),
            "internal_sampled_gas_K":gas,
            "internal_sampled_rock_K":rock,
        }
    return out


def test_all_seven_probes_both_phases_refine_on_shared_absolute_coordinates():
    result=assess_internal_field_refinement(_mock_runs())
    assert result["source_case"]=="B_only"
    assert len(result["mesh_pairs"])==4
    assert result["finest_pair_max_gas_RMS_K"]==pytest.approx(100/256-100/512)
    assert result["finest_pair_max_rock_RMS_K"]==pytest.approx(.8*(100/256-100/512))
    assert result["prospective_internal_increment_screen_1K_all_positions"] is True
    assert result["experimental_predictive_validation_pass"] is False
    assert result["qualification_of_internal_sensor_measurement_operator"] is False


def test_moving_evaluation_coordinates_rejected():
    d=_mock_runs()
    d[128]["internal_sample_positions_m"][0]=.07
    with pytest.raises(ValueError,match="same fixed"):
        assess_internal_field_refinement(d)


def test_measured_tc_target_coming_into_model_is_blocked():
    d=_mock_runs()
    d[512]["internal_fields_do_not_use_post_initial_measured_TC"]=False
    with pytest.raises(ValueError,match="downstream observed"):
        assess_internal_field_refinement(d)


def test_provenance_mismatch_rejected():
    d=_mock_runs()
    d[32]["source_sha256"]="invalid"
    with pytest.raises(ValueError,match="source"):
        assess_internal_field_refinement(d)
