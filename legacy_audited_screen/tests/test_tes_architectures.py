import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tes_architectures import evaluate_packed_bed, evaluate_molten_salt, _packed_bed_cycle


def test_energy_and_exergy_efficiency_never_exceed_one():
    for NTU in (5.0, 15.0, 25.0, 50.0):
        r = evaluate_packed_bed("test", NTU_total=NTU, cost_per_kWh_th=1.0)
        assert 0 < r.energy_efficiency <= 1.0 + 1e-9
        assert 0 < r.exergy_efficiency <= 1.0 + 1e-9
    r_salt = evaluate_molten_salt()
    assert 0 < r_salt.energy_efficiency <= 1.0
    assert 0 < r_salt.exergy_efficiency <= 1.0


def test_higher_ntu_improves_packed_bed_efficiency():
    low = evaluate_packed_bed("low", NTU_total=5.0, cost_per_kWh_th=1.0)
    mid = evaluate_packed_bed("mid", NTU_total=15.0, cost_per_kWh_th=1.0)
    high = evaluate_packed_bed("high", NTU_total=50.0, cost_per_kWh_th=1.0)
    assert low.energy_efficiency < mid.energy_efficiency < high.energy_efficiency
    assert low.exergy_efficiency < mid.exergy_efficiency < high.exergy_efficiency


def test_packed_bed_approaches_ideal_regenerator_as_M_and_NTU_both_grow():
    # At FIXED M=200, efficiency plateaus below 1 as NTU_total -> infinity
    # (finite-stage dispersion of the M-tanks-in-series approximation to
    # plug flow -- a known, expected artifact of this standard
    # discretisation, not a bug). Confirm it only approaches the true
    # ideal-regenerator limit of 1.0 when BOTH M and NTU_total grow
    # together, which is the correct diagnostic for this model class.
    plateau_200 = evaluate_packed_bed("M200", NTU_total=20000.0, cost_per_kWh_th=1.0, M=200)
    plateau_800 = evaluate_packed_bed("M800", NTU_total=20000.0, cost_per_kWh_th=1.0, M=800)
    assert plateau_200.energy_efficiency < plateau_800.energy_efficiency
    assert plateau_800.energy_efficiency > 0.985


def test_molten_salt_analytical_match():
    # Hand-derivable closed form: eta_E = (T_hot_in - approach - T_cold_in) / (T_hot_in - T_cold_in)
    r = evaluate_molten_salt(T_hot_in_C=150.0, T_cold_in_C=30.0, charge_approach_K=5.0)
    expected_eta_E = (150.0 - 5.0 - 30.0) / (150.0 - 30.0)
    assert abs(r.energy_efficiency - expected_eta_E) < 1e-9

    T0 = 293.15
    carnot_in = 1 - T0 / (150.0 + 273.15)
    carnot_out = 1 - T0 / (150.0 - 5.0 + 273.15)
    ex_in = (150.0 - 30.0) * carnot_in
    ex_out = (150.0 - 5.0 - 30.0) * carnot_out
    expected_eta_Ex = ex_out / ex_in
    assert abs(r.exergy_efficiency - expected_eta_Ex) < 1e-9


def test_discretisation_converged_in_segment_count():
    # M=200 (default) vs M=400 should agree closely at the operating
    # NTU_total=15 used for Architecture A -- confirms M is a
    # numerical-resolution choice at this operating point, not a
    # physically meaningful knob (unlike at very high NTU_total, see
    # test_packed_bed_approaches_ideal_regenerator_as_M_and_NTU_both_grow,
    # where M=200 is NOT yet converged -- this project only relies on
    # M=200 convergence at the actual NTU values it uses, 15 and 25).
    _, discharge_200 = _packed_bed_cycle(NTU_total=15.0, T_hot_in_C=150.0,
                                          T_cold_in_C=30.0, M=200)
    _, discharge_400 = _packed_bed_cycle(NTU_total=15.0, T_hot_in_C=150.0,
                                          T_cold_in_C=30.0, M=400)
    assert abs(discharge_200.mean() - discharge_400.mean()) < 0.5  # within 0.5 C


def test_molten_salt_has_highest_exergy_efficiency_of_the_three():
    # The architectural claim this project exists to check: isothermal
    # two-tank storage should beat both packed-bed variants on exergy
    # quality, at the illustrative NTU values chosen for A and B.
    A = evaluate_packed_bed("A", NTU_total=15.0, cost_per_kWh_th=31.68)
    B = evaluate_packed_bed("B", NTU_total=25.0, cost_per_kWh_th=36.43)
    C = evaluate_molten_salt()
    assert C.exergy_efficiency > B.exergy_efficiency > A.exergy_efficiency
    # ...but C is also the most expensive -- the actual trade-off
    assert C.cost_per_kWh_th > B.cost_per_kWh_th > A.cost_per_kWh_th
