"""M3.20 finite gas preheater + electrical booster, coupled at the TES return.

Heat-pump COP at the 80C source is a *screening assumption*, not a
speed-dependent or calibrated compressor map. The HP is represented by
instantaneously available 150C water, finite U*A and bounded real-fluid
hot-water/gas/source-water enthalpy flows. No physical HP startup,
two-phase refrigerant inventory, gas-cooler transients or compressor
hardware qualification. The gas-side assumed K is a hydraulic penalty.
"""
from dataclasses import dataclass,asdict
import math

@dataclass(frozen=True)
class HPChargeInterface:
    hot_water_supply_C:float=150.
    hot_water_return_nominal_C:float=110.
    source_inlet_C:float=80.
    source_outlet_C:float=60.
    min_approach_K:float=5.
    gas_UA_W_K:float=50000.
    hp_thermal_nameplate_W:float=1e6
    hot_water_max_flow_kg_s:float=10.
    source_water_max_flow_kg_s:float=20.
    COP_electric_assumed:float=2.302054578653484
    gas_minor_loss_K:float=2.
    assumed_liquid_pressure_Pa:float=2e6
    assumed_pump_deltaP_Pa:float=1e5
    pump_efficiency:float=.65
    water_rho_kg_m3:float=950.

    def __post_init__(self):
        z=asdict(self)
        if any(isinstance(v,bool) or not math.isfinite(v) for v in z.values()):
            raise ValueError("nonfinite HP interface")
        if min(self.min_approach_K,self.gas_UA_W_K,self.hp_thermal_nameplate_W,
               self.hot_water_max_flow_kg_s,self.source_water_max_flow_kg_s,
               self.assumed_liquid_pressure_Pa,self.assumed_pump_deltaP_Pa,
               self.water_rho_kg_m3,self.pump_efficiency)>0:
            pass
        else:raise ValueError("invalid HP equipment assumptions")
        if not (self.source_inlet_C>self.source_outlet_C
                and self.hot_water_supply_C>self.hot_water_return_nominal_C
                and self.hot_water_supply_C>self.source_inlet_C
                and 1.<self.COP_electric_assumed<=12.
                and 0.<self.pump_efficiency<=1.
                and self.gas_minor_loss_K>=0.
                and self.hot_water_supply_C+self.min_approach_K<=160.):
            raise ValueError("outside reference OST compressor rating and source/sink scope")

    def split(self,*,charge,return_gas_T_K,return_gas_P_Pa,
              return_gas_h_J_kg,gas_mass_flow_kg_s,
              requested_gas_heating_W,resistance_heater_efficiency,
              props=None):
        """Return rate breakdown for physical energy and capacity constraints.

        Heater demand is the *existing* feedback's thermal demand.
        The HP supplies at most that demand. Extra booster electricity
        maintains exactly the same total return-gas energy injection.
        This is dynamic demand sharing but the HP side is steady idealised.
        """
        if props is None:
            from CoolProp.CoolProp import PropsSI
            props=PropsSI
        vals=(return_gas_T_K,return_gas_P_Pa,return_gas_h_J_kg,
              gas_mass_flow_kg_s,requested_gas_heating_W,resistance_heater_efficiency)
        if any(not math.isfinite(v) for v in vals) or min(
                return_gas_T_K,return_gas_P_Pa,resistance_heater_efficiency)<=0 or min(
                gas_mass_flow_kg_s,requested_gas_heating_W)<0 or not 0<resistance_heater_efficiency<=1.:
            raise ValueError("invalid TES heater state")
        qhp=0.
        hot_flow=source_flow=0.
        if charge and requested_gas_heating_W>0 and gas_mass_flow_kg_s>0:
            hot_K=self.hot_water_supply_C+273.15
            gas_limit_K=hot_K-self.min_approach_K
            if return_gas_T_K<gas_limit_K:
                P=self.assumed_liquid_pressure_Pa
                def H(T,fluid,pressure):
                    return float(props("Hmass","T",T,"P",pressure,fluid))
                hhot=H(hot_K,"HEOS::Water",P)
                return_min_K=max(self.hot_water_return_nominal_C+273.15,
                                 return_gas_T_K+self.min_approach_K)
                hhot_min=H(return_min_K,"HEOS::Water",P)
                hsource_in=H(self.source_inlet_C+273.15,"HEOS::Water",P)
                hsource_out=H(self.source_outlet_C+273.15,"HEOS::Water",P)
                hgasmax=H(gas_limit_K,"HEOS::Air",return_gas_P_Pa)
                dh_hot=hhot-hhot_min
                dh_source=hsource_in-hsource_out
                dh_gas=hgasmax-return_gas_h_J_kg
                if min(dh_hot,dh_source,dh_gas)<0:
                    raise ValueError("invalid real-fluid enthalpy ordering")
                source_fraction=1.-1./self.COP_electric_assumed
                # Constant-heat-capacity *secant* approximation for
                # preliminary counterflow NTU, anchored to real-fluid h(T).
                # Design hot-water flow is held at maximum when HP runs.
                # Do not treat this as validated exchanger sizing.
                dT=hot_K-return_gas_T_K
                cg=gas_mass_flow_kg_s*dh_gas/(gas_limit_K-return_gas_T_K)
                cw=self.hot_water_max_flow_kg_s*dh_hot/(hot_K-return_min_K)
                cmin=min(cg,cw);cmax=max(cg,cw)
                if cmin>0:
                    cr=cmin/cmax
                    ntu=self.gas_UA_W_K/cmin
                    if abs(cr-1.)<1e-9:
                        effectiveness=ntu/(1.+ntu)
                    else:
                        z=math.exp(-ntu*(1.-cr))
                        effectiveness=(1.-z)/(1.-cr*z)
                    q_ntu=effectiveness*cmin*dT
                else:q_ntu=0.
                qhp=min(requested_gas_heating_W,self.hp_thermal_nameplate_W,
                    q_ntu,gas_mass_flow_kg_s*dh_gas,
                    self.hot_water_max_flow_kg_s*dh_hot,
                    self.source_water_max_flow_kg_s*dh_source/source_fraction)
                qhp=max(0.,qhp)
                # Pump the designated water flow while producing HP heat,
                # rather than assuming a lower flow but the full-flow UA.
                hot_flow=self.hot_water_max_flow_kg_s if qhp>0 else 0.
                source_flow=qhp*source_fraction/dh_source if dh_source>0 else 0.
        compressor=qhp/self.COP_electric_assumed
        source=qhp-compressor
        booster_heat=requested_gas_heating_W-qhp if charge else 0.
        booster_electric=booster_heat/resistance_heater_efficiency
        pump_flows=hot_flow+source_flow
        pump_electric=pump_flows/self.water_rho_kg_m3*self.assumed_pump_deltaP_Pa/self.pump_efficiency
        return dict(
            heat_pump_to_gas_W=qhp,booster_heat_to_gas_W=booster_heat,
            booster_electric_W=booster_electric,
            heat_pump_compressor_electric_W=compressor,
            assumed_external_source_heat_W=source,
            circulation_pump_electric_W=pump_electric,
            hot_water_flow_kg_s=hot_flow,source_water_flow_kg_s=source_flow,
            gas_to_gas_requested_heating_W=requested_gas_heating_W,
            HP_150C_source80COP_assumption=True,
            COP_not_compressor_map_validated=True,
            water_HX_state_equilibrates_instantaneously=True)

def lossless_heat_balance(rate):
    return (rate["heat_pump_to_gas_W"]-
            rate["heat_pump_compressor_electric_W"]-
            rate["assumed_external_source_heat_W"])
