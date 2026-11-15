"""First R718 -> gas/rock TES thermal coupling (charging only, research F1).

Finite HP condenser transfers a specified duty into a RECIRCULATING gas stream,
whose mean return temperature is solved from the bed's actual transient outlet.
Thus bed state changes condenser temperature, compressor work and HX pinch.
Constant commanded duty and ideal cooled blower mean this is NOT full dynamic
compressor map/control, production plant design or usable process discharge.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import math

from .r718 import R718Inputs, R718Result, InfeasibleCycle, solve_r718
from .finite_hx import InfeasibleHX
from .gas_rock_regenerator import GasRockBed, BedState, BedStep, advance_bed, bed_energy_J
from .auxiliary_hydraulics import ILLUSTRATIVE_CIRCUITS, solve_pipe


class InfeasibleCoupling(RuntimeError):
    """Fixed-point bed/HTF convergence failed; no invented result returned."""


@dataclass(frozen=True)
class ChargeControl:
    heat_into_gas_W: float = 1_000_000.0
    gas_mass_flow_kg_s: float = 25.0
    dt_s: float = 180.0
    number_of_steps: int = 6
    fixed_point_tolerance_K: float = 0.003
    maximum_fixed_point_iterations: int = 15

    def __post_init__(self):
        numbers=(self.heat_into_gas_W,self.gas_mass_flow_kg_s,self.dt_s,
                 self.fixed_point_tolerance_K)
        if not all(math.isfinite(x) and x>0 for x in numbers):
            raise ValueError("positive finite charge rate, flow, time and tolerance required")
        if not isinstance(self.number_of_steps,int) or self.number_of_steps<1:
            raise ValueError("number_of_steps must be >=1")
        if not isinstance(self.maximum_fixed_point_iterations,int) or self.maximum_fixed_point_iterations<2:
            raise ValueError("fixed point iteration limit must be >=2")


@dataclass(frozen=True)
class ChargeStep:
    elapsed_s: float
    mean_return_C: float
    hot_gas_in_C: float
    final_bed_exit_C: float
    condenser_saturation_C: float
    compressor_stage_ratios: tuple[float,...]
    compressor_electric_W: float
    source_pump_electric_W: float
    intercool_pump_electric_W: float
    blower_electric_W: float
    total_grid_electric_W: float
    heat_hp_to_gas_J: float
    heat_transferred_to_bed_J: float
    heat_loss_to_ambient_J: float
    stored_energy_change_J: float
    system_energy_residual_J: float
    bed_pressure_drop_Pa: float
    compressor_cop_including_partial_aux: float
    coupling_iterations: int
    bed_fluid_axial_K: tuple[float,...]
    bed_solid_axial_K: tuple[float,...]


@dataclass(frozen=True)
class ChargeRun:
    steps: tuple[ChargeStep,...]
    final_bed: BedState
    initial_bed: BedState
    completed: bool
    termination_reason: str | None
    cumulative_hp_heat_J: float
    cumulative_heat_into_bed_J: float
    cumulative_wall_loss_J: float
    cumulative_stored_energy_J: float
    cumulative_electric_grid_J: float
    energy_ledger_residual_J: float
    scientific_status: str = "charge_only_coupled_screening_unvalidated_compressor"


def _solve_one_charge_step(
    bed:GasRockBed, state:BedState, hp_inputs:R718Inputs,
    control:ChargeControl, elapsed_s:float
) -> tuple[ChargeStep,BedState]:
    gas_mcp=control.gas_mass_flow_kg_s*bed.gas_cp_J_kgK
    rise_K=control.heat_into_gas_W/gas_mcp
    return_guess_K=float(state.fluid_temperature_K[-1])
    trial=None
    for iteration in range(1,control.maximum_fixed_point_iterations+1):
        supply_K=return_guess_K+rise_K
        trial=advance_bed(bed,state,inlet_K=supply_K,
                          mass_flow_kg_s=control.gas_mass_flow_kg_s,
                          dt_s=control.dt_s)
        mismatch=trial.mean_outlet_temperature_K-return_guess_K
        if abs(mismatch)<=control.fixed_point_tolerance_K:
            break
        return_guess_K+=0.65*mismatch
    else:
        raise InfeasibleCoupling("bed/HTF return temperature fixed point failed")
    assert trial is not None
    mean_return_K=trial.mean_outlet_temperature_K
    supply_K=return_guess_K+rise_K
    # R718 variable names process* refer here to HOT GAS CHARGE LOOP, not to
    # delivered qualified industrial process heat. This is charge-only.
    case=replace(hp_inputs,
        useful_process_heat_W=control.heat_into_gas_W,
        process_return_C=mean_return_K-273.15,
        process_supply_C=supply_K-273.15,
        process_cp_J_kgK=bed.gas_cp_J_kgK,
        available_process_flow_kg_s=None)
    result=solve_r718(case)
    if abs(result.process_mass_flow_kg_s-control.gas_mass_flow_kg_s)>0.01:
        raise InfeasibleCoupling("gas mass flow does not match condenser power")
    source=solve_pipe(ILLUSTRATIVE_CIRCUITS[0],
                      result.source_mass_flow_kg_s,backend=case.backend)
    intercool=solve_pipe(ILLUSTRATIVE_CIRCUITS[2],
                         result.intercooler_sink_flow_kg_s,backend=case.backend)
    compressor_grid=result.W_compressor_shaft_W/(case.motor_efficiency*0.98*0.95)
    total_grid=compressor_grid+source.pump_electric_W+intercool.pump_electric_W+trial.blower_electric_W
    hp_heat_J=result.Q_process_W*control.dt_s
    # q_hot_gas differs from the prescribed HX heat by at most the fixed-point
    # temperature residual; report (never hide) that operator-splitting error.
    residual=trial.stored_energy_change_J+trial.heat_loss_to_ambient_J-hp_heat_J
    step=ChargeStep(elapsed_s,
        mean_return_K-273.15,supply_K-273.15,
        trial.final_outlet_temperature_K-273.15,
        case.process_supply_C+case.condenser_pinch_K,
        result.stage_pressure_ratios,
        compressor_grid,source.pump_electric_W,intercool.pump_electric_W,
        trial.blower_electric_W,total_grid,hp_heat_J,
        trial.heat_from_hot_gas_J,trial.heat_loss_to_ambient_J,
        trial.stored_energy_change_J,residual,trial.pressure_drop_Pa,
        result.Q_process_W/total_grid,iteration,
        trial.final_state.fluid_temperature_K,trial.final_state.solid_temperature_K)
    return step,trial.final_state


def simulate_charge(bed:GasRockBed, state:BedState, hp_inputs:R718Inputs,
                    control:ChargeControl=ChargeControl()) -> ChargeRun:
    current=state
    initial_energy=bed_energy_J(bed,state)
    steps=[]
    termination=None
    for n in range(control.number_of_steps):
        try:
            step,current=_solve_one_charge_step(bed,current,hp_inputs,control,
                                                (n+1)*control.dt_s)
        except (InfeasibleCycle,InfeasibleHX,InfeasibleCoupling,RuntimeError,ValueError) as exc:
            termination=f"{type(exc).__name__}: {exc}"
            break
        steps.append(step)
    hp_heat=sum(s.heat_hp_to_gas_J for s in steps)
    into_bed=sum(s.heat_transferred_to_bed_J for s in steps)
    wall=sum(s.heat_loss_to_ambient_J for s in steps)
    dU=bed_energy_J(bed,current)-initial_energy
    electric=sum(s.total_grid_electric_W*control.dt_s for s in steps)
    return ChargeRun(tuple(steps),current,state,termination is None,termination,
                     hp_heat,into_bed,wall,dU,electric,dU+wall-hp_heat)
