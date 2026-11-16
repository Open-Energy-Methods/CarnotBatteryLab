"""Experimental gate is independent of numerical convergence, even at 512 cells."""
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[1]
GATE=runpy.run_path(str(ROOT/"scripts/report_m2_validation_readiness.py"))["assess"]
SOURCE="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"


def test_physically_missing_instruments_never_pass_even_if_512_converges():
    observed={"dataset_doi":"10.17632/j37x6ptpk2.1",
              "comparisons":{"B":{"source_sha256":SOURCE}}}
    result=GATE(observed,{"case":"B ONLY","numerical_resolution_pass":True})
    assert result["numerical_resolution_pass"] is True
    assert result["mass_flow_calibration_pass"] is False
    assert result["pressure_calibration_pass"] is False
    assert result["thermal_sensor_and_material_metadata_pass"] is False
    assert result["full_experimental_validation_pass"] is False
    assert len(result["pressure_calibration_missing_machine_fields"])>=3


def test_source_hash_mismatch_hard_fails():
    observed={"dataset_doi":"10.17632/j37x6ptpk2.1",
              "comparisons":{"B":{"source_sha256":"invalid"}}}
    try:
        GATE(observed,{"case":"B ONLY","numerical_resolution_pass":True})
    except ValueError as exc:
        assert "source-locked" in str(exc)
    else:
        raise AssertionError("provenance mismatch accepted")
