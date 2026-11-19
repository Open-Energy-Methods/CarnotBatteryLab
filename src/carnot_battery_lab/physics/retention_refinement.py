"""Predeclared zero-cooling numerical confirmation, not plant qualification."""
import math

def compare(candidate,reference):
    if candidate["heater_per_bank_MW"]!=reference["heater_per_bank_MW"] or candidate["cooler_cap_W"]!=reference["cooler_cap_W"] or candidate["main_heat_loss_assumptions"]!=reference["main_heat_loss_assumptions"]:
        raise ValueError("inconsistent refinement architecture")
    keys=("mean_electric_W","raw_margin_K","peak_thermal_K","sampled_peak_electric_W")
    if not all(math.isfinite(x[k]) for x in (candidate,reference) for k in keys) or min(candidate["mean_electric_W"],reference["mean_electric_W"],candidate["sampled_peak_electric_W"],reference["sampled_peak_electric_W"])<=0:
        raise ValueError("invalid diagnostics")
    e=abs(candidate["mean_electric_W"]-reference["mean_electric_W"])/reference["mean_electric_W"]
    m=abs(candidate["raw_margin_K"]-reference["raw_margin_K"])
    t=abs(candidate["peak_thermal_K"]-reference["peak_thermal_K"])
    p=abs(candidate["sampled_peak_electric_W"]-reference["sampled_peak_electric_W"])/reference["sampled_peak_electric_W"]
    return dict(both_eligible=bool(candidate["eligible"] and reference["eligible"]),
                mean_electric_relative_difference=e,raw_margin_difference_K=m,
                thermal_peak_difference_K=t,sampled_peak_electric_relative_difference=p,
                pass_screen=bool(candidate["eligible"] and reference["eligible"] and e<=.02 and m<=1. and t<=1. and p<=.05))

def preferred_capacity(low,high,*,confirmed_low,confirmed_high):
    """Prefer lower nameplate if both corroborated and mean electricity tied within 0.2%."""
    if low["heater_per_bank_MW"]>=high["heater_per_bank_MW"]:raise ValueError("invalid capacity order")
    if not confirmed_low:return high["case"] if confirmed_high else None
    if not confirmed_high:return low["case"]
    e=abs(low["mean_electric_W"]-high["mean_electric_W"])/high["mean_electric_W"]
    if e<=.002:return low["case"]
    return min((low,high),key=lambda x:x["mean_electric_W"])["case"]
