import pytest
from carnot_battery_lab.physics.thermal_retention import MainHeatLoss,ThermalBuffer
from carnot_battery_lab.physics.retention_refinement import compare,preferred_capacity

def sample(h=3):
    return dict(case=str(h),heater_per_bank_MW=h,cooler_cap_W=0.,main_heat_loss_assumptions=None,eligible=True,
        mean_electric_W=1058000.,raw_margin_K=29.,peak_thermal_K=462.,sampled_peak_electric_W=3500000.)

def test_confirmed_and_tied_capacity():
    a,b=sample(),sample(5)
    assert compare(a,a)["pass_screen"]
    assert preferred_capacity(a,b,confirmed_low=True,confirmed_high=True)=="3"
    assert preferred_capacity(a,b,confirmed_low=False,confirmed_high=True)=="5"
    assert preferred_capacity(a,b,confirmed_low=False,confirmed_high=False) is None

@pytest.mark.parametrize("key,value",[("eligible",False),("mean_electric_W",1100000.),("raw_margin_K",27.),("peak_thermal_K",464.),("sampled_peak_electric_W",4000000.)])
def test_reject_refinement_difference(key,value):
    a,b=sample(),sample();b[key]=value
    assert not compare(a,b)["pass_screen"]

def test_invalid_heat_leak():
    with pytest.raises(ValueError):MainHeatLoss(-1.,0.,0.)
    with pytest.raises(ValueError):compare(sample(),sample(5))

@pytest.mark.parametrize("buffer",[False,True])
def test_coupled_main_loss_ledgers(buffer):
    pytest.importorskip("CoolProp");pytest.importorskip("numpy");pytest.importorskip("scipy")
    from dataclasses import replace
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    c=ClosedCycle();c=replace(c,charge_s=120.,discharge_s=60.,train=replace(c.train,bed_cells=2,hx_cells=2))
    b=ThermalBuffer(5000.,100.,.1) if buffer else None
    loss=MainHeatLoss(.6,.2,.2)
    x=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=2,process_duty_W=1000.,
                      cooler_cap_W=0.,recuperator=b,main_heat_loss=loss)
    for row in x["cycle_records"]:
        for ph in ("charge","discharge"):
            z=row[ph]
            assert z["main_rock_ambient_heat_J"]>0.
            assert z["main_wall_ambient_heat_J"]>0.
            assert z["main_return_ambient_heat_J"]>0.
            assert z["main_ambient_heat_J"]==pytest.approx(sum(z[k] for k in ("main_rock_ambient_heat_J","main_wall_ambient_heat_J","main_return_ambient_heat_J")))
            assert abs(z["electrical_boundary_residual_J"])<.2
            assert max(abs(y) for y in z["component_thermal_residuals_J"].values())<.2
