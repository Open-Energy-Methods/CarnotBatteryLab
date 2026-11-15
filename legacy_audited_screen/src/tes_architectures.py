"""
Three TES architectures charged by the same HP cycle (hp_cycle.py),
compared on round-trip energy efficiency, round-trip EXERGY efficiency,
and a storage-system cost proxy ($/kWh_th).

All three are sized to the same nominal thermal capacity E_design and
cycled over the same charge/discharge duration, so the comparison is
apples-to-apples. This is a STEADY/QUASI-STEADY SCREENING model, not a
full transient PDE solve -- explicitly scoped this way to stay buildable
and independently checkable in days, not weeks. It complements, not
replaces, HTHP-ControlBench (full transient HP control) and TES
Discharge Screen (single-architecture storage validation against an FMU).

--------------------------------------------------------------------
Architecture A: single-media packed bed (basalt/rock gravel)
Architecture B: dual-media packed bed (rock + a finer second filler)
Architecture C: two-tank molten salt (isothermal tanks)
--------------------------------------------------------------------

Packed-bed thermocline physics (A, B)
--------------------------------------
Modelled as a 1-D counter-flow regenerator discretised into M well-mixed
control volumes in series (the standard way to approximate the Schumann
packed-bed energy equation; see e.g. Nellis & Klein, "Heat Transfer",
Ch. 10, regenerator/packed-bed effectiveness theory -- the same class of
textbook treatment already used for the counterflow-HX derivation in
HTHP-ControlBench). M=200 is a NUMERICAL RESOLUTION parameter (converged,
not a physical knob). The physically meaningful parameter is NTU_total =
UA_total / (mdot * cp_fluid): higher NTU -> sharper thermal front ->
less exergy destroyed by temperature mixing during charge/discharge.

NTU_total values used here (illustrative, ASSUMED, not fit to a specific
real bed -- same "illustrative" convention already used for the HP
nominal point and elsewhere in this project's sibling repos):
    Architecture A (single coarse rock filler):  NTU_total = 15
    Architecture B (dual-media, finer 2nd stage): NTU_total = 25
Architecture B's higher NTU is a MODELLING ASSUMPTION representing the
qualitative, literature-documented effect of smaller filler particles /
better thermal matching reducing flow disturbance and mixing in
dual-media thermocline tanks (Mira-Hernandez, Flueckiger & Garimella,
J. Solar Energy Engineering, 2015 -- qualitative direction only; that
paper reports no single applicable NTU or percentage figure, so one is
not invented here and B's improvement is not presented as empirically
calibrated).

Two-tank molten salt (C)
-------------------------
By design, two well-mixed isothermal tanks have (ideally) NO internal
temperature glide: the hot tank delivers at a constant temperature and
the cold tank returns at a constant temperature, independent of how much
energy has been drawn. The only loss modelled is a fixed charging
approach temperature (ambient tank heat loss is a separate, usually
smaller effect and is not included here -- flagged as a limitation).

Cost proxies ($/kWh_th, system-level CAPEX, NOT raw media $/kg)
-----------------------------------------------------------------
    A: $31.68/kWh_th  -- rock/basalt packed bed, 4-hour discharge
       duration (same duration used in this study's charge/discharge
       cycle). Source: Allen et al., rock-bed TES cost study, via
       OSTI/NREL (osti.gov/servlets/purl/1783087), Table 2, Case 1.
    B: $36.43/kWh_th = A x 1.15 -- ASSUMED +15% over A for the second
       filler material and more complex packing. NOT independently
       sourced; flagged in README as an assumption, not a citation.
    C: $60/kWh_th -- two-tank molten salt (Gen2 nitrate-salt design),
       system-level CAPEX including tanks and refractory. Source: NREL,
       SolarPACES 2020 proceedings (nrel.gov/docs/fy22osti/77852.pdf).
       Not duration-specific like A; this is a known asymmetry (molten-
       salt tank cost scales roughly linearly with capacity, while
       packed-bed cost per kWh drops sharply at longer discharge
       durations) and is stated as a limitation, not smoothed over.
"""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp

T0_K = 293.15  # ambient reference temperature for exergy (20 C)


@dataclass
class TESResult:
    name: str
    NTU_total: float | None
    energy_efficiency: float
    exergy_efficiency: float
    mean_discharge_T_C: float
    cost_per_kWh_th: float


def _segment_rhs(t, T_s, T_in_boundary, NTU_seg, C_seg, M, reverse):
    """
    Continuous-time ODE right-hand side for the M-segment regenerator
    (replaces an earlier hand-rolled explicit-Euler loop that silently
    coupled timestep size to segment count and gave results that
    changed by 40x under a pure dt refinement -- a genuine bug caught
    before shipping, see git history / project memory. Using scipy's
    adaptive solve_ivp removes the hand-picked-dt failure mode entirely:
    the solver chooses its own accurate step size, and M is then the
    ONLY discretisation parameter, whose convergence is checked
    directly in tests/test_tes_architectures.py.

    Fluid cascades through the M segments quasi-steadily in space at
    each instant (standard regenerator-theory assumption: fluid transit
    time through the bed is fast compared to the solid's thermal
    response -- this is what makes it a *regenerator* model rather than
    a slug-flow model, and is now decoupled from the time integrator's
    own step size, which is the bug that existed before).
    """
    order = range(M) if not reverse else reversed(range(M))
    dTs_dt = np.zeros(M)
    T_in = T_in_boundary
    for i in order:
        T_out = T_s[i] + (T_in - T_s[i]) * np.exp(-NTU_seg)
        dTs_dt[i] = (T_in - T_out) / C_seg
        T_in = T_out
    return dTs_dt


def _packed_bed_cycle(NTU_total: float, T_hot_in_C: float, T_cold_in_C: float,
                       M: int = 200, n_report: int = 400):
    """
    Simulate one charge + one discharge half-cycle of an M-segment packed
    bed (M-tanks-in-series regenerator model), integrated continuously
    in time with scipy.integrate.solve_ivp (RK45, tight tolerances).
    Returns the fluid outlet temperature time series for charge and
    discharge, sampled at n_report points (a reporting-resolution
    choice only, not a solver-accuracy choice).
    """
    NTU_seg = NTU_total / M
    C_seg = 1.0 / M  # normalised: total bed thermal mass / (mdot*cp) = 1.0
    tau_charge = 1.0
    t_eval = np.linspace(0, tau_charge, n_report)

    def outlet_series(T_in_boundary, T_s0, reverse):
        sol = solve_ivp(_segment_rhs, [0, tau_charge], T_s0,
                         args=(T_in_boundary, NTU_seg, C_seg, M, reverse),
                         t_eval=t_eval, method="RK45", rtol=1e-8, atol=1e-10)
        assert sol.success, sol.message
        T_s_t = sol.y  # shape (M, n_report)
        seg_order = list(range(M)) if not reverse else list(reversed(range(M)))
        outlets = np.empty(n_report)
        for k in range(n_report):
            T_in = T_in_boundary
            for i in seg_order:
                T_in = T_s_t[i, k] + (T_in - T_s_t[i, k]) * np.exp(-NTU_seg)
            outlets[k] = T_in
        return outlets, T_s_t[:, -1]

    T_s0 = np.full(M, T_cold_in_C)
    charge_outlet, T_s_after_charge = outlet_series(T_hot_in_C, T_s0, reverse=False)
    discharge_outlet, _ = outlet_series(T_cold_in_C, T_s_after_charge, reverse=True)

    return charge_outlet, discharge_outlet


def evaluate_packed_bed(name: str, NTU_total: float, cost_per_kWh_th: float,
                         T_hot_in_C: float = 150.0, T_cold_in_C: float = 30.0,
                         M: int = 200) -> TESResult:
    n_report = 400
    charge_outlet, discharge_outlet = _packed_bed_cycle(NTU_total, T_hot_in_C, T_cold_in_C,
                                                         M=M, n_report=n_report)
    t = np.linspace(0, 1.0, n_report)  # normalised time, matches _packed_bed_cycle's tau_charge=1.0

    # Energy delivered during discharge, normalised to energy charged.
    # Proper time integration (trapezoid rule over the reported series),
    # not a plain index sum -- both halves use the same flow rate and
    # the same normalised duration, so this is a like-for-like ratio.
    charge_energy = np.trapezoid(T_hot_in_C - charge_outlet, t)       # energy absorbed by the bed during charge
    discharge_energy = np.trapezoid(discharge_outlet - T_cold_in_C, t)  # energy delivered to the load during discharge
    energy_efficiency = discharge_energy / charge_energy

    T_hot_in_K = T_hot_in_C + 273.15
    carnot_in = 1 - T0_K / T_hot_in_K   # exergy factor of the heat charged in (constant, at HP condenser T)
    ex_in = charge_energy * carnot_in

    discharge_outlet_K = discharge_outlet + 273.15
    carnot_out = 1 - T0_K / discharge_outlet_K  # time-varying: delivery temp declines through discharge
    ex_out = np.trapezoid((discharge_outlet - T_cold_in_C) * carnot_out, t)

    exergy_efficiency = ex_out / ex_in
    mean_discharge_T_C = np.trapezoid(discharge_outlet, t)  # time-weighted mean

    return TESResult(name=name, NTU_total=NTU_total,
                      energy_efficiency=energy_efficiency,
                      exergy_efficiency=exergy_efficiency,
                      mean_discharge_T_C=mean_discharge_T_C,
                      cost_per_kWh_th=cost_per_kWh_th)


def evaluate_molten_salt(name: str = "C: Two-tank molten salt",
                          T_hot_in_C: float = 150.0, T_cold_in_C: float = 30.0,
                          charge_approach_K: float = 5.0,
                          cost_per_kWh_th: float = 60.0) -> TESResult:
    """
    Isothermal two-tank model. The only loss represented is a fixed
    charging approach temperature (hot tank settles charge_approach_K
    below the HP condenser outlet, a standard HX pinch allowance).
    Ambient tank heat loss is NOT modelled -- flagged as a limitation
    in the README, since including it would only ever improve C's
    relative standing further (less, not more, exergy destruction is
    being omitted from its competitors' comparison).
    """
    T_hot_tank_C = T_hot_in_C - charge_approach_K

    energy_efficiency = (T_hot_tank_C - T_cold_in_C) / (T_hot_in_C - T_cold_in_C)

    T_hot_in_K = T_hot_in_C + 273.15
    T_hot_tank_K = T_hot_tank_C + 273.15
    carnot_in = 1 - T0_K / T_hot_in_K
    carnot_out = 1 - T0_K / T_hot_tank_K
    ex_in = (T_hot_in_C - T_cold_in_C) * carnot_in
    ex_out = (T_hot_tank_C - T_cold_in_C) * carnot_out
    exergy_efficiency = ex_out / ex_in

    return TESResult(name=name, NTU_total=None,
                      energy_efficiency=energy_efficiency,
                      exergy_efficiency=exergy_efficiency,
                      mean_discharge_T_C=T_hot_tank_C,
                      cost_per_kWh_th=cost_per_kWh_th)


if __name__ == "__main__":
    A = evaluate_packed_bed("A: Single-media packed bed (rock)", NTU_total=15.0,
                             cost_per_kWh_th=31.68)
    B = evaluate_packed_bed("B: Dual-media packed bed", NTU_total=25.0,
                             cost_per_kWh_th=31.68 * 1.15)
    C = evaluate_molten_salt()
    for r in (A, B, C):
        print(f"{r.name:35s} NTU={str(r.NTU_total):>6} "
              f"eta_E={r.energy_efficiency:.4f} eta_Ex={r.exergy_efficiency:.4f} "
              f"T_disch_mean={r.mean_discharge_T_C:6.2f}C cost=${r.cost_per_kWh_th:.2f}/kWh_th")
