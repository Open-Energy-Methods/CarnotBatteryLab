"""M1.6: acquire and audit *genuine* publicly released compressor observations.

This program never promotes published compressor measurements to a complete
M1.5 measured *hardware map* when mandatory measured mass flow, shaft power,
discharge temperature, uncertainty, verified rated limits and speed lines are
absent. Manufacturer EN12900 polynomial outputs are synthetic, not physical
test observations. No external source rows are redistributed by this script.

Published open CSV: Widmaier et al., Zenodo 10.5281/zenodo.17599603.
Original CSV md5: 680dd400cfb39b2fa0a1dd22a09c731f (publisher record).
"""
from __future__ import annotations

import argparse
import csv
from hashlib import md5,sha256
import io
import json
import math
from pathlib import Path
import urllib.request

SOURCE_URL="https://zenodo.org/records/17599603/files/compressor_performance_data.csv?download=1"
SOURCE_DOI="10.5281/zenodo.17599603"
SOURCE_MD5="680dd400cfb39b2fa0a1dd22a09c731f"
REQUIRED_COLUMNS={
    "source","compressor","refrigerant","f_elec_Hz",
    "T_ev_C","T_suc_C","p_suc_bar","p_dis_bar","eta_is","eta_vol",
}
# These are only joint NOMINAL PROXIMITY indicators, not interpolation
# acceptance criteria or manufacturer machine-nameplate limits.
PROXIMITY={"pressure_relative":.05,"temperature_abs_K":5.}
MISSING_M15={
    "measured_refrigerant_mass_flow_kg_s",
    "measured_suction_volumetric_flow_m3_s",
    "measured_compressor_shaft_W",
    "measured_discharge_temperature_C",
    "machine_rated_speed_rpm_and_oil_limits",
    "traceable_per_point_measurement_standard_uncertainty",
    "reserved_independent_heldout_campaign",
    "machine_train_identity_at_1MW_and_actual_IHX_topology",
}


def fetch_source(*,url:str=SOURCE_URL,max_bytes:int=7_000_000)->bytes:
    """Bound size; caller verifies original published checksum before parsing."""
    if url!=SOURCE_URL:
        raise ValueError("external data URL is pinned for this evidence release")
    request=urllib.request.Request(
        url,headers={"User-Agent":"CarnotBatteryLab-EvidenceAudit/1.0"})
    with urllib.request.urlopen(request,timeout=45) as response:
        if response.status!=200:
            raise ValueError("public dataset HTTP status not 200")
        data=response.read(max_bytes+1)
    if len(data)>max_bytes:
        raise ValueError("source dataset larger than expected download cap")
    return data


def _bounded_float(row:dict,key:str,lower:float|None=None)->float:
    value=float(row[key])
    if not math.isfinite(value) or (lower is not None and value<=lower):
        raise ValueError(f"invalid experimental measurement in {key}")
    return value


def parse_and_audit_bytes(raw:bytes,requirements:dict, *,
                          expected_md5:str=SOURCE_MD5)->dict:
    actual_md5=md5(raw).hexdigest()
    if actual_md5!=expected_md5:
        raise ValueError(f"published dataset MD5 mismatch: {actual_md5}")
    text=raw.decode("utf-8-sig",errors="strict")
    rdr=csv.DictReader(io.StringIO(text))
    if not rdr.fieldnames or not REQUIRED_COLUMNS.issubset(rdr.fieldnames):
        raise ValueError("published dataset columns changed or are missing")
    all_count=0
    origin_counts={}
    measured_nbutane=[]
    malformed=0
    for row in rdr:
        all_count+=1
        label=row["source"].strip()
        origin=("MEASURED_EXPERIMENTAL_OST" if
                label.startswith("Experimental OST") else
                "MEASURED_EXPERIMENTAL_MILANO" if
                label.startswith("Experimental Milano") else
                "SYNTHETIC_MANUFACTURER_POLYNOMIAL" if
                label.startswith(("Bitzer EN12900","Bock EN12900")) else
                "UNRECOGNIZED_SOURCE_CLASS")
        origin_counts[origin]=origin_counts.get(origin,0)+1
        if (origin=="MEASURED_EXPERIMENTAL_OST" and
            row["refrigerant"].strip().casefold()=="butane"):
            try:
                p0=_bounded_float(row,"p_suc_bar",0)
                p1=_bounded_float(row,"p_dis_bar",0)
                ts=_bounded_float(row,"T_suc_C")
                eta_is=_bounded_float(row,"eta_is",0)
                eta_vol=_bounded_float(row,"eta_vol",0)
                freq=_bounded_float(row,"f_elec_Hz",0)
                if p1<=p0 or eta_is>1 or eta_vol>1:
                    raise ValueError("not an admissible compressor operating point")
            except (KeyError,ValueError,TypeError):
                malformed+=1
                continue
            measured_nbutane.append({
                "source":label,"compressor":row["compressor"].strip(),
                "suction_bar":p0,"discharge_bar":p1,
                "suction_C":ts,"stage_ratio":p1/p0,
                "reported_eta_is_overall_electric":eta_is,
                "eta_vol":eta_vol,"drive_frequency_Hz":freq,
            })
    if all_count==0:
        raise ValueError("published data file is empty")
    if origin_counts.get("UNRECOGNIZED_SOURCE_CLASS",0):
        raise ValueError("unrecognized source categories; source type contamination risk")
    r600=requirements["r600_80C_source_110_150C_transcritical_screen"][
        "map_requirements_for_numerically_feasible_points"]
    comparisons=[]
    for pressure,case in sorted(r600.items(),key=lambda kv:int(kv[0])):
        d=case["compressor_stage_demands"][0]
        def match(x):
            return (
                abs(x["suction_bar"]*1e5-d["suction_pressure_Pa"])/
                    d["suction_pressure_Pa"]<=PROXIMITY["pressure_relative"]
                and abs(x["discharge_bar"]*1e5-d["discharge_pressure_Pa"])/
                    d["discharge_pressure_Pa"]<=PROXIMITY["pressure_relative"]
                and abs(x["suction_C"]-d["suction_temperature_C"])<=
                    PROXIMITY["temperature_abs_K"])
        matched=[x for x in measured_nbutane if match(x)]
        comparisons.append({
            "target_high_pressure_Pa":d["discharge_pressure_Pa"],
            "target_suction_pressure_Pa":d["suction_pressure_Pa"],
            "target_suction_temperature_C":d["suction_temperature_C"],
            "target_stage_pressure_ratio":d["stage_pressure_ratio"],
            "target_actual_suction_volumetric_flow_m3_s":
                d["suction_volumetric_flow_m3_s"],
            "raw_experimental_points_meeting_5pct_both_pressures_and_5K_suction":
                len(matched),
            "map_interpolation_support_established":False,
            "can_certify_compressor":False,
        })
    def bound(key:str)->dict:
        if not measured_nbutane:
            return {"min":None,"max":None}
        values=[x[key] for x in measured_nbutane]
        return {"min":min(values),"max":max(values)}
    groups=sorted(set(x["compressor"] for x in measured_nbutane))
    return {
        "status":"OPEN_MEASURED_COMPRESSOR_POINTS_AUDITED_NOT_M15_MAP",
        "source_doi":SOURCE_DOI,
        "source_url":SOURCE_URL,
        "source_reported_md5":SOURCE_MD5,
        "download_sha256":sha256(raw).hexdigest(),
        "source_csv_rows":all_count,
        "raw_origin_counts":origin_counts,
        "source_classification":"CSV ROW BY ROW synthetic vs physically measured",
        "real_measured_nbutane_points":len(measured_nbutane),
        "malformed_real_nbutane_points":malformed,
        "real_nbutane_machine_ids":groups,
        "real_nbutane_range":{
            "suction_pressure_bar":bound("suction_bar"),
            "discharge_pressure_bar":bound("discharge_bar"),
            "suction_temperature_C":bound("suction_C"),
            "stage_pressure_ratio":bound("stage_ratio"),
            "overall_electric_isentropic_efficiency":bound(
                "reported_eta_is_overall_electric"),
            "volumetric_efficiency":bound("eta_vol"),
            "electrical_frequency_Hz_NOT_SHAFT_RPM":bound(
                "drive_frequency_Hz"),
        },
        "strict_nominal_point_comparison":comparisons,
        "unreported_m15_fields":sorted(MISSING_M15),
        "manufacturer_map_at_H_REF_available":False,
        "safe_use":"Independent experimental screening of overall electrical "
             "isentropic/volumetric compressor efficiencies at OTHER operating "
             "conditions, NOT a shaft-efficiency map for 80-to-70C/1MW H-REF.",
        "no_raw_data_copied_into_report":True,
        "rights":"Source states CC BY 4.0; attribution required",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--requirements",required=True,type=Path)
    p.add_argument("--input-csv",type=Path,default=None)
    p.add_argument("--download",action="store_true")
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_6_open_r600_experimental_evidence_audit.json"))
    p.add_argument("--checksum",default=SOURCE_MD5)
    args=p.parse_args()
    if args.download==(args.input_csv is not None):
        raise ValueError("choose exactly one of --download or --input-csv")
    req=json.loads(args.requirements.read_text(encoding="utf-8"))
    if req.get("evidence_status")!=(
        "M1_4_SCIENTIFIC_REQUIREMENTS_AND_LITERATURE_CROSSWALK_ONLY"):
        raise ValueError("M1.4 compressor demand file is required")
    raw=fetch_source() if args.download else args.input_csv.read_bytes()
    report=parse_and_audit_bytes(raw,req,expected_md5=args.checksum)
    report["m1_4_inputs_sha256"]=sha256(args.requirements.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("M1_6_PUBLIC_DATA_CHECKSUM_MATCHED",report["source_reported_md5"])
    print("M1_6_CSV_ROWS",report["source_csv_rows"],
          "MEASURED_NBUTANE",report["real_measured_nbutane_points"],
          "ORIGINS",report["raw_origin_counts"])
    print("M1_6_NBUTANE_RANGES",report["real_nbutane_range"])
    for item in report["strict_nominal_point_comparison"]:
        print("M1_6_R600_NOMINAL_NEIGHBOR_COUNT",
              int(item["target_high_pressure_Pa"]),
              item["raw_experimental_points_meeting_5pct_both_pressures_and_5K_suction"])
    print("M1_5_MACHINE_QUALIFIED=False; METADATA_INSPECTION_NOT_FULL_MAP")


if __name__=="__main__":
    main()
