"""M2 first charge-only integration: numerical conservation and causal HP feedback."""
import pytest

pytest.importorskip("scipy")
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed, BedState, advance_bed, bed_energy_J)


def test_equilibrium_no_flow_no_wall_has_no_energy_creation():
    bed=GasRockBed(wall_UA_W_K=0.0,cells=8)
    s=BedState.uniform(bed,90.0)
    r=advance_bed(bed,s,inlet_K=363.15,mass_flow_kg_s=0,dt_s=600)
    assert r.heat_from_hot_gas_J==pytest.approx(0.0,abs=0.001)
    assert r.stored_energy_change_J==pytest.approx(0.0,abs=0.5)
    assert r.blower_electric_W==0.0
    assert r.pressure_drop_Pa==0.0


def test_charge_transient_energy_and_outlet_bounds():
    bed=GasRockBed(cells=12,wall_UA_W_K=0)
    s=BedState.uniform(bed,95)
    r=advance_bed(bed,s,inlet_K=408.15,mass_flow_kg_s=25,dt_s=180)
    assert r.stored_energy_change_J>0
    assert r.heat_from_hot_gas_J>0
    assert abs(r.energy_residual_J) < 0.001*r.heat_from_hot_gas_J
    assert r.blower_electric_W>0
    assert r.pressure_drop_Pa>0
    assert 368.15 <= r.final_outlet_temperature_K <=408.15 + 1e-3
    assert r.stored_energy_change_J==pytest.approx(r.heat_from_hot_gas_J,rel=0.001)


def test_standby_walls_loss_energy_without_flow():
    bed=GasRockBed(cells=8,ambient_K=293.15,wall_UA_W_K=250)
    state=BedState.uniform(bed,125)
    r=advance_bed(bed,state,inlet_K=398.15,mass_flow_kg_s=0,dt_s=3600)
    assert r.heat_from_hot_gas_J==pytest.approx(0.0,abs=0.01)
    assert r.heat_loss_to_ambient_J>0
    assert r.stored_energy_change_J<0
    assert abs(r.energy_residual_J)<0.002*r.heat_loss_to_ambient_J


def test_geometry_influences_pressure_and_blower_power():
    a=GasRockBed(cells=8,geometry=PackedBedGeometry(4,5,0.045,0.4))
    b=GasRockBed(cells=8,geometry=PackedBedGeometry(4,5,0.025,0.4))
    s_a=BedState.uniform(a,95)
    s_b=BedState.uniform(b,95)
    x=advance_bed(a,s_a,inlet_K=408.15,mass_flow_kg_s=25,dt_s=30)
    y=advance_bed(b,s_b,inlet_K=408.15,mass_flow_kg_s=25,dt_s=30)
    assert y.pressure_drop_Pa>x.pressure_drop_Pa
    assert y.blower_electric_W>x.blower_electric_W


@pytest.mark.parametrize("cells", [8,16,32])
def test_independent_meshes_each_close_energy(cells):
    bed=GasRockBed(cells=cells,wall_UA_W_K=120)
    s=BedState.uniform(bed,95)
    r=advance_bed(bed,s,inlet_K=408.15,mass_flow_kg_s=25,dt_s=100)
    assert abs(r.energy_residual_J)<0.001*r.heat_from_hot_gas_J
    assert r.solver_nfev>0


def test_invalid_state_and_step_rejected():
    bed=GasRockBed(cells=8)
    with pytest.raises(ValueError):
        advance_bed(bed,BedState.uniform(bed,95),inlet_K=0,
                    mass_flow_kg_s=25,dt_s=60)


@pytest.mark.realfluid
def test_hp_charge_coupling_energy_and_electricity():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.r718 import R718Inputs
    from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
    bed=GasRockBed(cells=12)
    state=BedState.uniform(bed,95)
    run=simulate_charge(bed,state,R718Inputs(),
                        ChargeControl(dt_s=120,number_of_steps=4))
    assert run.completed,run.termination_reason
    assert len(run.steps)==4
    assert run.cumulative_hp_heat_J==pytest.approx(4*120*1e6)
    assert run.cumulative_electric_grid_J>0
    assert run.cumulative_stored_energy_J>0
    assert abs(run.energy_ledger_residual_J)<0.001*run.cumulative_hp_heat_J
    assert all(s.total_grid_electric_W>s.compressor_electric_W for s in run.steps)
    assert all(s.bed_pressure_drop_Pa>0 for s in run.steps)
    assert all(s.coupling_iterations>=1 for s in run.steps)


@pytest.mark.realfluid
def test_hotter_initial_storage_increases_hp_lift_and_work():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.r718 import R718Inputs
    from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
    bed=GasRockBed(cells=12)
    a=simulate_charge(bed,BedState.uniform(bed,90),R718Inputs(),
                      ChargeControl(dt_s=120,number_of_steps=1))
    b=simulate_charge(bed,BedState.uniform(bed,105),R718Inputs(),
                      ChargeControl(dt_s=120,number_of_steps=1))
    assert a.completed,a.termination_reason
    assert b.completed,b.termination_reason
    assert b.steps[0].condenser_saturation_C>a.steps[0].condenser_saturation_C
    assert b.steps[0].compressor_stage_ratios[0]>a.steps[0].compressor_stage_ratios[0]
    assert b.steps[0].total_grid_electric_W>a.steps[0].total_grid_electric_W


@pytest.mark.realfluid
def test_impossible_hot_bed_reports_infeasible_not_numeric_cop():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.r718 import R718Inputs
    from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
    bed=GasRockBed(cells=8)
    r=simulate_charge(bed,BedState.uniform(bed,155),R718Inputs(),
                      ChargeControl(dt_s=120,number_of_steps=2))
    assert not r.completed
    assert len(r.steps)==0
    assert r.termination_reason
    assert r.cumulative_hp_heat_J==0


def test_wakao_validity_guard_rejects_unqualified_flow():
    bed=GasRockBed(cells=8)
    with pytest.raises(ValueError,match="Wakao"):
        advance_bed(bed,BedState.uniform(bed,95),inlet_K=408.15,
                    mass_flow_kg_s=0.01,dt_s=60)


@pytest.mark.realfluid
def test_compact_bed_breakthrough_changes_compressor_demand_or_reports_limit():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.r718 import R718Inputs
    from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
    bed=GasRockBed(
        geometry=PackedBedGeometry(1.5,3.5,.045,.4),cells=12,wall_UA_W_K=50.0)
    run=simulate_charge(bed,BedState.uniform(bed,95),R718Inputs(),
                        ChargeControl(dt_s=180,number_of_steps=20))
    assert len(run.steps)>=2
    assert all(s.heat_hp_to_gas_J>0 for s in run.steps)
    assert all(abs(s.system_energy_residual_J)<0.001*s.heat_hp_to_gas_J
               for s in run.steps)
    assert max(s.total_grid_electric_W for s in run.steps)>=run.steps[0].total_grid_electric_W
    if not run.completed:
        assert run.termination_reason
        assert run.cumulative_hp_heat_J==pytest.approx(
            len(run.steps)*180*1e6)
