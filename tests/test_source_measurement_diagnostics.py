"""Source-data workflow regression; fixtures are synthetic NOT experiment data."""
import runpy
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
OBS=runpy.run_path(str(ROOT/"scripts/analyze_horizontal_bed_observations.py"))
INSPECT=runpy.run_path(str(ROOT/"scripts/inspect_public_copper_slag_a1.py"))


def test_threshold_interpolation_uses_measured_time_and_avoids_guessed_geometry():
    f=OBS["first_threshold_time"]
    rows=[
        {"Time exp.":0.0,"out":20.0},
        {"Time exp.":30.0,"out":60.0},
        {"Time exp.":60.0,"out":100.0},
        {"Time exp.":90.0,"out":120.0},
    ]
    assert f(rows,"out",80.0)==pytest.approx(45.0)
    assert f(rows,"out",180.0) is None


def test_data_validator_requires_original_sha(monkeypatch,tmp_path):
    file=tmp_path/"Case_A.csv"
    file.write_text("Time exp.,Velocity,$T_{out}$\n0,1,22\n",encoding="utf-8")
    with pytest.raises(ValueError,match="modified"):
        OBS["load_case"](tmp_path,"A")


def test_radial_only_dataset_cannot_be_mislabeled_axial(tmp_path):
    file=tmp_path/"one_radial_only.csv"
    lines=[
        "Run:,R4,Topology:,Radial,Temperature [°C],,300,Charging time [h]:,,3.0",
        "Time [h],T_upper [°C],T_1 [°C],T_2 [°C],T_3 [°C],T_4 [°C],T_5 [°C],T_6 [°C],T_bottom [°C],",
    ]
    lines += [f"{(k+1)/360},{20+k/10},20,20,20,20,20,20,20," for k in range(14)]
    file.write_text("\n".join(lines),encoding="cp1252")
    out=INSPECT["inspect_sections"](file,require_hash=False)
    assert len(out["sections"])==1
    assert out["sections"][0]["run"]=="R4"
    assert out["sections"][0]["topology"]=="Radial"
    assert all(s["run"]!="A1" for s in out["sections"])
    assert out["experimental_validation"]=="NOT_RUN"
