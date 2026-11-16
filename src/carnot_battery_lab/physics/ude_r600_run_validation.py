"""M1.8: independent UDE n-butane compressor instrumentation validation GATE.

Source: Schmeing, Welp & Atakan, 2026, Zenodo:18712882.
Three explicitly labeled experimental runs (026/027/028) are the independent
experimental unit; 6,839 nested time samples are NOT independent experiments.
No proprietary archived compressor model is opened, copied, fitted or used.
No reference to original 5 reserved OST M1.7 measured holdouts is modified.

Bitzer logger motor power and compressor speed channels lack confirmed units
and measurement-boundary calibration in this independent analysis. We do not
treat them as kW/shaft rpm or infer mass flow/isentroptic efficiency from them.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from hashlib import md5,sha256
import io,math
from statistics import median
from zipfile import ZipFile
import re

UDE_MD5="d17bf8b134977f4672c1ec22f085f0ea"
DOI="10.5281/zenodo.18712882"
ROOT="data/GitLab Code/measurement_data/Bitzer Data Log/"
EXPECTED_RUN_IDS=("026","027","028")
MIN_INDEPENDENT_RUNS_FOR_IN_ENVELOPE=5  # stated preregistration heuristic, not a standard
MEASURED_CHANNELS=("Low pressure [bar(a)]","High pressure [bar(a)]",
                   "Compressor speed","Motor power","Compressor frequency")
MANDATORY_CHANNELS=MEASURED_CHANNELS+("Refrigerant",)
ORIGINAL_SOURCE_MODEL_REUSE_ALLOWED=False


def _numeric(x:str)->float|None:
    """Parse unambiguous locale numeric without silently treating text as zero."""
    if x is None:return None
    v=x.strip().replace(chr(160),"").replace(" ","").replace(",",".")
    if not v:return None
    if not re.fullmatch(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?",v):
        return None
    try: value=float(v)
    except ValueError:return None
    return value if math.isfinite(value) else None


def _distribution(v:list[float])->dict:
    if not v:return {"N":0,"min":None,"median":None,"max":None}
    return {"N":len(v),"min":min(v),"median":median(v),"max":max(v)}


@dataclass(frozen=True)
class RunSummary:
    run_id:str
    filename:str
    csv_record_count:int
    physically_running_pressure_valid_rows:int
    positive_motor_channel_rows:int
    motor_power_channel_parseable_rows:int
    fluid_label_stated_in_filename:bool
    refrigerant_text_unique:list[str]
    samples_with_all_required_channels:int
    measured_pressure_suction_bar_a:dict
    measured_pressure_discharge_bar_a:dict
    measured_pressure_ratio:dict
    compressor_speed_logger_units_UNCONFIRMED:dict
    motor_power_logger_units_UNCONFIRMED:dict
    compressor_frequency_logger_units_UNCONFIRMED:dict
    per_sample_sensor_standard_uncertainty_available:bool=False
    shaft_power_measured_in_confirmed_SI_units:bool=False
    refrigerant_mass_flow_kg_s_measured_in_this_log:bool=False
    actual_suction_temperature_C_measured_in_this_log:bool=False


def read_original_bitzer_run(source:bytes,*,filename:str,run_id:str)->RunSummary:
    if run_id not in EXPECTED_RUN_IDS or not re.search(
        rf"Experiment\s*0?{run_id}_n-Butane_",filename,re.IGNORECASE):
        raise ValueError("attempt to pass a different refrigerant or experimental run")
    csvtext=source.decode("utf-8-sig",errors="replace")
    reader=csv.DictReader(io.StringIO(csvtext),delimiter=";")
    fields=reader.fieldnames
    if fields is None or len(fields)!=len(set(fields)) or not set(
        MANDATORY_CHANNELS).issubset(fields):
        raise ValueError("required original Bitzer sensor channels unavailable")
    if not any("Time"==col for col in fields):
        raise ValueError("no original logger time channel")
    observations=0;pressure_good=0;motor_good=0;motor_parse=0;complete=0
    fluid_names=set();values={x:[] for x in MEASURED_CHANNELS}
    ratios=[]
    for row in reader:
        observations+=1
        if None in row or any(v is None for v in row.values()):
            raise ValueError("source CSV row column count changed")
        fluid=(row["Refrigerant"] or "").strip()
        if fluid:fluid_names.add(fluid)
        datum={k:_numeric(row[k]) for k in MEASURED_CHANNELS}
        if datum["Motor power"] is not None:
            motor_parse+=1
        if not all(x is not None for x in datum.values()):
            continue
        complete+=1
        ps,pd=datum["Low pressure [bar(a)]"],datum["High pressure [bar(a)]"]
        n=datum["Compressor speed"]
        f=datum["Compressor frequency"]
        w=datum["Motor power"]
        if ps<=0 or pd<=ps or n<=0 or f<=0:
            continue
        pressure_good+=1
        if w<=0:continue
        motor_good+=1
        for k in MEASURED_CHANNELS: values[k].append(datum[k])
        ratios.append(pd/ps)
    if not observations or pressure_good>observations:
        raise ValueError("not a valid original experimental Bitzer sensor log")
    return RunSummary(
        run_id=run_id,filename=filename,
        csv_record_count=observations,
        physically_running_pressure_valid_rows=pressure_good,
        positive_motor_channel_rows=motor_good,
        motor_power_channel_parseable_rows=motor_parse,
        fluid_label_stated_in_filename=True,
        refrigerant_text_unique=sorted(fluid_names)[:12],
        samples_with_all_required_channels=complete,
        measured_pressure_suction_bar_a=_distribution(values[
            "Low pressure [bar(a)]"]),
        measured_pressure_discharge_bar_a=_distribution(values[
            "High pressure [bar(a)]"]),
        measured_pressure_ratio=_distribution(ratios),
        compressor_speed_logger_units_UNCONFIRMED=_distribution(
            values["Compressor speed"]),
        motor_power_logger_units_UNCONFIRMED=_distribution(
            values["Motor power"]),
        compressor_frequency_logger_units_UNCONFIRMED=_distribution(
            values["Compressor frequency"]),
    )


def _inside_segment_in_3d(q:tuple[float,...],a:tuple[float,...],
                          b:tuple[float,...])->bool:
    # Two independent experimental run centroids span, at most, a LINE in
    # 3D. Exact barycentric support, no assumption of rectangular envelope.
    if len(q)!=3 or len(a)!=3 or len(b)!=3:
        raise ValueError("expected three-dimensional source-state coordinates")
    scales=[max(abs(v),abs(w),abs(k),1.) for v,w,k in zip(q,a,b)]
    q0=[v/s for v,s in zip(q,scales)]
    a0=[v/s for v,s in zip(a,scales)]
    b0=[v/s for v,s in zip(b,scales)]
    delta=[x-y for x,y in zip(b0,a0)]
    distance=sum(x*x for x in delta)
    if distance<=1e-22:
        return math.sqrt(sum((x-y)**2 for x,y in zip(q0,a0)))<=1e-8
    w=sum((x-y)*d for x,y,d in zip(q0,a0,delta))/distance
    if not 0<=w<=1:return False
    residual=math.sqrt(sum((x-(y+w*d))**2
                           for x,y,d in zip(q0,a0,delta)))
    return residual<=1e-8


def _features(run:RunSummary)->tuple[float,float,float]|None:
    fields=(run.measured_pressure_suction_bar_a,
            run.measured_pressure_discharge_bar_a,
            run.compressor_speed_logger_units_UNCONFIRMED)
    if not all(v["N"]>=1 and v["median"] is not None for v in fields):
        return None
    return tuple(v["median"] for v in fields)


def audit_original_ude_archive(raw:bytes,expected_md5:str=UDE_MD5)->dict:
    if md5(raw).hexdigest()!=expected_md5:
        raise ValueError("UDE original published source MD5 mismatch")
    findings=[]
    with ZipFile(io.BytesIO(raw)) as z:
        paths=z.namelist()
        if len(paths)>5000:raise ValueError("unexpected large ZIP file count")
        for path in paths:
            if path.startswith("/") or ".." in path.replace(chr(92),"/").split("/"):
                raise ValueError("unsafe ZIP source path")
        for run_id in EXPECTED_RUN_IDS:
            matched=[path for path in paths if path.startswith(ROOT) and
                     path.lower().endswith(".csv") and
                     re.search(rf"Experiment\s*0?{run_id}_n-Butane_",
                               path,re.IGNORECASE)]
            if len(matched)!=1:
                raise ValueError("ambiguous or missing original n-butane run "+run_id)
            path=matched[0]
            if z.getinfo(path).file_size>30_000_000:
                raise ValueError("oversize original Bitzer sensor file")
            with z.open(path) as s:
                reading=s.read()
            findings.append(read_original_bitzer_run(
                reading,filename=path.rsplit("/",1)[-1],run_id=run_id))
    runs=[r.__dict__ for r in findings]
    grouped=[]
    for chosen in findings:
        train=[r for r in findings if r.run_id!=chosen.run_id]
        candidate=_features(chosen)
        other=[_features(r) for r in train]
        full=all(v is not None for v in [candidate,*other])
        support=(_inside_segment_in_3d(candidate,*other) if full else False)
        grouped.append({
            "reserved_entire_run":chosen.run_id,
            "training_run_ids":[r.run_id for r in train],
            "3D_holdout_centroid_in_training_two_run_line_segment":support,
            "point_level_efficiency_prediction_or_fit_conducted":False,
            "independent_holdout_accuracy_claim":False,
            "reason":"Only two distinct training runs and uncertain power/speed "
                     "sensor units; no comparable measured massflow or suction T.",
        })
    total=sum(r.csv_record_count for r in findings)
    return {
        "scientific_status":"VERIFIED_NBUTANE_THREE_RUN_SENSOR_AUDIT_NO_IN_ENVELOPE_VALIDATION",
        "doi":DOI,"published_archive_md5":expected_md5,
        "download_sha256":sha256(raw).hexdigest(),
        "independent_original_R600_run_count":len(findings),
        "raw_correlated_time_sample_count_not_independent":total,
        "experimental_run_ids":list(EXPECTED_RUN_IDS),
        "run_sensor_aggregate_only":runs,
        "leave_one_ENTIRE_run_out_support_checks":grouped,
        "independent_runs_required_for_preregistered_envelope_gate":
            MIN_INDEPENDENT_RUNS_FOR_IN_ENVELOPE,
        "minimum_independent_run_count_gate_passed":
            len(findings)>=MIN_INDEPENDENT_RUNS_FOR_IN_ENVELOPE,
        "all_reserved_runs_have_3D_support":
            all(q["3D_holdout_centroid_in_training_two_run_line_segment"] for q in grouped),
        "original_OST_M1_7_holdouts_must_remain_unchanged":True,
        "claim_of_real_3D_in_envelope_predictive_accuracy":False,
        "measured_electrical_power_units_and_meter_boundary_verified":False,
        "measured_shaft_speed_units_verified":False,
        "sensor_calibration_uncertainty_verified":False,
        "actual_refrigerant_massflow_and_compressor_inlet_temperature_available_in_bitzer_file":False,
        "manufacturer_compressor_map_qualified":False,
        "industrial_80_70_source_110_150_process_1MW_qualified":False,
        "individual_measurement_timeseries_redistributed":False,
        "source_model_code_used_or_republished":False,
    }
