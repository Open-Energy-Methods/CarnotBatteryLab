"""Predicted-outlet flow mesh convergence must remain scientifically unvalidated."""
from __future__ import annotations
from pathlib import Path
import runpy
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
module=runpy.run_path(str(ROOT/"scripts/study_case_B_no_target_leak_512.py"))
MESHES=module["MESHES"]


def fixture(offsets=(8.,4.,2.,1.,.5),crosses=(800,840,860,870,875)):
    return {
        n:{
            "source_sha256":"unchanged-hash",
            "model_time_s":list(range(30)),
            "outlet_temperature_target_used_in_physics":False,
            "predicted_exhaust_C":[20+i+off for i in range(30)],
            "predicted_first_80C_s":t,
        } for n,off,t in zip(MESHES,offsets,crosses)
    }


def test_source_identical_target_free_grids_report_passing_provisional_limit():
    r=module["assess"](fixture())
    assert r["observed_RMS_grid_orders"]==pytest.approx([1,1,1])
    assert r["provisional_spatial_screen_pass"] is True
    assert r["predictive_experimental_validation_pass"] is False


def test_model_target_leakage_is_rejected():
    data=fixture()
    data[256]["outlet_temperature_target_used_in_physics"]=True
    with pytest.raises(ValueError,match="measured Tout"):
        module["assess"](data)


def test_mismatched_time_or_source_rejected():
    data=fixture()
    data[512]["model_time_s"][1]=18
    with pytest.raises(ValueError,match="source or time"):
        module["assess"](data)


def test_underresolved_front_does_not_pass():
    data=fixture(crosses=(800.,850.,900.,945.,975.))
    assert not module["assess"](data)["provisional_spatial_screen_pass"]


def test_missing_crossing_does_not_infer_an_unobserved_front():
    data=fixture()
    data[512]["predicted_first_80C_s"]=None
    r=module["assess"](data)
    assert r["all_crossings_present"] is False
    assert r["provisional_spatial_screen_pass"] is False
