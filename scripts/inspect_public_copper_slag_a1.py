"""Inspect externally acquired Mendeley A1/R4 CSV without inventing sensor positions.

The file contains multiple experiments separated by rows beginning "Run:".
The export is Windows-1252; metadata/column rows are not time samples.
The only allowed measured data source is its pinned CC-BY original file.
"""
from __future__ import annotations
import csv
from hashlib import sha256
import json
from pathlib import Path
import argparse

EXPECTED_SHA256 = "b557561cecb9b87092c0ea6f14bda178d7b9aae301a939267702bd943c46cce8"
DOI = "10.17632/fgn79fzg7x.1"


def inspect_sections(path:Path, *, require_hash:bool=True) -> dict:
    original=path.read_bytes()
    digest=sha256(original).hexdigest()
    if require_hash and digest!=EXPECTED_SHA256:
        raise ValueError(f"source dataset version/hash mismatch: {digest}")
    text=original.decode("cp1252")
    rows=list(csv.reader(text.splitlines(),delimiter=","))
    sections=[]
    markers=[i for i,row in enumerate(rows) if row and row[0].strip()=="Run:"]
    if not markers:
        raise ValueError("expected Mendeley A1/R4 run labels absent")
    for idx,begin in enumerate(markers):
        end=markers[idx+1] if idx+1<len(markers) else len(rows)
        meta=rows[begin]
        run=meta[1].strip() if len(meta)>1 else "UNKNOWN"
        topology=meta[3].strip() if len(meta)>3 else "UNKNOWN"
        headers=None
        start=None
        for i in range(begin+1,min(begin+12,end)):
            if rows[i] and rows[i][0].strip().lower()=="time [h]":
                headers=rows[i]
                start=i+1
                break
        if headers is None or start is None:
            raise ValueError(f"{run}: measured-header row missing")
        samples=[]
        for row in rows[start:end]:
            if not row or not row[0].strip():
                continue
            try:
                t=float(row[0])
            except ValueError:
                continue
            samples.append((t,row))
        if len(samples)<10:
            raise ValueError(f"{run}: insufficient original observations")
        times=[t for t,_ in samples]
        if any(a>=b for a,b in zip(times,times[1:])):
            raise ValueError(f"{run}: measured timestamps not monotonically increasing")
        sections.append({
            "run":run,"topology":topology,"metadata_fields":meta,
            "header":headers,"file_header_row_index":start-1,
            "time_unit":"hours","temperature_unit":"degrees Celsius",
            "start_time_h":times[0],"end_time_h":times[-1],
            "number_of_rows":len(samples),
            "source_sha256":digest,
            "first_data_row":samples[0][1][:10],
            "last_data_row":samples[-1][1][:10],
            "status":"MEASUREMENTS_PARSED_NOT_PREDICTION_VALIDATED",
        })
    return {
        "doi":DOI,"sha256":digest,"total_source_csv_rows":len(rows),
        "sections":sections,
        "experimental_validation":"NOT_RUN",
        "notice":"Sensor axial coordinates, bed geometry, inlet histories and mass-flow data must not be inferred from numerical model fit",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("results/external_a1/copper_slag_axial_A1_radial_R4_original.csv"))
    p.add_argument("--output",type=Path,default=Path("results/external_a1/sections_manifest.json"))
    args=p.parse_args()
    data=inspect_sections(args.input)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("MEASURED_SECTION_SCHEMA",json.dumps(data,sort_keys=True))


if __name__=="__main__":
    main()
