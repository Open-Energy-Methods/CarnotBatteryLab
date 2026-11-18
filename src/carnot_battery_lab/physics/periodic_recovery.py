"""M3.12 preregistered approximate periodicity gate (model-only)."""
import math

# Numerical research tolerances, not instrument accuracy or plant specification.
STATE_LIMITS={
    "max_rock_cycle_end_change_K":.05,
    "max_wall_cycle_end_change_K":.05,
    "max_water_temperature_cycle_end_change_K":.05,
    "max_gas_temperature_cycle_end_change_K":.05,
    "max_gas_pressure_cycle_end_change_Pa":50.,
    "max_gas_relative_cell_mass_cycle_end_change":.0002,
}
ENERGY_REL=.005
ENERGY_ABS_J=10.
DURATION_ABS_S=.5

def periodic_audit(records):
    """Require two successive all-state and output repeatability passes.

    Always report observed evidence; a failed/missing gate is never
    auto-promoted by an iteration budget or stable total energy alone.
    """
    previous=None
    rows=[]
    def metrics(row):
        c,d=row["charge"],row["discharge"]
        return {"heater":c["heater_electric_J"],
                "charge_blower":c["blower_electric_J"],
                "discharge_blower":d["blower_electric_J"],
                "cooler":d["cooler_heat_to_assumed_sink_J"],
                "gross":d["water_boundary_heat_J"],
                "qualified":d["qualified_water_heat_J"],
                "band":d["water_target_band_heat_J"]}
    for row in records:
        ratios={k:abs(float(row[k]))/v for k,v in STATE_LIMITS.items()}
        if any(not math.isfinite(x) for x in ratios.values()):
            raise ValueError("nonfinite periodic diagnostic")
        m=metrics(row)
        if not all(math.isfinite(x) for x in m.values()):
            raise ValueError("nonfinite output")
        d=row["discharge"]
        durations={k:d[k] for k in ("qualified_water_duration_s","water_target_band_duration_s")}
        if not all(math.isfinite(x) for x in durations.values()):
            raise ValueError("nonfinite duration")
        changes=None if previous is None else {
            k:abs(m[k]-previous[0][k])/max(ENERGY_ABS_J,ENERGY_REL*max(abs(m[k]),abs(previous[0][k])))
            for k in m}
        dt=None if previous is None else {k:abs(v-previous[1][k])/DURATION_ABS_S for k,v in durations.items()}
        passed=changes is not None and max(*ratios.values(),*changes.values(),*dt.values())<=1.
        rows.append({"cycle":row["cycle"],"state_ratios":ratios,"output_energy_ratios":changes,
                     "output_duration_ratios":dt,"pass":passed})
        previous=(m,durations)
    return {"state_limits":STATE_LIMITS,"energy_relative_tolerance":ENERGY_REL,
            "energy_absolute_floor_J":ENERGY_ABS_J,"duration_absolute_s":DURATION_ABS_S,
            "required_consecutive_passes":2,"rows":rows,
            "approximate_periodic_model_gate_pass":len(rows)>=3 and all(r["pass"] for r in rows[-2:])}
