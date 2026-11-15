"""Transparent, unit-aware financial identities (not a cost-estimation model).

All costs must be normalized externally to common currency, price year, and
scope. This module deliberately does not hard-code any literature CAPEX.
"""
from __future__ import annotations
import math


def capital_recovery_factor(real_discount_rate: float, lifetime_years: int) -> float:
    if not math.isfinite(real_discount_rate) or real_discount_rate <= -1 or lifetime_years < 1:
        raise ValueError("discount rate and lifetime invalid")
    if abs(real_discount_rate) < 1e-14:
        return 1/lifetime_years
    r = real_discount_rate
    return r*(1+r)**lifetime_years/((1+r)**lifetime_years-1)


def levelized_cost_of_heat_per_MWh(
    capex_currency: float,
    annual_fixed_opex_currency: float,
    annual_variable_opex_currency: float,
    annual_qualified_heat_MWh: float,
    real_discount_rate: float,
    lifetime_years: int,
) -> float:
    """Equivalent-annual-cost LCOH for constant real annual flows.

    All costs must share currency and price year. The heat denominator is
    annual heat meeting process-temperature and availability criteria.
    """
    vals=(capex_currency,annual_fixed_opex_currency,annual_variable_opex_currency,annual_qualified_heat_MWh)
    if not all(math.isfinite(x) and x>=0 for x in vals) or annual_qualified_heat_MWh<=0:
        raise ValueError("invalid costs or delivered heat")
    annuity = capex_currency*capital_recovery_factor(real_discount_rate,lifetime_years)
    return (annuity + annual_fixed_opex_currency + annual_variable_opex_currency)/annual_qualified_heat_MWh
