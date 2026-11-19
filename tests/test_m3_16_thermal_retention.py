import pytest
from carnot_battery_lab.physics.thermal_retention import ThermalBuffer,water_service_exergy,buffer_periodic_gate

def test_passive_buffer_phase_direction():
    b=ThermalBuffer(1000.,10.,2.,300.)
    assert b.rates(420.,400.,False)==(200.,0.,200.)
    assert b.rates(380.,400.,True)==(0.,200.,200.)
    assert b.rates(420.,400.,True)==(0.,0.,200.)
    assert b.rates(380.,400.,False)==(0.,0.,200.)

def test_invalid_and_exergy():
    with pytest.raises(ValueError):ThermalBuffer(0.,10.,2.)
    assert water_service_exergy(2.,100.,200.,1.,1.2,T0=300.)==pytest.approx(80.)

def test_buffer_periodicity_requires_state_and_ledger():
    def row(drift,returned):
        return dict(recuperator_cycle_end_change_K=drift,
            charge=dict(recuperator_returned_J=returned,recuperator_captured_J=0.,recuperator_ambient_loss_J=20.),
            discharge=dict(recuperator_returned_J=0.,recuperator_captured_J=returned+40.,recuperator_ambient_loss_J=20.))
    a=row(.01,1000.)
    assert not buffer_periodic_gate([a,a])
    assert buffer_periodic_gate([a,a,a])
    assert not buffer_periodic_gate([a,a,row(.1,1000.)])
    assert not buffer_periodic_gate([a,a,row(.01,2000.)])

@pytest.mark.parametrize("with_buffer",[False,True])
def test_dynamic_zero_cooling_and_buffer_conservation(with_buffer):
    pytest.importorskip("CoolProp");pytest.importorskip("numpy");pytest.importorskip("scipy")
    from dataclasses import replace
    from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
    c=ClosedCycle();c=replace(c,charge_s=120.,discharge_s=60.,train=replace(c.train,bed_cells=2,hx_cells=2))
    b=ThermalBuffer(5000.,100.,.1) if with_buffer else None
    x=run_closed_cycle(c,reverse_discharge=True,valve_loss_K=2.,cycles=2,process_duty_W=1000.,cooler_cap_W=0.,recuperator=b)
    for row in x["cycle_records"]:
        for phase in ("charge","discharge"):
            z=row[phase]
            assert z["cooler_heat_to_assumed_sink_J"]==0.
            assert z["peak_cooler_at_accepted_nodes_W"]==0.
            assert abs(z["recuperator_inventory_change_J"]-z["recuperator_captured_J"]+z["recuperator_returned_J"]+z["recuperator_ambient_loss_J"])<.01
            assert abs(z["electrical_boundary_residual_J"])<.2
        assert row["charge"]["recuperator_captured_J"]==0.
        assert row["discharge"]["recuperator_returned_J"]==0.
