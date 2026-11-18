"""Independent pressure-driven bed prototype numerical controls.
All boundary data and heat-transfer parameters are hypothetical.
"""
import pytest
pytest.importorskip("CoolProp")

from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.real_air_bed_prototype import (
    RealAirBedAssumptions,ergun_face,run_real_air_bed,_tp_properties,
)


def _bed(n=4):
    return RealAirBedAssumptions(
        PackedBedGeometry(length_m=.5,diameter_m=.3,
                          particle_diameter_m=.01,porosity=.4),cells=n)


def test_ergun_face_pressure_sign_and_upwind_enthalpy():
    a=_bed()
    hot=_tp_properties(493.15,250100.)
    cold=_tp_properties(383.15,249900.)
    md,hd,M=ergun_face(hot,cold,a.geometry,.125)
    mr,hr,Mr=ergun_face(cold,hot,a.geometry,.125)
    assert md>0 and hd==pytest.approx(md*hot["h"])
    assert mr==pytest.approx(-md)
    assert hr==pytest.approx(-hd)
    assert 0<M<.1
    assert Mr==pytest.approx(M)


def test_zero_pressure_gradient_zero_face_mass_flow():
    a=_bed()
    hot=_tp_properties(493.15,250000.)
    cold=_tp_properties(383.15,250000.)
    assert ergun_face(hot,cold,a.geometry,.125)==pytest.approx((0,0,0),abs=1e-8)


def test_nonisothermal_pressure_driven_bed_conserves_gas_mass_and_energy():
    r=run_real_air_bed(_bed(),duration_s=10.)
    assert r["pressure_at_gas_cells_calculated_from_mass_and_internal_energy"]
    assert r["variable_air_enthalpy_density_and_viscosity_used"]
    assert all(x>0 for x in r["final_signed_face_mass_flow_kg_s"])
    assert r["solid_sensible_energy_change_J"]>0.
    assert r["final_gas_states"][0]["T"]>r["final_gas_states"][-1]["T"]
    assert abs(r["mass_first_law_residual_kg"])<1e-6
    assert abs(r["energy_first_law_residual_J"])<1.
    assert not r["coupled_HX_and_closed_loop_qualified"]
    assert not r["experimentally_validated"]


def test_reverse_flow_with_mirrored_boundaries_and_same_initial_state():
    a=_bed(3)
    x=run_real_air_bed(a,duration_s=4.,
                      left_T_K=493.15,left_P_Pa=250100.,
                      right_T_K=383.15,right_P_Pa=249900.)
    y=run_real_air_bed(a,duration_s=4.,
                      left_T_K=383.15,left_P_Pa=249900.,
                      right_T_K=493.15,right_P_Pa=250100.)
    assert [q["T"] for q in x["final_gas_states"]]==pytest.approx(
        [q["T"] for q in reversed(y["final_gas_states"])],abs=.002)
    assert x["final_signed_face_mass_flow_kg_s"]==pytest.approx(
        [-q for q in reversed(y["final_signed_face_mass_flow_kg_s"])],rel=.002)
    assert abs(y["mass_first_law_residual_kg"])<1e-6
    assert abs(y["energy_first_law_residual_J"])<1.


def test_closed_pressure_equilibrium_is_not_fake_gas_energy_gain():
    r=run_real_air_bed(_bed(3),duration_s=4.,
                      left_T_K=383.15,left_P_Pa=250000.,
                      right_T_K=383.15,right_P_Pa=250000.)
    assert r["final_total_gas_mass_kg"]==pytest.approx(
        r["initial_total_gas_mass_kg"],abs=1e-7)
    assert abs(r["energy_first_law_residual_J"])<1.
    assert abs(r["solid_sensible_energy_change_J"])<.1
