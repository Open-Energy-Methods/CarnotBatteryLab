"""Independent EOS/refrigerant-massflow/electrical-power cross-check of original
UDE experiment-summary MEASUREMENTS, not proprietary compressor-model outputs.

Source: Schmeing et al. doi:10.5281/zenodo.18712882, CSV_mirror/experimental_data.CSV.
The 66-column file explicitly labels measured kg/s, Pa(abs), K and inverter-W.
The computed efficiencies are derived from common measured sensor channels;
they are NOT independently measured efficiencies, nor dense manufacturer maps.
"""
from __future__ import annotations
import csv,io,math,re
from collections import Counter
from statistics import mean
from carnot_battery_lab.physics.r600_offdesign_holdout import (
    REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,
)
from carnot_battery_lab.physics.ude_r600_run_validation import _numeric

COL={
  "fluid":(1,"wf_name"),
  "electrical_frequency_Hz":(3,"f_comp"),
  "massflow_kg_s":(6,"m_dot_wf"),
  "nominal_rotational_frequency_Hz":(7,"n_comp"),
  "compressor_suction_pressure_Pa":(11,"p-R02"),
  "compressor_discharge_pressure_Pa":(12,"p-R03"),
  "compressor_inverter_electric_power_W":(17,"P_comp_el"),
  "compressor_suction_temperature_K":(30,"T-R02"),
  "compressor_discharge_temperature_original_K":(31,"T-R03"),
  "compressor_discharge_temperature_new_sensor_K":(32,"T-R03-new"),
  "source_derived_global_eta":(45,"eta_comp_global"),
  "source_derived_eta_from_new_sensor":(46,"eta_comp_is_T3_new"),
  "source_derived_volumetric_eta":(49,"eta_comp_vol"),
}
ACCEPT_PURE_NBUTANE={"nbutane","butane","r600"}


def _mean_and_range(v:list[float])->dict:
    if not v:return {"N":0,"mean":None,"min":None,"max":None}
    return {"N":len(v),"mean":mean(v),"min":min(v),"max":max(v)}


def _in_same_frequency_train_hull(held:dict,training:list[dict])->bool:
    """No speed interpolation: require exact original electrical frequency.

    This is an INPUT interpolation check, not validation of response accuracy.
    """
    from scipy.optimize import linprog
    group=[x for x in training
           if abs(x["reported_compressor_electric_frequency_Hz"]-
                  held["reported_compressor_electric_frequency_Hz"])<1e-9]
    if len(group)<2:
        return False
    def coord(x):
        return (x["p_suc_Pa"],x["T_suction_K"],
                math.log(x["p_dis_Pa"]/x["p_suc_Pa"]))
    coords=[coord(p) for p in group]
    q=coord(held)
    eq=[[1.]*len(group)]
    target=[1.]
    for dim in range(3):
        components=[p[dim] for p in coords]
        lo,hi=min(components),max(components)
        if abs(hi-lo)<1e-10*max(1.,abs(lo),abs(hi)):
            if abs(q[dim]-lo)>1e-8*max(1.,abs(lo)):
                return False
            continue
        scaled=(q[dim]-lo)/(hi-lo)
        if not -1e-9<=scaled<=1+1e-9:
            return False
        eq.append([(v-lo)/(hi-lo) for v in components])
        target.append(scaled)
    s=linprog([0.]*len(group),A_eq=eq,b_eq=target,
              bounds=(0,None),method="highs")
    return bool(s.success and min(s.x)>=-1e-8)


def _loocv_training_only_predictions(points:list[dict])->dict:
    """Experimental ROW-group withholding, same rig/campaign not new lab.

    No source efficiencies are used to choose a heldout row or fit on that row.
    Reuse pre-declared M1.7 ridge log-pressure-ratio regularization (=0.20).
    """
    from carnot_battery_lab.physics.r600_offdesign_holdout import (
        RIDGE_LOG_PRESSURE_RATIO_PENALTY,
    )
    n=len(points)
    if n<5:
        return {"eligible":False,"N":n,
                "reason":"fewer than 5 distinct measured experiment-summary rows",
                "same_frequency_in_training_hull_N":0}
    errors={"fixed_original_M1_7_constant":[],"train_only_electric_eta_mean":[],
            "train_only_two_parameter_log_pressure_ridge":[]}
    within=[]
    for i,held in enumerate(points):
        train=[x for j,x in enumerate(points) if j!=i]
        outputs=[x["eta_is_overall_electric_recomputed"] for x in train]
        inputs=[math.log(x["p_dis_Pa"]/x["p_suc_Pa"]) for x in train]
        xmean,ymean=mean(inputs),mean(outputs)
        b=sum((x-xmean)*(y-ymean) for x,y in zip(inputs,outputs))/(
            sum((x-xmean)**2 for x in inputs)+RIDGE_LOG_PRESSURE_RATIO_PENALTY)
        pred=ymean+b*(math.log(held["p_dis_Pa"]/held["p_suc_Pa"])-xmean)
        predictions={
            "fixed_original_M1_7_constant":
                REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,
            "train_only_electric_eta_mean":ymean,
            "train_only_two_parameter_log_pressure_ridge":pred,
        }
        # Do not clip an invalid efficiency prediction to create good scores.
        if any(not math.isfinite(x) or not 0<x<=1 for x in predictions.values()):
            return {"eligible":False,"N":n,
                    "reason":"physically inadmissible leave-one-experiment prediction",
                    "same_frequency_in_training_hull_N":0}
        truth=held["eta_is_overall_electric_recomputed"]
        for key,val in predictions.items():
            errors[key].append(val-truth)
        within.append(_in_same_frequency_train_hull(held,train))
    def metrics(e):
        return {"N":len(e),"MAE":mean(abs(x) for x in e),
                "RMSE":math.sqrt(mean(x*x for x in e)),
                "bias":mean(e)}
    inside=[i for i,v in enumerate(within) if v]
    return {
        "eligible":True,"N":n,
        "test_unit":"one original experiment-summary row not correlated logger sample",
        "same_source_experimental_campaign_no_independent_lab":True,
        "source_derived_electric_eta_recomputed_not_a_direct_efficiency_sensor":True,
        "training_only_regularization_predeclared":
            RIDGE_LOG_PRESSURE_RATIO_PENALTY,
        "whole_experiment_LOO_metrics":{k:metrics(e) for k,e in errors.items()},
        "same_frequency_in_training_hull_N":len(inside),
        "outside_same_frequency_training_hull_N":n-len(inside),
        "interior_holdout_errors":(
            {k:metrics([errs[i] for i in inside]) for k,errs in errors.items()}
            if inside else None),
        "multi_speed_interpolation_used":False,
        "minimum_3_in_domain_heldout_experiments_for_strong_claim_met":
            len(inside)>=3,
        "in_domain_predictive_accuracy_established":False,
        "uncertainty_calibrations_reviewed":False,
    }


def audit_processed_experiment_summaries(raw:bytes)->dict:
    """Strict source multiprovenance, no original measured values in response."""
    rows=list(csv.reader(io.StringIO(raw.decode("utf-8-sig",errors="replace")),
                         delimiter=";"))
    if len(rows)<12 or len(rows[0])!=66 or any(len(row)!=66 for row in rows):
        raise ValueError("original processed UDE experiment summary table shape changed")
    header=rows[10]
    for name,(index,expected) in COL.items():
        if header[index].strip()!=expected:
            raise ValueError(f"source measured-field header changed at {name}")
    # Check original preamble also retains an explicit 'measured data' column
    # partition. A calculated eta is NOT an independent physical sensor.
    if not any("Measured" in s for s in rows[6]):
        raise ValueError("source measured-vs-calculated partition missing")
    all_cats=Counter()
    rejected=Counter()
    valid=[]
    for row in rows[11:]:
        fluid=row[1].strip()
        if not fluid:continue
        all_cats[fluid]+=1
        fluid_class=re.sub("[^a-z0-9]","",fluid.casefold())
        if fluid_class not in ACCEPT_PURE_NBUTANE:
            continue
        datum={}
        for name,(idx,_) in COL.items():
            if name=="fluid":continue
            datum[name]=_numeric(row[idx])
        must=("electrical_frequency_Hz","massflow_kg_s",
              "compressor_suction_pressure_Pa","compressor_discharge_pressure_Pa",
              "compressor_inverter_electric_power_W",
              "compressor_suction_temperature_K")
        if any(datum[k] is None for k in must):
            rejected["missing_measured_required_channel"]+=1
            continue
        if (not 0<datum["electrical_frequency_Hz"]<200 or
            not 0<datum["massflow_kg_s"]<100 or
            not 0<datum["compressor_suction_pressure_Pa"]<
                datum["compressor_discharge_pressure_Pa"]<1e8 or
            not 0<datum["compressor_inverter_electric_power_W"]<1e8 or
            not 200<datum["compressor_suction_temperature_K"]<700):
            rejected["nonphysical_or_unexpected_measured_state"]+=1
            continue
        # Source headers give absolute pressure Pa, absolute T Kelvin,
        # refrigerant massflow kg/s, inverter inlet electric W.
        from CoolProp.CoolProp import PropsSI
        try:
            b="HEOS::n-Butane"
            h_in=float(PropsSI("H","P",datum["compressor_suction_pressure_Pa"],
                              "T",datum["compressor_suction_temperature_K"],b))
            s_in=float(PropsSI("S","P",datum["compressor_suction_pressure_Pa"],
                              "T",datum["compressor_suction_temperature_K"],b))
            h_is=float(PropsSI("H","P",datum["compressor_discharge_pressure_Pa"],
                              "S",s_in,b))
        except (ValueError,OverflowError):
            rejected["coolprop_inlet_or_outlet_state_not_evaluable"]+=1
            continue
        ideal_specific=h_is-h_in
        eta=(datum["massflow_kg_s"]*ideal_specific/
             datum["compressor_inverter_electric_power_W"])
        if not math.isfinite(eta) or not 0<eta<=1.1:
            rejected["measured_energy_meter_sanity_failed"]+=1
            continue
        valid.append({
            "eta_is_overall_electric_recomputed":eta,
            "reference_model_eta_error":(
                REFERENCE_OVERALL_ELECTRIC_EFFICIENCY-eta),
            "p_suc_Pa":datum["compressor_suction_pressure_Pa"],
            "p_dis_Pa":datum["compressor_discharge_pressure_Pa"],
            "mass_kg_s":datum["massflow_kg_s"],
            "electrical_W":datum["compressor_inverter_electric_power_W"],
            "T_suction_K":datum["compressor_suction_temperature_K"],
            "reported_compressor_electric_frequency_Hz":
                datum["electrical_frequency_Hz"],
            "reported_source_derived_global_eta":
                datum["source_derived_global_eta"],
            "reported_source_derived_isen_eff_new_sensor":
                datum["source_derived_eta_from_new_sensor"],
            "source_rotational_frequency_derived_not_independent_sensor":
                datum["nominal_rotational_frequency_Hz"],
        })
    errs=[r["reference_model_eta_error"] for r in valid]
    rms=math.sqrt(mean([e*e for e in errs])) if errs else None
    out={
        "source_table_type":"ORIGINAL_UDE_EXPERIMENT_MEASURED_SENSOR_MEANS",
        "original_fluid_category_counts":dict(sorted(all_cats.items())),
        "candidate_original_pure_nbutane_record_count":sum(
            count for label,count in all_cats.items()
            if re.sub("[^a-z0-9]","",label.casefold()) in ACCEPT_PURE_NBUTANE),
        "pure_nbutane_measured_EOS_eligible_points":len(valid),
        "rejected_original_nbutane_rows_by_reason":dict(rejected),
        "EOS_backend":"CoolProp HEOS::n-Butane",
        "ELECTRIC_METER":"source-described compressor frequency inverter input W",
        "sensor_rather_than_derived_fields_used_for_EOS":(
            "m_dot_wf","p-R02","p-R03","T-R02","P_comp_el"),
        "experimental_source_means_leave_ONE_EXPERIMENT_OUT_validation":
            _loocv_training_only_predictions(valid),
        "isentropic_efficiency_recomputed_from_shared_source_measurements":
            _mean_and_range([r["eta_is_overall_electric_recomputed"] for r in valid]),
        "reference_M1_7_0_68894_electrical_eta_absolute_error_mean":
            mean(abs(x) for x in errs) if errs else None,
        "reference_M1_7_0_68894_electrical_eta_RMSE":rms,
        "reference_M1_7_0_68894_electrical_eta_bias":
            mean(errs) if errs else None,
        "source_derived_global_eta_not_independently_measured":
            _mean_and_range([r["reported_source_derived_global_eta"]
                             for r in valid if r["reported_source_derived_global_eta"]
                             is not None]),
        "suction_pressure_Pa":_mean_and_range([r["p_suc_Pa"] for r in valid]),
        "discharge_pressure_Pa":_mean_and_range([r["p_dis_Pa"] for r in valid]),
        "mass_flow_kg_s":_mean_and_range([r["mass_kg_s"] for r in valid]),
        "electrical_inverter_power_W":_mean_and_range([r["electrical_W"] for r in valid]),
        "suction_temperature_K":_mean_and_range([r["T_suction_K"] for r in valid]),
        "electric_frequency_Hz_not_independent_shaft_speed":
            _mean_and_range([r["reported_compressor_electric_frequency_Hz"]
                             for r in valid]),
        "original_measured_rows_redistributed":False,
        "raw_individual_points_exposed":False,
        "publisher_model_code_used":False,
        "physical_measurement_uncertainty_independently_verified":False,
        "independent_campaign_run_count_not_equivalent_to_rows":True,
        "in_envelope_efficiency_surrogate_validation_supported":False,
        "original_1MW_H_REF_hardware_map_qualified":False,
    }
    return out
