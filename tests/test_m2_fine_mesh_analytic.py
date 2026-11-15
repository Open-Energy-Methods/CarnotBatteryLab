"""Independent closed-form two-temperature exchanger and spatial-evidence checks.

This is a mathematical VERIFICATION benchmark, not an experiment. It checks
an isolated gas/rock exchange against the analytical solution, including
spatial grids that differ by 32x, and keeps physical validation FALSE.
"""
from __future__ import annotations
import math
from pathlib import Path
import runpy
import sys
import pytest
pytest.importorskip("scipy")

from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed,BedState,advance_bed,
)

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
SCRIPT=runpy.run_path(str(ROOT/"scripts/study_horizontal_bed_fine_mesh_512.py"))
MESHES=SCRIPT["MESHES"]


@pytest.mark.parametrize("n",[8,32,128,256])
def test_sealed_two_temperature_exchange_matches_closed_form(n:int):
    bed=GasRockBed(
        geometry=PackedBedGeometry(length_m=.4,diameter_m=.158,
                                   particle_diameter_m=.02,porosity=.39),
        cells=n,gas_density_kg_m3=1.0,rock_density_kg_m3=3700.,
        rock_cp_J_kgK=1100.,wall_UA_W_K=0.0,
        solid_axial_conductivity_W_mK=0.0)
    tf0=430.
    ts0=335.
    state=BedState((tf0,)*n,(ts0,)*n)
    t_s=30.
    result=advance_bed(bed,state,inlet_K=tf0,mass_flow_kg_s=0.,dt_s=t_s,
                       relative_tolerance=1e-10)
    vi=bed.geometry.bed_volume_m3/n
    cf=vi*bed.geometry.porosity*bed.gas_density_kg_m3*bed.gas_cp_J_kgK
    cs=vi*(1-bed.geometry.porosity)*bed.rock_density_kg_m3*bed.rock_cp_J_kgK
    H=(result.h_fluid_solid_W_m2K*
       bed.geometry.specific_interfacial_area_m2_per_m3*vi)
    d=(tf0-ts0)*math.exp(-H*(1/cf+1/cs)*t_s)
    teq=(cf*tf0+cs*ts0)/(cf+cs)
    expected_tf=teq+cs/(cf+cs)*d
    expected_ts=teq-cf/(cf+cs)*d
    assert result.final_state.fluid_temperature_K[0]==pytest.approx(expected_tf,abs=.002)
    assert result.final_state.solid_temperature_K[0]==pytest.approx(expected_ts,abs=.002)
    assert result.final_state.fluid_temperature_K[-1]==pytest.approx(expected_tf,abs=.002)
    assert abs(result.stored_energy_change_J)<.01
    assert abs(result.energy_residual_J)<.01
    assert result.heat_from_hot_gas_J==pytest.approx(0,abs=.0001)


def _artificial_source(grids):
    profiles={}
    ts=list(range(20))
    for n,offset in zip(MESHES,grids):
        profiles[n]={
            "source_sha256":"identical-fixture",
            "time_s":ts,
            "model_Tout_C":[45.0+t*.5+offset for t in ts],
            "model_first_80C_outlet_crossing_s": 1600.0+offset*30.0,
        }
    return profiles


def test_exact_mesh_pair_report_and_provisional_pass_does_not_create_validation():
    outputs=_artificial_source((4.,2.,1.,.5))
    result=SCRIPT["evaluate_fine_mesh_outputs"](outputs)
    assert list(result["pairs"])==["64_to_128","128_to_256","256_to_512"]
    assert result["observed_RMS_refinement_orders"]==pytest.approx([1,1])
    assert result["provisional_numerical_increment_pass_at_512"] is True
    assert result["external_physical_validation_pass"] is False


def test_mesh_nonconvergence_fails_without_spinning_numbers():
    outputs=_artificial_source((14.,7.,3.5,1.75))
    result=SCRIPT["evaluate_fine_mesh_outputs"](outputs)
    assert result["provisional_numerical_increment_pass_at_512"] is False


def test_invalid_mesh_pair_or_unmatched_source_fails_closed():
    outputs=_artificial_source((4.,2.,1.,.5))
    del outputs[512]
    with pytest.raises(ValueError,match="exactly"):
        SCRIPT["evaluate_fine_mesh_outputs"](outputs)
    outputs=_artificial_source((4.,2.,1.,.5))
    outputs[512]["source_sha256"]="different-source"
    with pytest.raises(ValueError,match="different experimental"):
        SCRIPT["evaluate_fine_mesh_outputs"](outputs)
