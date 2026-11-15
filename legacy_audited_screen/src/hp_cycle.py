"""
Single-stage vapour-compression heat pump cycle, used to charge the TES
architectures compared in this project.

Refrigerant: R1233zd(E) (same fluid independently verified for real-fluid
HTHP cycle screening in the HTHP-ControlBench WP7 study). Critical point
(CoolProp 8.0.0): Tcrit = 165.71 C, Pcrit = 3.583 MPa.

Nominal operating point (illustrative, chosen for this screening study,
NOT fit to any specific real plant):
    T_evap = 70 C   (waste-heat source, saturated vapour leaves evaporator)
    T_cond = 150 C  (TES charging temperature, saturated liquid leaves
                     condenser)
    eta_is = 0.70   (isentropic compressor efficiency, typical mid-range
                     value for a single-stage high-lift HP compressor)

Cycle: 1 = saturated vapour at T_evap -> 2 = compressed vapour at P_cond
(via isentropic efficiency) -> 3 = saturated liquid at T_cond ->
4 = throttled (isenthalpic) back to P_evap -> 1.

COP_heating = (h2 - h3) / (h2 - h1)

This module only computes the HP side. It is shared identically across
all three TES architectures in compare.py, so differences in the
comparison come only from the storage side, not from re-tuning the HP.
"""
from dataclasses import dataclass
import CoolProp.CoolProp as CP

FLUID = "R1233zd(E)"


@dataclass
class HPCycleResult:
    T_evap_C: float
    T_cond_C: float
    eta_is: float
    P_evap_Pa: float
    P_cond_Pa: float
    h1: float
    h2s: float
    h2: float
    h3: float
    h4: float
    w_comp: float          # specific compressor work, J/kg
    q_cond: float          # specific condenser heat rejected, J/kg
    q_evap: float          # specific evaporator heat absorbed, J/kg
    COP_heating: float
    COP_cooling: float


def solve_hp_cycle(T_evap_C: float = 70.0, T_cond_C: float = 150.0,
                    eta_is: float = 0.70) -> HPCycleResult:
    T_evap = T_evap_C + 273.15
    T_cond = T_cond_C + 273.15

    P_evap = CP.PropsSI("P", "T", T_evap, "Q", 1, FLUID)
    P_cond = CP.PropsSI("P", "T", T_cond, "Q", 1, FLUID)

    # State 1: saturated vapour leaving evaporator
    h1 = CP.PropsSI("H", "T", T_evap, "Q", 1, FLUID)
    s1 = CP.PropsSI("S", "T", T_evap, "Q", 1, FLUID)

    # State 2s: isentropic compression to P_cond
    h2s = CP.PropsSI("H", "P", P_cond, "S", s1, FLUID)

    # State 2: actual compression (isentropic efficiency)
    w_comp_ideal = h2s - h1
    w_comp = w_comp_ideal / eta_is
    h2 = h1 + w_comp

    # State 3: saturated liquid leaving condenser
    h3 = CP.PropsSI("H", "T", T_cond, "Q", 0, FLUID)

    # State 4: isenthalpic throttle back to P_evap
    h4 = h3

    q_cond = h2 - h3       # heat rejected at condenser (delivered to TES charge loop)
    q_evap = h1 - h4        # heat absorbed at evaporator

    COP_heating = q_cond / w_comp
    COP_cooling = q_evap / w_comp

    return HPCycleResult(
        T_evap_C=T_evap_C, T_cond_C=T_cond_C, eta_is=eta_is,
        P_evap_Pa=P_evap, P_cond_Pa=P_cond,
        h1=h1, h2s=h2s, h2=h2, h3=h3, h4=h4,
        w_comp=w_comp, q_cond=q_cond, q_evap=q_evap,
        COP_heating=COP_heating, COP_cooling=COP_cooling,
    )


if __name__ == "__main__":
    r = solve_hp_cycle()
    print(f"T_evap={r.T_evap_C} C  T_cond={r.T_cond_C} C  eta_is={r.eta_is}")
    print(f"P_evap={r.P_evap_Pa/1e6:.4f} MPa  P_cond={r.P_cond_Pa/1e6:.4f} MPa")
    print(f"w_comp={r.w_comp/1e3:.2f} kJ/kg  q_cond={r.q_cond/1e3:.2f} kJ/kg  q_evap={r.q_evap/1e3:.2f} kJ/kg")
    print(f"COP_heating={r.COP_heating:.3f}  COP_cooling={r.COP_cooling:.3f}")
    # First-law closure check
    closure_err = abs((r.q_cond) - (r.w_comp + r.q_evap)) / r.q_cond
    print(f"First-law closure error: {closure_err:.2e}")
