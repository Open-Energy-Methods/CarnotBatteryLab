"""Analytic sparse BDF Jacobian must reproduce independent finite difference."""
import pytest
pytest.importorskip("scipy")
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed,BedState,advance_bed)


@pytest.mark.parametrize("k_solid", [0.,2.0,10.0])
@pytest.mark.parametrize("n", [8,16,32])
def test_analytic_sparse_jacobian_matches_numerical_jacobian(n,k_solid):
    bed=GasRockBed(
        geometry=PackedBedGeometry(.4,.158,.02,.39),
        cells=n,gas_density_kg_m3=1.,rock_density_kg_m3=3700.,
        rock_cp_J_kgK=1100.,wall_UA_W_K=.5,
        solid_axial_conductivity_W_mK=k_solid)
    state=BedState.uniform(bed,32.)
    source=423.15
    a=advance_bed(bed,state,inlet_K=source,mass_flow_kg_s=.009,
                  dt_s=30,relative_tolerance=1e-9,
                  use_analytic_sparse_jacobian=True)
    b=advance_bed(bed,state,inlet_K=source,mass_flow_kg_s=.009,
                  dt_s=30,relative_tolerance=1e-9,
                  use_analytic_sparse_jacobian=False)
    assert a.final_outlet_temperature_K==pytest.approx(
        b.final_outlet_temperature_K,abs=1e-5)
    assert a.stored_energy_change_J==pytest.approx(
        b.stored_energy_change_J,abs=.01)
    assert a.energy_residual_J==pytest.approx(b.energy_residual_J,abs=.01)
    assert abs(a.energy_residual_J)<1e-5*max(abs(a.heat_from_hot_gas_J),1)


def test_invalid_jacobian_selector_rejected():
    bed=GasRockBed(cells=8)
    with pytest.raises(ValueError,match="selector"):
        advance_bed(bed,BedState.uniform(bed,90),inlet_K=403.15,
                    mass_flow_kg_s=25,dt_s=30,
                    use_analytic_sparse_jacobian="yes")
