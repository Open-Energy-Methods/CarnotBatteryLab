import pytest
from carnot_battery_lab.physics.fine_duty_audit import compare_pair,size_candidate

def row(n):
    return dict(duty_W=1000.,cells=n,step_s=5.,full=True,electric_J=1800000.,
                raw_margin_K=2.,peak_cooler_W=3000.,water_flow=.00587,cooler_J=1100000.,
                peak_blower_electric_W=20.)

def test_two_grid_gate():
    a,b=row(12),row(16)
    assert compare_pair(a,b)["screening_pass"]
    b["raw_margin_K"]=-.01
    assert not compare_pair(a,b)["screening_pass"]

@pytest.mark.parametrize("k,x",[("full",False),("electric_J",2000000.),("raw_margin_K",.5),("peak_cooler_W",4000.)])
def test_detect_unsuitable_basis(k,x):
    a,b=row(12),row(16);b[k]=x
    assert not compare_pair(a,b)["screening_pass"]

def test_reject_unmatched_service():
    a,b=row(12),row(16);b["duty_W"]=1250.
    with pytest.raises(ValueError):compare_pair(a,b)

def test_peak_capacity_not_mean():
    s=size_candidate(row(16))
    assert s["parallel_modules"]==1000
    assert s["plant_coincident_peak_cooler_W"]==3000000.
    assert s["plant_peak_coolant_flow_kg_s"]>s["coolant_average_flow_kg_s"]
    assert not s["industrial_service_qualified"]
