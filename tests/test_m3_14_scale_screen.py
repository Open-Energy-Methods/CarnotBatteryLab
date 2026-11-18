import pytest
from carnot_battery_lab.physics.scale_screen import convergence,module_screen

def test_known_second_order():
    v=convergence([104.,101.,100.25])
    assert v["observed_order"]==pytest.approx(2.)
    assert v["gci_absolute"]==pytest.approx(.3125)

@pytest.mark.parametrize("v",[[1,2,1],[1,1,1],[1,2,4]])
def test_unresolved(v):
    assert convergence(v)["gci_absolute"] is None

def test_parallel_mass_and_auxiliary_energy():
    v=module_screen(500.,170000.,1000000.,100000.)
    assert v["parallel_modules"]==2000
    assert v["water_flow_kg_s"]==pytest.approx(1e6/170000.)
    assert v["modeled_cycle_electric_J"]>2e9
    assert v["delivered_heat_J"]==6e8
    assert not v["continuous_service"] and not v["hardware_qualified"]
