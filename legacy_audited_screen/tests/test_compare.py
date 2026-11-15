import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from compare import run_comparison


def test_three_architectures_returned_in_order():
    hp, results = run_comparison()
    names = [r.tes_name for r in results]
    assert names[0].startswith("A:")
    assert names[1].startswith("B:")
    assert names[2].startswith("C:")


def test_cost_and_exergy_quality_are_not_dominated():
    # The headline research finding: cheapest (A) is not also the best
    # on delivered-exergy-per-electricity, and vice versa for C -- i.e.
    # a genuine Pareto trade-off, not one architecture dominating.
    hp, results = run_comparison()
    by_cost = sorted(results, key=lambda r: r.cost_per_kWh_th)
    by_exergy_elec = sorted(results, key=lambda r: r.electricity_per_unit_exergy_delivered)
    assert by_cost[0].tes_name != by_exergy_elec[0].tes_name


def test_electricity_per_exergy_decreases_monotonically_with_exergy_efficiency():
    hp, results = run_comparison()
    ordered = sorted(results, key=lambda r: r.tes_exergy_efficiency)
    elec = [r.electricity_per_unit_exergy_delivered for r in ordered]
    assert elec[0] > elec[1] > elec[2]
