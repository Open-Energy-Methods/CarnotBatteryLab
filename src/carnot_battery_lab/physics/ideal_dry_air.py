"""Thermodynamically paired sensible enthalpy and cp for an IDEAL N2/O2 gas.

Individual N2 and O2 species Shomate coefficients (Chase 1998, JANAF) are
from the public NIST Chemistry WebBook SRD 69:
  N2: https://webbook.nist.gov/cgi/cbook.cgi?Formula=N2&cTG=on
  O2: https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Type=JANAFG

Assume 79% N2 + 21% O2 by MOLES. Ignore trace argon, CO2, H2O/humidity,
dissociation, nonideal pressure effects and changing composition. This
is a clearly declared idealised dry-air mixture, NOT a material property
measurement of the 2024 laboratory air stream.

cp_molar = A+B*t+C*t²+D*t³+E/t² [J/(mol K)], t=T/1000,
h_molar primitive = A*t+B*t²/2+C*t³/3+D*t⁴/4-E/t [kJ/mol].
We integrate each fitted segment independently across breakpoints, so
h(T) is CONTINUOUS and d h/dT = cp(T) piecewise. No arbitrary cp*deltaT
approximation is used in finite-volume energy balances.

Scoped to 298.15–1500 K for current research screens. The individual
fits cover wider intervals but this implementation is intentionally guarded.
"""
from __future__ import annotations
import math

T_REF_K=298.15
T_MIN_K=298.15
T_MAX_K=1500.
XN2=.79
XO2=.21
M_N2_KG_MOL=.0280134
M_O2_KG_MOL=.0319988
M_AIR_KG_MOL=XN2*M_N2_KG_MOL+XO2*M_O2_KG_MOL
# N2 100–500, 500–2000 K; O2 100–700, 700–2000 K
_N2_LOW=(28.98641,1.853978,-9.647459,16.63537,.000117)
_N2_HIGH=(19.50583,19.88705,-8.598535,1.369784,.527601)
_O2_LOW=(31.32234,-20.23531,57.86644,-36.50624,-.007374)
_O2_HIGH=(30.03235,8.772972,-3.988133,.788313,-.741599)


def _check(T:float)->None:
    if not math.isfinite(T) or not T_MIN_K<=T<=T_MAX_K:
        raise ValueError("N2/O2 ideal-mixture gas temperature outside fitted research domain 298.15..1500 K")


def _coeff(species:str,T:float)->tuple[float,...]:
    if species=="N2":
        return _N2_LOW if T<=500. else _N2_HIGH
    if species=="O2":
        return _O2_LOW if T<=700. else _O2_HIGH
    raise ValueError("only N2/O2 supported")


def _cp_shomate(T:float,coeff:tuple[float,...])->float:
    a,b,c,d,e=coeff
    t=T/1000
    return a+b*t+c*t*t+d*t*t*t+e/t**2


def _primitive_kJ_mol(T:float,coeff:tuple[float,...])->float:
    a,b,c,d,e=coeff
    t=T/1000
    return a*t+b*t*t/2+c*t**3/3+d*t**4/4-e/t


def air_cp_J_kgK(T_K:float)->float:
    _check(T_K)
    molar=(XN2*_cp_shomate(T_K,_coeff("N2",T_K))+
           XO2*_cp_shomate(T_K,_coeff("O2",T_K)))
    mass=molar/M_AIR_KG_MOL
    if mass<=0 or not math.isfinite(mass):
        raise ValueError("nonphysical mixture cp")
    return float(mass)


def _integral_species_kJ_mol(species:str,T_K:float)->float:
    if T_K==T_REF_K:
        return 0.
    cuts=(500.,) if species=="N2" else (700.,)
    knots=[T_REF_K]+[cut for cut in cuts if T_REF_K<cut<T_K]+[T_K]
    h=0.
    for a,b in zip(knots,knots[1:]):
        coeff=_coeff(species,(a+b)/2)
        h+=_primitive_kJ_mol(b,coeff)-_primitive_kJ_mol(a,coeff)
    return h


def air_sensible_enthalpy_J_kg(T_K:float)->float:
    """Specific sensible h referenced to 298.15K, not total combustion h."""
    _check(T_K)
    return float(1000.*(
        XN2*_integral_species_kJ_mol("N2",T_K)+
        XO2*_integral_species_kJ_mol("O2",T_K))/M_AIR_KG_MOL)


def air_mu_sutherland_Pa_s(T_K:float)->float:
    """Approximate viscosity scenario; not an experimental gas analyser."""
    _check(T_K)
    t0=273.15
    return 1.716e-5*(T_K/t0)**1.5*(t0+111.)/(T_K+111.)


def air_k_powerlaw_W_mK(T_K:float)->float:
    """Illustrative conductivity scaling; needs measured/cited transport data."""
    _check(T_K)
    return .0262*(T_K/300.)**.85
