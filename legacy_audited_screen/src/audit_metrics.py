"""Independent thermodynamic audit for the legacy packed-bed screen.

This module intentionally does NOT reuse the original TESResult.exergy_efficiency
or electricity-per-exergy formulas. It computes heat-transfer-fluid flow-exergy
changes for a constant-cp fluid, using the original solved temperature histories.

The physical system remains NOT validated: no pressure drops, HX pinch dynamics,
geometry, periodic-cycle closure, heat-pump feedback, or minimum delivery-temperature
criterion. These are illustrative diagnostic calculations, not design predictions.
"""

from dataclasses import dataclass
import numpy as np
from scipy.integrate import trapezoid
from tes_architectures import _packed_bed_cycle

T_REF_K = 293.15
T_COLD_C = 30.0
T_HOT_C = 150.0
LEGACY_COP = 2.123  # Historical external result, NOT verified in this environment.


def flow_exergy_delta(T_hi_C, T_lo_C, ambient_K=T_REF_K):
    """b(hi)-b(lo) / cp for constant-cp, incompressible-flow streams.

    Units: kelvin-equivalent (multiply by mdot*cp*duration for energy).
    The expression is (T_hi - T_lo) - T0 ln(T_hi/T_lo), all in kelvin.
    Temperature arrays are supported; positive output requires hi > lo > 0K
    and thermodynamically meaningful boundary conditions.
    """
    high = np.asarray(T_hi_C, dtype=float) + 273.15
    low = np.asarray(T_lo_C, dtype=float) + 273.15
    if np.any(low <= 0) or np.any(high <= 0):
        raise ValueError("Absolute temperatures must be > 0 K")
    if np.any(high < low):
        raise ValueError("High boundary temperature must be >= low")
    return (high - low) - ambient_K * np.log(high / low)


@dataclass(frozen=True)
class PackedBedAudit:
    case: str
    ntu: float
    charge_heat: float
    recovered_heat: float
    recovery_fraction: float
    charge_exergy: float
    recovered_exergy: float
    stream_exergy_ratio: float
    delivered_exergy_per_charged_heat: float
    electrical_input_per_delivered_exergy: float


def audit_packed_bed(case: str, ntu: float, M: int = 200,
                     assumed_cop: float = LEGACY_COP) -> PackedBedAudit:
    """Audit one normalized single-charge, single-discharge history.

    Both thermal energy and flow-exergy metrics use the same constant-cp
    fluid with matched flow rates and half-cycle durations. The computed
    electricity metric assumes a shared HP with constant COP and perfect
    charge-loop heat matching -- neither is dynamically demonstrated.
    """
    if ntu <= 0 or M < 2 or assumed_cop <= 0:
        raise ValueError("NTU, M and COP must be positive (M >= 2)")
    charge_out, discharge_out = _packed_bed_cycle(
        ntu, T_HOT_C, T_COLD_C, M=M, n_report=400
    )
    time = np.linspace(0, 1, len(charge_out))
    charge_heat = float(trapezoid(T_HOT_C - charge_out, time))
    recovered_heat = float(trapezoid(discharge_out - T_COLD_C, time))
    charge_exergy = float(trapezoid(
        flow_exergy_delta(T_HOT_C, charge_out), time))
    recovered_exergy = float(trapezoid(
        flow_exergy_delta(discharge_out, T_COLD_C), time))
    if min(charge_heat, recovered_heat, charge_exergy, recovered_exergy) <= 0:
        raise ValueError("Nonpositive energy/exergy; check assumed operating conditions")
    return PackedBedAudit(
        case=case, ntu=ntu,
        charge_heat=charge_heat, recovered_heat=recovered_heat,
        recovery_fraction=recovered_heat / charge_heat,
        charge_exergy=charge_exergy, recovered_exergy=recovered_exergy,
        stream_exergy_ratio=recovered_exergy / charge_exergy,
        delivered_exergy_per_charged_heat=recovered_exergy / charge_heat,
        electrical_input_per_delivered_exergy=(charge_heat / assumed_cop) / recovered_exergy,
    )


def check_solar_salt_compatibility(T_cold_C: float, T_hot_C: float,
                                   conservative_freezing_C: float = 240.0):
    """Only for NaNO3-KNO3 solar salt, conservative liquidus guard (240 C)."""
    if T_cold_C >= T_hot_C:
        raise ValueError("Cold tank must be colder than hot tank")
    return (T_cold_C >= conservative_freezing_C
            and T_hot_C >= conservative_freezing_C)


def main():
    print("CORRECTIVE AUDIT — legacy screen results must not be treated as validated designs")
    print("Reference: incompressible constant-cp flow exergy, T0 = 293.15 K")
    print(f"Hypothetical fixed COP = {LEGACY_COP} (not independently checked here)\n")
    print(f"{'case':8} {'heat recovery':>14} {'stream Ex ratio':>16} {'elec / delivered Ex':>22}")
    for case, ntu in (("A", 15.0), ("B", 25.0)):
        r = audit_packed_bed(case, ntu)
        print(f"{case:8} {r.recovery_fraction:14.4f} {r.stream_exergy_ratio:16.4f} "
              f"{r.electrical_input_per_delivered_exergy:22.4f}")
    print("\nC: no comparable result. The originally cited high-temperature salt and")
    print("cost case are not compatible with the proposed 30–145 °C temperatures.")
    print("\nNo valid full-system Pareto frontier or architecture ranking is established.")


if __name__ == '__main__':
    main()
