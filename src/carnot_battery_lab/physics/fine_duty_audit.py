"""Discrete two-grid capacity screen, not asymptotic GCI or qualification."""
import math
from .scale_screen import module_screen

def compare_pair(a,b):
    if a["duty_W"]!=b["duty_W"] or a["cells"]!=12 or b["cells"]!=16 or a["step_s"]!=b["step_s"]:
        raise ValueError("expected matched 12/16 cell pair")
    if not all(math.isfinite(x[k]) for x in (a,b) for k in ("electric_J","raw_margin_K","peak_cooler_W")):
        raise ValueError("nonfinite diagnostics")
    if min(a["electric_J"],b["electric_J"])<=0:
        raise ValueError("nonpositive input")
    energy=abs(a["electric_J"]-b["electric_J"])/b["electric_J"]
    margin=abs(a["raw_margin_K"]-b["raw_margin_K"])
    cooler=abs(a["peak_cooler_W"]-b["peak_cooler_W"])/max(1.,b["peak_cooler_W"])
    return dict(duty_W=a["duty_W"],both_full=bool(a["full"] and b["full"]),
                electric_relative_difference=energy,raw_margin_difference_K=margin,
                cooler_peak_relative_difference=cooler,
                screening_pass=bool(a["full"] and b["full"] and min(a["raw_margin_K"],b["raw_margin_K"])>=0
                and energy<=.02 and margin<=1. and cooler<=.05))

def size_candidate(v):
    if not v["full"] or v["raw_margin_K"]<0:
        raise ValueError("screening requires positive full service")
    s=module_screen(v["duty_W"],v["duty_W"]/v["water_flow"],v["electric_J"],v["cooler_J"],
                    cooler_peak_W=v["peak_cooler_W"])
    n=s["parallel_modules"]
    peak=n*v["peak_cooler_W"]
    coolant_flow=peak/(4180.*10.)
    s.update(plant_coincident_peak_cooler_W=peak,plant_peak_coolant_flow_kg_s=coolant_flow,
             assumed_peak_coolant_pump_W=coolant_flow/970.*100000./.65,
             plant_coincident_peak_blower_electric_W=n*v["peak_blower_electric_W"],
             installed_heater_W=n*5000.,
             bed_bulk_volume_m3=n*math.pi*.3**2/4*.5,
             rock_mass_kg=n*math.pi*.3**2/4*.5*.6*2600.,
             hx_UA_W_K=n*120.,
             peak_basis="accepted numerical nodes, synchronous modules, not continuous bound",
             sizing_basis="hypothetical screened module, not qualified equipment")
    return s
