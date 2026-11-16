"""Non-fit synthetic model sensitivity with exact independent structural aliases."""
import pytest
pytest.importorskip("scipy")
from dataclasses import replace
from carnot_battery_lab.validation.m2_synthetic_identifiability import (
    SyntheticInputs,forward_synthetic,exact_reparameterisation_aliases,
    synthetic_local_sensitivity,
)


def test_physical_model_uncertainty_scenarios_not_probabilities():
    x=SyntheticInputs()
    assert x.pipe_inner_diameter_m==.052
    with pytest.raises(ValueError):
        replace(x,pipe_inner_diameter_m=0)
    with pytest.raises(ValueError):
        replace(x,porosity=.7)


def test_flow_bore_and_velocity_calibration_are_exact_structural_alias():
    x=SyntheticInputs()
    pairs=exact_reparameterisation_aliases(x)
    assert pairs["same_D_squared_velocity_product"]
    r=forward_synthetic(x,cells=6,steps=5,dt_s=45)
    other=forward_synthetic(
        SyntheticInputs(**pairs["pipe_diameter_and_velocity_scale_pair"]),
        cells=6,steps=5,dt_s=45)
    assert r["T_out_K"]==pytest.approx(other["T_out_K"],abs=2e-5)
    assert r["stored_energy_increase_J"]==pytest.approx(
        other["stored_energy_increase_J"],abs=.03)


def test_rock_density_and_heat_capacity_are_exact_model_alias():
    x=SyntheticInputs()
    pair=exact_reparameterisation_aliases(x)
    assert pair["same_rock_volumetric_heat_capacity"]
    r=forward_synthetic(x,cells=6,steps=5,dt_s=45)
    other=forward_synthetic(SyntheticInputs(**pair["rock_density_and_cp_pair"]),
                            cells=6,steps=5,dt_s=45)
    assert r["T_out_K"]==pytest.approx(other["T_out_K"],abs=2e-5)


def test_synthetic_energy_closed_but_not_physical_validation():
    r=forward_synthetic(cells=6,steps=5,dt_s=45)
    assert r["analysis_class"]=="SYNTHETIC_UNCALIBRATED_MODEL_ONLY"
    assert abs(r["end_to_end_first_law_residual_J"])<.1


def test_local_log_sensitivity_has_no_measured_output_targets():
    r=synthetic_local_sensitivity(cells=6,steps=5,dt_s=45)
    assert r["actual_experiment_fitted"] is False
    assert r["source_2024_case_B_C_D_used"] is False
    assert r["external_physical_validation_pass"] is False
    assert len(r["parameter_metrics"])==7
    assert len(r["outlet_temperature_sensitivity_matrix_K"])==5
    assert len(r["outlet_temperature_sensitivity_matrix_K"][0])==7
    assert r["effective_SVD_rank_relative_1e_minus3"]<=5


def test_perturbation_scale_guard():
    with pytest.raises(ValueError):
        synthetic_local_sensitivity(cells=6,steps=5,log_step=0)
