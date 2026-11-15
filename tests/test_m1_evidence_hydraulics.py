"""Evidence-separated M1 hydraulic, compressor and HX verification tests."""
import pytest

pytest.importorskip("CoolProp")

from carnot_battery_lab.physics.r718 import R718Inputs, solve_r718
from carnot_battery_lab.physics.compressor_evidence import (
    DESIGN_2018, compare_required_stage_ratios)
from carnot_battery_lab.physics.auxiliary_hydraulics import (
    ILLUSTRATIVE_CIRCUITS, PipeCircuit, solve_pipe, add_liquid_auxiliaries)
from carnot_battery_lab.physics.hx_convergence import hx_resolution_study


@pytest.fixture(scope="module")
def hp():
    return solve_r718(R718Inputs())


def test_published_nominal_impeller_volume_mass_density_consistency():
    # Independent *reported design inputs*, but not experimentally measured output.
    for impeller in DESIGN_2018:
        result=impeller.property_check()
        assert abs(result["relative_volume_flow_difference"])<0.08


def test_reference_impellers_are_not_misrepresented_as_feasible(hp):
    nominal=compare_required_stage_ratios(hp,reference="design_2018")
    measured=compare_required_stage_ratios(hp,reference="measured_2020")
    assert nominal["reference_type"]=="nominal_design_points"
    assert not nominal["fits_reference_ratio_caps"]
    assert nominal["stage_ratio_exceeded"]==(True,True)
    assert measured["stage_ratio_exceeded"]==(True,True)
    assert nominal["product_ratio_reference"]==pytest.approx(6.4)
    assert measured["product_ratio_reference"]==pytest.approx(4.8)


def test_auxiliary_pumps_and_pressurised_liquid_properties(hp):
    r=add_liquid_auxiliaries(hp)
    assert len(r["circuits"])==3
    assert all(x.density_kg_m3>0 for x in r["circuits"])
    assert all(x.pressure_drop_Pa>0 for x in r["circuits"])
    assert r["total_grid_electric_W"]>hp.W_compressor_electric_W
    assert r["COP_grid_with_liquid_auxiliaries"]<hp.COP_heating_electric
    assert r["liquid_pump_electric_W"]==pytest.approx(
        sum(x.pump_electric_W for x in r["circuits"]))
    assert r["circuits"][1].density_kg_m3<r["circuits"][0].density_kg_m3


def test_pipe_zero_flow_and_flow_scaling():
    c=ILLUSTRATIVE_CIRCUITS[0]
    zero=solve_pipe(c,0.0)
    assert zero.pressure_drop_Pa==0.0
    assert zero.pump_electric_W==0.0
    low=solve_pipe(c,2.0)
    high=solve_pipe(c,4.0)
    assert high.pressure_drop_Pa>low.pressure_drop_Pa
    assert high.pump_electric_W>2*low.pump_electric_W


def test_liquid_pressure_and_invalid_pipe_rejected():
    with pytest.raises(ValueError):
        PipeCircuit("bad",1e5,130,40,.05,1e-5,8,.7)
        # invalid liquid phase is rejected during solve, not at construction
    with pytest.raises(ValueError,match="subcooled"):
        solve_pipe(PipeCircuit("boiling",100000.0,130.0,40,.05,1e-5,8,.7),3.0)


def test_hx_quadrature_convergence_without_fitting(hp):
    runs=hx_resolution_study(hp.inputs,(24,48,96,192))
    assert len(runs)==4
    changes=[r.worst_relative_change_from_previous for r in runs[1:]]
    assert all(x>=0 for x in changes)
    assert changes[-1] < changes[0]
    # A conservative pre-registered screening rule, not physical accuracy.
    assert changes[-1] < 0.01


def test_hx_resolution_validation():
    with pytest.raises(ValueError):
        hx_resolution_study(R718Inputs(),(48,24,96))
