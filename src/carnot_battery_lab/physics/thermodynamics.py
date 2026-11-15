"""Dimensionally explicit stream energy/exergy metrics (SI units).

Flow exergy assumes pressure differences and composition effects are either
accounted for separately or negligible when a constant-cp approximation is used.
Chemical exergy, kinetic and potential exergy are NOT included.
"""
from __future__ import annotations
import math


def thermal_stream_exergy_J_per_kg(
    t_hot_K: float, t_cold_K: float, ambient_K: float, cp_J_per_kgK: float
) -> float:
    """Physical flow-exergy difference for constant cp, fixed pressure.

    Δb = cp [(Th - Tc) - T0 ln(Th/Tc)], in J/kg.
    This may be negative for a temperature interval entirely below ambient;
    negative exergy *changes* are not silently rectified.
    """
    if not all(math.isfinite(x) for x in (t_hot_K, t_cold_K, ambient_K, cp_J_per_kgK)):
        raise ValueError("all temperatures and cp must be finite")
    if min(t_hot_K, t_cold_K, ambient_K, cp_J_per_kgK) <= 0:
        raise ValueError("Kelvin temperatures and cp must be strictly positive")
    if t_hot_K < t_cold_K:
        raise ValueError("hot stream boundary must be >= cold boundary")
    return cp_J_per_kgK * ((t_hot_K-t_cold_K) - ambient_K * math.log(t_hot_K/t_cold_K))


def specific_physical_flow_exergy_delta_J_per_kg(
    delta_h_J_per_kg: float, delta_s_J_per_kgK: float, ambient_K: float
) -> float:
    """Δb = Δh - T0 Δs, for common composition at consistent reference states."""
    if not all(math.isfinite(x) for x in (delta_h_J_per_kg, delta_s_J_per_kgK, ambient_K)) or ambient_K <= 0:
        raise ValueError("invalid specific exergy inputs")
    return delta_h_J_per_kg - ambient_K * delta_s_J_per_kgK


def electricity_per_useful_heat_kWh_per_kWh(
    electricity_kWh: float, useful_heat_kWh: float
) -> float:
    """Electricity consumed per certified useful process heat (not heat exergy)."""
    if not all(math.isfinite(x) for x in (electricity_kWh, useful_heat_kWh)):
        raise ValueError("non-finite energy")
    if electricity_kWh < 0 or useful_heat_kWh <= 0:
        raise ValueError("electricity must be nonnegative and useful heat positive")
    return electricity_kWh/useful_heat_kWh


def electrical_round_trip_efficiency(electricity_out_kWh: float, electricity_in_kWh: float) -> float:
    """Electrical-output/electrical-input only; never substitute heat for output."""
    if not all(math.isfinite(x) for x in (electricity_out_kWh, electricity_in_kWh)):
        raise ValueError("non-finite energy")
    if electricity_in_kWh <= 0 or electricity_out_kWh < 0:
        raise ValueError("invalid electricity flows")
    return electricity_out_kWh/electricity_in_kWh
