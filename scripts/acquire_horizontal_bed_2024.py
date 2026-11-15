"""Acquire Mendeley 2024 horizontal-flow PBTES cases and supplementary methods.

Published source: Calderón-Vásquez et al., DOI 10.17632/j37x6ptpk2.1,
CC BY 4.0, four experimental CSV cases A/B/C/D plus README and methods PDF.

Do not confuse this with the 2025 A1/R4 file which currently exposes only
radial R4. Each case requires external geometry and measured inlet/flow/sensor
mapping before any temperature comparison can be called predictive validation.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import urllib.request
import zipfile
import io
import hashlib
import json
import csv


DATASET_URL="https://data.mendeley.com/public-api/zip/j37x6ptpk2/download/1"
DOI="10.17632/j37x6ptpk2.1"
MAX_BYTES=8_000_000


def acquire(outdir:Path)->dict:
    req=urllib.request.Request(DATASET_URL,headers={
        "User-Agent":"CarnotBatteryLab/0.1 academic experimental validation provenance"})
    with urllib.request.urlopen(req,timeout=50) as response:
        content=response.read(MAX_BYTES+1)
    if len(content)>MAX_BYTES or content[:2]!=b"PK":
        raise ValueError("source expected small ZIP; download missing or unexpected content")
    outdir.mkdir(parents=True,exist_ok=True)
    entries=[]
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.file_size>4_000_000:
                raise ValueError("unexpected file size")
            original=zf.read(info)
            name=Path(info.filename).name
            if not name or name not in (
                "Case_A.csv","Case_B.csv","Case_C.csv","Case_D.csv",
                "README.txt","Electronic Supplementary Information.pdf"):
                raise ValueError(f"unexpected dataset entry: {info.filename}")
            (outdir/name).write_bytes(original)
            rec={"name":name,"size":len(original),
                 "sha256":hashlib.sha256(original).hexdigest()}
            if name.endswith(".csv"):
                try:
                    text=original.decode("utf-8-sig")
                    enc="utf-8"
                except UnicodeDecodeError:
                    text=original.decode("cp1252")
                    enc="cp1252"
                # No silent time/temperature/flow units or sensor-position assumptions.
                rows=list(csv.reader(text.splitlines()))
                rec.update({"encoding":enc,"rows":len(rows),
                            "header_preview":rows[:4]})
            if name=="README.txt":
                try:
                    rec["readme_text"]=original.decode("utf-8-sig")
                except UnicodeDecodeError:
                    rec["readme_text"]=original.decode("cp1252")
            entries.append(rec)
    required={"Case_A.csv","Case_B.csv","Case_C.csv","Case_D.csv",
              "README.txt","Electronic Supplementary Information.pdf"}
    if set(e["name"] for e in entries)!=required:
        raise ValueError("source archive lacks expected cases or supplementary methods")
    return {
        "status":"ORIGINAL_EXPERIMENTAL_FILES_ACQUIRED_VALIDATION_NOT_RUN",
        "dataset_doi":DOI,
        "source_url":DATASET_URL,
        "licence":"CC BY 4.0",
        "zip_sha256":hashlib.sha256(content).hexdigest(),
        "extracted_entries":entries,
        "source_case_labels":["A","B","C","D"],
        "validation_level":"source_acquisition_and_metadata_only",
        "reproduction_gate":"BLOCKED_UNTIL_GEOMETRY_FLOW_SENSOR_MAPPINGS_AND_HOLDOUT_DEFINED",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=Path("results/external_horizontal_bed"))
    args=p.parse_args()
    data=acquire(args.output_dir)
    (args.output_dir/"provenance.json").write_text(
        json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("HORIZONTAL_EXPERIMENTAL_DATA",json.dumps(data,sort_keys=True))


if __name__=="__main__":
    main()
