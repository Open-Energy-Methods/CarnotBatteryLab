"""512-cell numerical pass must never imply independent physical validation."""
import runpy
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
assess=runpy.run_path(str(ROOT/"scripts/report_m2_physical_validation_readiness.py"))["assess"]
SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"


def test_two_passing_meshes_keep_physical_gate_blocked():
    historic={
        "source_sha256":SHA,
        "doi":"10.17632/j37x6ptpk2.1",
        "source_case":"B_only",
        "flow_target_leakage_warning":"Measured Tout enters mass flow",
        "refinement_evidence":{
            "provisional_numerical_increment_pass_at_512":True,
            "external_physical_validation_pass":False,
        }
    }
    independent={
        "source_sha256":SHA,
        "source_doi":"10.17632/j37x6ptpk2.1",
        "case":"B_only",
        "measured_Tout_excluded_from_physics":True,
        "refinement":{
            "provisional_spatial_screen_pass":True,
            "predictive_experimental_validation_pass":False,
        }
    }
    output=assess(historic,independent)
    assert output["historical_mesh_provisional_pass"] is True
    assert output["target_independent_mesh_provisional_pass"] is True
    assert output["true_experimental_predictive_validation_pass"] is False
    assert output["target_independent_mass_flow_measured_and_calibrated"] is False
    assert "pressure" in output["missing_evidence"]


def test_invalid_experimental_checksum_rejected():
    historic={
        "source_sha256":"UNVERIFIED",
        "doi":"10.17632/j37x6ptpk2.1",
        "source_case":"B_only",
    }
    independent={"source_sha256":SHA}
    with pytest.raises(ValueError,match="checksum"):
        assess(historic,independent)


def test_measured_outlet_leak_in_new_study_rejected():
    historic={"source_sha256":SHA,"doi":"10.17632/j37x6ptpk2.1",
        "source_case":"B_only","flow_target_leakage_warning":"measured Tout",
        "refinement_evidence":{
            "provisional_numerical_increment_pass_at_512":True,
            "external_physical_validation_pass":False}}
    independent={"source_sha256":SHA,"source_doi":"10.17632/j37x6ptpk2.1",
        "case":"B_only","measured_Tout_excluded_from_physics":False,
        "refinement":{"provisional_spatial_screen_pass":True,
                      "predictive_experimental_validation_pass":False}}
    with pytest.raises(ValueError,match="leaked"):
        assess(historic,independent)
