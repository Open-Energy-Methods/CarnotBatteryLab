"""Grid-order evaluation cannot turn internal refinement into external validation."""
import pytest
from carnot_battery_lab.validation.numerical_convergence import (
    evaluate_resolution,ResolutionEvidenceError,PAIR_KEYS)


def fixture(values=(8.,4.,2.,1.),cross=(80.,40.,20.,10.)):
    return {
      "status":"CASE_B_ONLY_RESOLUTION_AND_UNCERTAINTY_SCREEN_NO_VALIDATION",
      "experiment":"10.17632/j37x6ptpk2.1/Case_B.csv",
      "grid_pairwise_refinement_differences":{
        k:{
            "temperature_grid_RMS_difference_K":x,
            "model_80C_breakthrough_shift_s":t,
        } for k,x,t in zip(PAIR_KEYS,values,cross)
      },
    }


def test_pure_first_order_doublings_observed_exactly():
    result=evaluate_resolution(fixture())
    assert result["observed_order_from_outlet_RMS_doublings"]==pytest.approx([1.,1.,1.])
    assert result["observed_order_from_breakthrough_doublings"]==pytest.approx([1.,1.,1.])
    assert result["RMS_convergence_monotonic"] is True
    assert result["numerical_resolution_pass"] is True
    assert result["external_predictive_validation_pass"] is False


def test_doubling_still_too_coarse_is_not_numerical_pass():
    result=evaluate_resolution(fixture(values=(16,8,4,2),cross=(160,80,40,20)))
    assert result["numerical_resolution_pass"] is False


def test_missing_pair_or_missing_front_is_blocked():
    case=fixture()
    del case["grid_pairwise_refinement_differences"]["grid_64_to_grid_128"]
    with pytest.raises(ResolutionEvidenceError,match="complete"):
        evaluate_resolution(case)
    case=fixture()
    case["grid_pairwise_refinement_differences"]["grid_64_to_grid_128"]["model_80C_breakthrough_shift_s"]=None
    with pytest.raises(ResolutionEvidenceError,match="missing crossings"):
        evaluate_resolution(case)


def test_refuse_unqualified_report_type():
    case=fixture()
    case["status"]="EVIDENCE_NOT_AVAILABLE"
    with pytest.raises(ResolutionEvidenceError):
        evaluate_resolution(case)


def test_512_mesh_extension_requires_complete_source_pairs():
    source=fixture()
    source["grid_pairwise_refinement_differences"]["grid_128_to_grid_256"]={
        "temperature_grid_RMS_difference_K":.5,
        "model_80C_breakthrough_shift_s":5.,
    }
    source["grid_pairwise_refinement_differences"]["grid_256_to_grid_512"]={
        "temperature_grid_RMS_difference_K":.25,
        "model_80C_breakthrough_shift_s":2.5,
    }
    report=evaluate_resolution(source)
    assert report["finest_grid_cells"]==512
    assert len(report["rms_change_K"])==6
    assert report["numerical_resolution_pass"] is True
    assert report["external_predictive_validation_pass"] is False


def test_512_missing_256_intermediate_fails():
    source=fixture()
    source["grid_pairwise_refinement_differences"]["grid_256_to_grid_512"]={
        "temperature_grid_RMS_difference_K":.25,
        "model_80C_breakthrough_shift_s":2.5,
    }
    with pytest.raises(ResolutionEvidenceError,match="missing intermediate"):
        evaluate_resolution(source)


def test_nonmonotonic_fine_grid_cannot_claim_numerical_acceptance():
    source=fixture()
    source["grid_pairwise_refinement_differences"]["grid_128_to_grid_256"]={
        "temperature_grid_RMS_difference_K":2.,
        "model_80C_breakthrough_shift_s":20.,
    }
    source["grid_pairwise_refinement_differences"]["grid_256_to_grid_512"]={
        "temperature_grid_RMS_difference_K":.5,
        "model_80C_breakthrough_shift_s":5.,
    }
    report=evaluate_resolution(source)
    assert report["RMS_convergence_monotonic"] is False
    assert report["numerical_resolution_pass"] is False
