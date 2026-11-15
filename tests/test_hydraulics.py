import math
import pytest
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry, ergun_pressure_drop_Pa,hydraulic_power_W


def test_bed_geometry_and_ergun_independent_hand_formula():
    bed=PackedBedGeometry(length_m=5,diameter_m=3,particle_diameter_m=.04,porosity=.4)
    assert bed.bed_volume_m3 == pytest.approx(math.pi*9/4*5)
    assert bed.specific_interfacial_area_m2_per_m3 == pytest.approx(90)
    u,rho,mu=.3,1.2,1.8e-5
    expected=5*(150*mu*(.6)**2*u/(.4**3*.04**2)+1.75*rho*.6*u**2/(.4**3*.04))
    assert ergun_pressure_drop_Pa(bed,u,rho,mu) == pytest.approx(expected)


def test_ergun_zero_flow_and_monotonicity():
    bed=PackedBedGeometry(5,3,.04,.4)
    assert ergun_pressure_drop_Pa(bed,0.,1.2,1.8e-5)==0
    assert ergun_pressure_drop_Pa(bed,.6,1.2,1.8e-5)>2*ergun_pressure_drop_Pa(bed,.3,1.2,1.8e-5)


def test_pump_power_and_geometry_validation():
    assert hydraulic_power_W(1e5,.02,.5)==pytest.approx(4000.)
    with pytest.raises(ValueError):PackedBedGeometry(1,1,0.5,0.4)
    with pytest.raises(ValueError):hydraulic_power_W(-1,.02,.5)
