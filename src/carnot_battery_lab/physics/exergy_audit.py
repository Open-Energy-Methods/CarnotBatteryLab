"""M3.17 model-consistent physical-exergy accounting.

Reference is environment temperature T0. Fixed-volume air, solids and
walls use changes in U-T0*S; pressurised water inventory uses H-T0*S.
No chemical exergy, kinetic exergy, p0*dV, actual compressor map, or
unmeasured heat-exchanger pressure losses are inferred.

Component categories are explicitly identifiable thermal-transfer and
electric dissipation terms only. The *unallocated* remainder includes
gas hydraulics, unresolved control-volume mixing and thermodynamic-
property / numerical entropy defects; it is NOT a measured component.
"""
from __future__ import annotations
import math

LEDGER_KEYS=(
    "product_entropy_out_J_K",
    "hx_branch_entropy_out_J_K",
    "rock_gas_entropy_generated_J_K",
    "wall_gas_entropy_generated_J_K",
    "water_wall_entropy_generated_J_K",
    "cooler_entropy_generated_J_K",
    "heater_exergy_destroyed_J",
    "bypass_mixing_entropy_generated_J_K",
    "main_heat_leak_entropy_generated_J_K",
    "buffer_entropy_generated_J_K",
)

def finite_nonnegative_transport(q_W, hot_K, cold_K):
    """Sgen rate for signed heat from hot node to cold node.

    Signed heat flows and finite reservoir temperatures; always >=0 for
    passive Q=UA*(Thot-Tcold). Negative here is evidence of bad inputs.
    """
    if any(not math.isfinite(x) for x in (q_W,hot_K,cold_K)) or min(hot_K,cold_K)<=0:
        raise ValueError("invalid heat entropy calculation")
    return q_W*(1/cold_K-1/hot_K)

def close_exergy_ledger(*,T0_K,inventory_energy_change_J,inventory_entropy_change_J_K,
    heater_electric_J,heater_to_gas_J,blower_electric_J,blower_to_gas_J,
    process_heat_J,product_entropy_change_J_K,cooler_heat_J,cooler_sink_K,
    ambient_energy_by_temperature,identified_components_J):
    """Compare *independently* computed energy/entropy inventory to fluxes.

    Positive exergy destruction is not imposed: a negative result or
    negative unidentified remainder is reported as a diagnostic.
    """
    scalars=(T0_K,inventory_energy_change_J,inventory_entropy_change_J_K,
        heater_electric_J,heater_to_gas_J,blower_electric_J,blower_to_gas_J,
        process_heat_J,product_entropy_change_J_K,cooler_heat_J,cooler_sink_K)
    if not all(math.isfinite(x) for x in scalars) or min(T0_K,cooler_sink_K)<=0:
        raise ValueError("nonfinite exergy inputs")
    if not all(math.isfinite(q) and math.isfinite(t) and t>0 for q,t in ambient_energy_by_temperature):
        raise ValueError("invalid ambient heat boundaries")
    if not all(math.isfinite(v) for v in identified_components_J.values()):
        raise ValueError("nonfinite component exergy contributions")
    electric=heater_electric_J+blower_electric_J
    electric_loss=heater_electric_J-heater_to_gas_J+blower_electric_J-blower_to_gas_J
    Bwater=process_heat_J-T0_K*product_entropy_change_J_K
    Bcooler=cooler_heat_J*(1.-T0_K/cooler_sink_K)
    Bamb=sum(q*(1.-T0_K/t) for q,t in ambient_energy_by_temperature)
    dB=inventory_energy_change_J-T0_K*inventory_entropy_change_J_K
    D=electric-Bwater-Bcooler-Bamb-dB
    Sgen=(inventory_entropy_change_J_K+product_entropy_change_J_K+
        cooler_heat_J/cooler_sink_K+
        sum(q/t for q,t in ambient_energy_by_temperature)+electric_loss/T0_K)
    entropy_based=T0_K*Sgen
    closure=D-entropy_based
    scale=max(1.,abs(electric),abs(process_heat_J),abs(dB))
    if abs(closure)>2e-5*scale:
        raise RuntimeError("independent exergy/entropy accounting violates energy closure")
    identified=sum(identified_components_J.values())
    return dict(environment_K=T0_K,inventory_physical_exergy_change_J=dB,
        electric_input_exergy_J=electric,process_water_exergy_export_J=Bwater,
        cooler_export_to_assumed_sink_exergy_J=Bcooler,
        ambient_heat_export_exergy_J=Bamb,
        process_water_entropy_export_J_K=product_entropy_change_J_K,
        inventory_entropy_change_J_K=inventory_entropy_change_J_K,
        total_entropy_generation_J_K=Sgen,
        total_exergy_destruction_J=D,entropy_based_destruction_J=entropy_based,
        exergy_entropy_closure_residual_J=closure,
        identified_exergy_destruction_J=dict(identified_components_J),
        identified_total_J=identified,
        unresolved_gas_hydraulics_and_numerical_exergy_J=D-identified,
        allocation_is_complete=False,compressor_qualified=False,
        heat_pump_integrated=False,Carnot_battery_RTE=None)
