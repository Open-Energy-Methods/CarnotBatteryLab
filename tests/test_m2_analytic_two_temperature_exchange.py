"""Independent exact 2T gas/rock exchange mode: no flow, no wall, no axial heat.

This is a genuine analytical limiting case of the implemented Schumann-
type two-temperature heat-exchange equations; it is NOT the published
full Schumann travelling thermal-breakthrough analytical solution.

For each isolated gas/solid volume (constant properties):
delta(t)=(Tf0-Ts0)*exp(-G*(1/Cf+1/Cs)*t)
Tbar=(Cf*Tf0+Cs*Ts0)/(Cf+Cs)
Tf(t)=Tbar+Cs/(Cf+Cs)*delta(t)
Ts(t)=Tbar-Cf/(Cf+Cs)*delta(t).
"""
from math import exp
import pytest
pytest.importorskip("scipy")
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed,BedState,advance_bed,bed_energy_J)
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry


@pytest.mark.parametrize("n",[8,32,128])
@pytest.mark.parametrize("dt",[.2,1.])
def test_exact_two_phase_isolated_exchange_against_analytic_solution(n,dt):
    bed=GasRockBed(
        geometry=PackedBedGeometry(.4,.158,.02,.39),
        cells=n,gas_density_kg_m3=1.,
        gas_cp_J_kgK=1005.,gas_conductivity_W_mK=.034,
        rock_density_kg_m3=3700.,rock_cp_J_kgK=1100.,
        wall_UA_W_K=0.,solid_axial_conductivity_W_mK=0.)
    state=BedState((400.,)*n,(300.,)*n)
    v=bed.geometry.bed_volume_m3/n
    cf=v*bed.geometry.porosity*bed.gas_density_kg_m3*bed.gas_cp_J_kgK
    cs=v*(1-bed.geometry.porosity)*bed.rock_density_kg_m3*bed.rock_cp_J_kgK
    re=0.
    nu=2.0
    g=nu*bed.gas_conductivity_W_mK/bed.geometry.particle_diameter_m * (
        bed.geometry.specific_interfacial_area_m2_per_m3*v)
    weighted=(cf*400.+cs*300.)/(cf+cs)
    delta=100.*exp(-g*(1/cf+1/cs)*dt)
    exact_g=weighted+cs/(cf+cs)*delta
    exact_s=weighted-cf/(cf+cs)*delta
    actual=advance_bed(
        bed,state,inlet_K=300.,mass_flow_kg_s=0.,
        dt_s=dt,relative_tolerance=1e-10)
    assert actual.final_state.fluid_temperature_K[n//2]==pytest.approx(exact_g,abs=5e-5)
    assert actual.final_state.solid_temperature_K[n//2]==pytest.approx(exact_s,abs=5e-5)
    assert actual.heat_from_hot_gas_J==pytest.approx(0.,abs=1e-4)
    assert actual.heat_loss_to_ambient_J==pytest.approx(0.,abs=1e-4)
    assert bed_energy_J(bed,actual.final_state)==pytest.approx(
        bed_energy_J(bed,state),abs=.05)
    assert abs(actual.energy_residual_J)<.05


def test_nonuniform_isolated_exchange_cell_by_cell_exact():
    n=8
    bed=GasRockBed(geometry=PackedBedGeometry(.4,.158,.02,.39),
                   cells=n,gas_density_kg_m3=1.,wall_UA_W_K=0.)
    gas=tuple(380.+2*i for i in range(n))
    solid=tuple(290.+3*i for i in range(n))
    r=advance_bed(bed,BedState(gas,solid),inlet_K=300.,
                  mass_flow_kg_s=0.,dt_s=.1,relative_tolerance=1e-10)
    v=bed.geometry.bed_volume_m3/n
    cf=v*bed.geometry.porosity*bed.gas_density_kg_m3*bed.gas_cp_J_kgK
    cs=v*(1-bed.geometry.porosity)*bed.rock_density_kg_m3*bed.rock_cp_J_kgK
    g=2*bed.gas_conductivity_W_mK/bed.geometry.particle_diameter_m*(
        bed.geometry.specific_interfacial_area_m2_per_m3*v)
    for i in range(n):
        bar=(cf*gas[i]+cs*solid[i])/(cf+cs)
        delta=(gas[i]-solid[i])*exp(-g*(1/cf+1/cs)*.1)
        assert r.final_state.fluid_temperature_K[i]==pytest.approx(
            bar+cs/(cf+cs)*delta,abs=5e-5)
        assert r.final_state.solid_temperature_K[i]==pytest.approx(
            bar-cf/(cf+cs)*delta,abs=5e-5)
