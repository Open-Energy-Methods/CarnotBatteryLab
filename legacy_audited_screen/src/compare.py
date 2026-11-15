"""
Ties the HP cycle (hp_cycle.py) and the three TES architectures
(tes_architectures.py) together into the actual research question this
project exists to answer, as posed by the DTU/HeatMinds "High
Temperature Heat Pumps with Thermal Energy Storage" PhD posting: given
the SAME high-temperature heat pump charging the SAME nominal thermal
duty, how do single-media packed bed, dual-media packed bed and
two-tank molten salt storage compare on (1) electricity consumed per
unit of usable exergy delivered, and (2) storage system cost?

This is deliberately a STEADY-STATE, SINGLE-CYCLE SCREENING comparison,
not a dynamic/transient system study (that is what HTHP-ControlBench
already does for the HP side) and not a full annual-dispatch economic
optimisation. It isolates the one question storage architecture choice
actually changes for a fixed HP: how much of the exergy the HP works to
create each cycle is still usable exergy by the time it's drawn back
out of storage.
"""
from dataclasses import dataclass
import warnings
from hp_cycle import solve_hp_cycle
from tes_architectures import evaluate_packed_bed, evaluate_molten_salt


@dataclass
class ArchitectureComparison:
    tes_name: str
    cop_heating: float
    tes_energy_efficiency: float
    tes_exergy_efficiency: float
    electricity_per_unit_exergy_delivered: float  # kWh_elec per kWh_exergy delivered
    cost_per_kWh_th: float


def run_comparison():
    warnings.warn(
        'Legacy, nonphysical architecture-comparison metrics: exergy/electricity '
        'denominators are inconsistent and salt temperature/cost are infeasible. '
        'Do not cite these figures as design evidence; read docs/SCIENTIFIC_AUDIT_2026-11-15.md.',
        RuntimeWarning, stacklevel=2,
    )
    hp = solve_hp_cycle(T_evap_C=70.0, T_cond_C=150.0, eta_is=0.70)

    A = evaluate_packed_bed("A: Single-media packed bed (rock)", NTU_total=15.0,
                             cost_per_kWh_th=31.68)
    B = evaluate_packed_bed("B: Dual-media packed bed", NTU_total=25.0,
                             cost_per_kWh_th=31.68 * 1.15)
    C = evaluate_molten_salt()

    results = []
    for tes in (A, B, C):
        # Electricity per unit of THERMAL energy charged: 1/COP_heating.
        # Electricity per unit of EXERGY actually delivered at the far
        # end of storage = (1/COP_heating) / tes_exergy_efficiency --
        # i.e. how much electrical input the whole chain (HP + storage)
        # needs per unit of usable (exergy-weighted) heat the end user
        # actually receives. This is the single number that lets a
        # cheaper-but-leakier architecture (A) be fairly compared
        # against a pricier-but-near-ideal one (C).
        elec_per_th = 1.0 / hp.COP_heating
        elec_per_exergy_delivered = elec_per_th / tes.exergy_efficiency
        results.append(ArchitectureComparison(
            tes_name=tes.name, cop_heating=hp.COP_heating,
            tes_energy_efficiency=tes.energy_efficiency,
            tes_exergy_efficiency=tes.exergy_efficiency,
            electricity_per_unit_exergy_delivered=elec_per_exergy_delivered,
            cost_per_kWh_th=tes.cost_per_kWh_th,
        ))
    return hp, results


if __name__ == "__main__":
    hp, results = run_comparison()
    print(f"Shared HP cycle: R1233zd(E), T_evap=70C, T_cond=150C, eta_is=0.70, "
          f"COP_heating={hp.COP_heating:.3f}\n")
    print(f"{'Architecture':38s} {'eta_E':>7} {'eta_Ex':>7} {'elec/exergy':>12} {'$/kWh_th':>10}")
    for r in results:
        print(f"{r.tes_name:38s} {r.tes_energy_efficiency:7.4f} {r.tes_exergy_efficiency:7.4f} "
              f"{r.electricity_per_unit_exergy_delivered:12.4f} {r.cost_per_kWh_th:10.2f}")
    print()
    cheapest = min(results, key=lambda r: r.cost_per_kWh_th)
    best_exergy = min(results, key=lambda r: r.electricity_per_unit_exergy_delivered)
    print(f"Cheapest storage: {cheapest.tes_name} (${cheapest.cost_per_kWh_th:.2f}/kWh_th)")
    print(f"Lowest electricity-per-delivered-exergy: {best_exergy.tes_name} "
          f"({best_exergy.electricity_per_unit_exergy_delivered:.4f} kWh_elec/kWh_exergy)")
    if cheapest.tes_name != best_exergy.tes_name:
        print("-> No single architecture wins both axes: this is a genuine "
              "cost-vs-exergy-quality trade-off, not a dominated choice.")
