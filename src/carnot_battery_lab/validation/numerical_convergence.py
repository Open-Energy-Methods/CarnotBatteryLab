"""Assess observed grid-refinement evidence without claiming external validation.

The first-order upwind finite-volume discretisation has expected O(dz)
space accuracy. Report empirical orders from pairs of *independent*
double-refinement differences, not from first-law closure or fitted curves.
The selection thresholds are prospective engineering decision levels
chosen after the INITIAL 2026-11-15 study, NOT preregistered validation
thresholds or measurement uncertainty specifications.
"""
from __future__ import annotations
import math


class ResolutionEvidenceError(ValueError):
    pass


PAIR_KEYS=[
    "grid_08_to_grid_16","grid_16_to_grid_32",
    "grid_32_to_grid_64","grid_64_to_grid_128",
]


def evaluate_resolution(
    study:dict, *,
    next_numerical_target_rms_K:float=1.0,
    next_numerical_target_crossing_shift_s:float=15.0,
)->dict:
    if not all(math.isfinite(x) and x>0 for x in (
            next_numerical_target_rms_K,next_numerical_target_crossing_shift_s)):
        raise ValueError("future numerical targets must be positive finite")
    if study.get("status")!="CASE_B_ONLY_RESOLUTION_AND_UNCERTAINTY_SCREEN_NO_VALIDATION":
        raise ResolutionEvidenceError("unqualified source, not Case B grid study")
    pairs=study.get("grid_pairwise_refinement_differences",{})
    if not all(k in pairs for k in PAIR_KEYS):
        raise ResolutionEvidenceError("require complete four matched doubling intervals")
    rms=[]
    breaks=[]
    for key in PAIR_KEYS:
        row=pairs[key]
        x=row["temperature_grid_RMS_difference_K"]
        t=row["model_80C_breakthrough_shift_s"]
        if not math.isfinite(x) or x<=0 or t is None or not math.isfinite(t):
            raise ResolutionEvidenceError("nonfinite/zero resolution evidence or missing crossings")
        rms.append(x)
        breaks.append(t)
    orders=[math.log(rms[i]/rms[i+1],2) for i in range(len(rms)-1)]
    crossing_orders=[math.log(abs(breaks[i])/abs(breaks[i+1]),2)
                     for i in range(len(breaks)-1)]
    monotonic=all(a>b for a,b in zip(rms,rms[1:]))
    crossed=all(abs(a)>abs(b) for a,b in zip(breaks,breaks[1:]))
    meets=rms[-1]<=next_numerical_target_rms_K and abs(breaks[-1])<=next_numerical_target_crossing_shift_s
    return {
        "scientific_status":"NUMERICAL_REFINEMENT_DIAGNOSTIC_NOT_EXTERNAL_VALIDATION",
        "dataset_doi":study.get("experiment"),
        "case":"B ONLY",
        "all_C_D_forward_predictions_still_withheld":True,
        "rms_change_K":rms,
        "crossing_shift_s":breaks,
        "observed_order_from_outlet_RMS_doublings":orders,
        "observed_order_from_breakthrough_doublings":crossing_orders,
        "RMS_convergence_monotonic":monotonic,
        "breakthrough_convergence_monotonic":crossed,
        "finest_grid_increment_RMS_K":rms[-1],
        "finest_grid_breakthrough_increment_s":breaks[-1],
        "proposed_NEXT_pass_targets_not_preregistered":[
            f"RMS outlet pairwise grid difference <= {next_numerical_target_rms_K} K",
            f"absolute crossing shift <= {next_numerical_target_crossing_shift_s} s",
        ],
        "numerical_resolution_pass":bool(meets),
        "external_predictive_validation_pass":False,
        "warning":(
            "Numerical refinement closeness is not a model-vs-experiment accuracy claim. "
            "Thresholds are prospective engineering decision values, not measurement uncertainty. "
            "Coarser-grid numerical diffusion can disguise physical-model deficiencies."
        ),
    }
