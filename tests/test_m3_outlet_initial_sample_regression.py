"""Regression: initial outlet sample must be downstream in BOTH flow directions.

The old sample used the upstream (inlet) cell, which made the reverse-flow
industrial-grade gate look at x=L rather than the physical discharge outlet x=0.
These tests use deliberately nonuniform state fields to expose that error.
"""
import pytest

pytest.importorskip("scipy")
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import (
    BedState, GasRockBed, advance_bed,
)
from carnot_battery_lab.physics.reverse_flow_discharge import advance_reverse_discharge


def _bed():
    return GasRockBed(
        geometry=PackedBedGeometry(.4, .158, .02, .39),
        cells=8, gas_density_kg_m3=1., rock_density_kg_m3=3700.,
        rock_cp_J_kgK=1100., ambient_K=303.15, wall_UA_W_K=0.,
    )


def test_forward_first_temperature_is_outlet_end_not_inlet_end():
    bed=_bed()
    state=BedState(
        (450., 440., 430., 420., 410., 400., 390., 310.),
        (445., 435., 425., 415., 405., 395., 385., 315.),
    )
    r=advance_bed(bed, state, inlet_K=303.15,
                  mass_flow_kg_s=.01, dt_s=.5)
    assert r.first_temperature_K==state.fluid_temperature_K[-1]
    assert r.first_temperature_K!=state.fluid_temperature_K[0]


def test_reverse_flow_qualification_samples_true_process_outlet():
    bed=_bed()
    # Physical x=0 is the hot discharge outlet; x=L is the cold inlet.
    state=BedState(
        (450., 440., 430., 420., 410., 400., 390., 310.),
        (445., 435., 425., 415., 405., 395., 385., 315.),
    )
    r=advance_reverse_discharge(
        bed, state, return_gas_K=303.15, mass_flow_kg_s=.01,
        dt_s=.5, minimum_process_delivery_K=420.,
    )
    assert r.first_outlet_K==state.fluid_temperature_K[0]
    assert r.first_outlet_K!=state.fluid_temperature_K[-1]
    assert r.time_mean_outlet_K>420.
    assert r.final_outlet_K>420.
    assert r.screen_passed_temperature_samples is True
    assert r.qualified_process_heat_J>0.
