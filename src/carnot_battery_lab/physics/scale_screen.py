"""Hypothetical parallel-module sizing; not a plant design."""
import math

def convergence(values,ratio=2.):
    """Three-level observed order/GCI; reject oscillating or divergent sequences."""
    a,b,c=map(float,values)
    if not all(math.isfinite(x) for x in (a,b,c,ratio)) or ratio<=1:raise ValueError("invalid sequence")
    d1,d2=a-b,b-c
    if d1==0 or d2==0 or d1*d2<=0 or abs(d2)>=abs(d1):
        return dict(status="order_unresolved",fine=c,observed_order=None,gci_absolute=None)
    p=math.log(abs(d1/d2))/math.log(ratio)
    return dict(status="monotone_triplet",fine=c,observed_order=p,
                gci_absolute=1.25*abs(d2)/(ratio**p-1))

def module_screen(duty_W,delta_h_J_kg,cycle_electric_J,cooler_J,*,plant_W=1e6,
                  charge_s=1200.,discharge_s=600.,water_dp_Pa=100000.,
                  pump_eff=.65,coolant_delta_T_K=10.,coolant_cp=4180.,
                  coolant_dp_Pa=100000.,coolant_rho=970.,water_rho=930.,cooler_peak_W=None):
    vals=(duty_W,delta_h_J_kg,cycle_electric_J,plant_W,charge_s,discharge_s,water_dp_Pa,pump_eff,
          coolant_delta_T_K,coolant_cp,coolant_dp_Pa,coolant_rho,water_rho)
    if any(not math.isfinite(x) or x<=0 for x in vals) or not 0<pump_eff<=1 or not math.isfinite(cooler_J) or cooler_J<0:
        raise ValueError("invalid sizing inputs")
    n=math.ceil(plant_W/duty_W)
    flow=n*duty_W/delta_h_J_kg
    pump=flow/water_rho*water_dp_Pa/pump_eff
    coolant_mass=n*cooler_J/(coolant_cp*coolant_delta_T_K)
    coolant_pump_J=coolant_mass/coolant_rho*coolant_dp_Pa/pump_eff
    return dict(parallel_modules=n,nominal_discharge_W=n*duty_W,water_flow_kg_s=flow,
        water_pump_W=pump,coolant_mass_per_discharge_kg=coolant_mass,
        coolant_pump_energy_J=coolant_pump_J,coolant_average_flow_kg_s=coolant_mass/discharge_s,
        coolant_peak_W=cooler_peak_W,modeled_cycle_electric_J=n*cycle_electric_J+pump*discharge_s+coolant_pump_J,
        delivered_heat_J=n*duty_W*discharge_s,charge_window_s=charge_s,
        discharge_window_s=discharge_s,continuous_service=False,
        header_losses_included=False,hardware_qualified=False,industrial_service_qualified=False)
