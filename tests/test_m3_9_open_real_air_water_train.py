"""M3.9 synthetic coupled-air/water prototype regressions."""
from dataclasses import replace
import pytest
pytest.importorskip("CoolProp")
from carnot_battery_lab.physics.open_real_air_water_train import (
    OpenAirWaterTrain,hx_darcy_face,run_open_air_water_train,
)
from carnot_battery_lab.physics.real_air_bed_prototype import _tp_properties


def test_darcy_signed_upwind_and_zero_gradient():
    l=_tp_properties(493.15,250100.)
    r=_tp_properties(383.15,249900.)
    a=hx_darcy_face(l,r,area=.012,loss_coefficient=1.)
    b=hx_darcy_face(r,l,area=.012,loss_coefficient=1.)
    assert a[0]>0
    assert a[1]==pytest.approx(a[0]*l["h"])
    assert b[0]==pytest.approx(-a[0])
    assert b[1]==pytest.approx(-a[1])
    assert hx_darcy_face(l,l,area=.012,loss_coefficient=1.)==(0.,0.,0.)


def test_pressure_connected_bed_and_counterflow_water_conservation():
    a=OpenAirWaterTrain(bed_cells=3,hx_cells=3)
    r=run_open_air_water_train(a,duration_s=30.)
    assert len(r["gas_final_states"])==6
    assert len(r["gas_face_mass_flow_kg_s"])==7
    assert r["bed_HX_shared_interface_mass_kg"]>0
    assert r["water_net_boundary_heat_J"]>0
    assert r["water_outlet_final_C"]>110.
    assert r["bed_solid_inventory_change_J"]<0.
    for key in ("bed_mass_residual_kg","HX_mass_residual_kg","whole_train_mass_residual_kg"):
        assert abs(r[key])<1e-7
    for key in ("bed_energy_residual_J","HX_energy_residual_J","whole_train_energy_residual_J"):
        assert abs(r[key])<.2
    assert all(x>0 for x in r["gas_face_mass_flow_kg_s"])
    assert r["maximum_interstitial_or_HX_Mach_at_accepted_nodes"]<.1
    assert r["gas_EOS_mass_and_energy_coupled_across_bed_HX"]
    assert not r["gas_return_closed_loop_implemented"]
    assert not r["industrial_1MW_service_qualified"]
    assert r["Carnot_battery_RTE"] is None


def test_cold_equilibrium_no_hidden_energy_input_to_water():
    a=OpenAirWaterTrain(bed_cells=2,hx_cells=2,
                         initial_bed_solid_K=383.15)
    r=run_open_air_water_train(a,duration_s=10.)
    # Nonzero pressure gradient can cause a small Joule-Thomson transient;
    # do not assert zero exactly for REAL gas.
    assert abs(r["water_net_boundary_heat_J"])<20.
    assert abs(r["water_outlet_final_C"]-110.)<.1


def test_increased_hx_resistance_changes_bed_flow_not_just_hx_flow():
    a=OpenAirWaterTrain(bed_cells=2,hx_cells=2)
    x=run_open_air_water_train(a,duration_s=20.)
    y=run_open_air_water_train(replace(a,hx_total_minor_K=40.),duration_s=20.)
    assert y["bed_HX_shared_interface_mass_kg"]<x["bed_HX_shared_interface_mass_kg"]
    assert y["left_mass_in_kg"]<x["left_mass_in_kg"]
    assert y["gas_face_mass_flow_kg_s"][1]<x["gas_face_mass_flow_kg_s"][1]


@pytest.mark.parametrize("kw",[
    {"water_pressure_assumed_Pa":400000.},{"hx_overall_UA_W_K":-1.},
    {"porosity":1.1},{"bed_cells":1},{"outlet_reservoir_P_Pa":260000.}
])
def test_invalid_prototype_input_rejected(kw):
    with pytest.raises(ValueError):
        run_open_air_water_train(OpenAirWaterTrain(**kw),duration_s=1.)
