"""Inspect original UDE experiment-summary **metadata**, not proprietary model code.

The 66-column multirow export contains independent sensor/meter headings and
17 summary runs. This script deliberately emits ONLY header metadata and
file-level numeric-parse counts -- never time series or measured observation
rows -- until the original sensor metadata and working fluid are reconciled.
"""
from __future__ import annotations
import csv,hashlib,io,json,re,sys
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
from inspect_ude_r600_run_metadata import fetch,SOURCE_MD5
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"src"))
from carnot_battery_lab.physics.ude_r600_run_validation import _numeric

FIELDS=("Compressor speed","Low pressure [bar(a)]",
        "High pressure [bar(a)]","Motor power",
        "Compressor frequency","Refrigerant")

def audit_headers_and_channel_parse(raw:bytes)->dict:
    if hashlib.md5(raw).hexdigest()!=SOURCE_MD5:
        raise ValueError("publisher MD5 mismatch")
    out={"published_md5":SOURCE_MD5,"origin_sha256":hashlib.sha256(raw).hexdigest(),
         "original_measured_rows_reproduced_in_report":False}
    with ZipFile(io.BytesIO(raw)) as z:
        processed="data/CSV_mirror/experimental_data.CSV"
        with z.open(processed) as f:
            text=f.read(1_000_000).decode("utf-8-sig",errors="replace")
        rows=list(csv.reader(io.StringIO(text),delimiter=";"))
        if not rows or len(rows[0])!=66:
            raise ValueError("unexpected original UDE summary table shape")
        metadata=[]
        for col in range(66):
            labels=[]
            for line in range(0,min(11,len(rows))):
                s=rows[line][col].strip()
                if s and bool(re.search("[A-Za-z]",s)):
                    labels.append({"row_0based":line,"header":s[:110]})
            metadata.append({"column_0based":col,"headings":labels})
        out["processed_66_column_multiline_header_metadata"]=metadata
        out["processed_column_count"]=len(rows[0])
        out["processed_total_line_count"]=len(rows)
        out["processed_data_rows_after_11_assumed_only_not_accepted"]=max(0,len(rows)-11)
        original_labeled_paths=[
            p for p in z.namelist()
            if p.startswith("data/GitLab Code/measurement_data/Bitzer Data Log/")
            and "n-butane" in p.casefold() and p.lower().endswith(".csv")]
        diagnostics=[]
        for p in sorted(original_labeled_paths):
            with z.open(p) as f: text=f.read().decode("utf-8-sig",errors="replace")
            rdr=csv.DictReader(io.StringIO(text),delimiter=";")
            hdrs=[h.strip() for h in (rdr.fieldnames or [])]
            rdr.fieldnames=hdrs
            count=0
            stats={c:{"nonempty":0,"numeric":0,"positive":0,"nonzero":0} for c in FIELDS[:-1]}
            labels=Counter()
            for row in rdr:
                count+=1
                labels[(row.get("Refrigerant") or "").strip()]+=1
                for field in stats:
                    v=row.get(field)
                    if v and v.strip():stats[field]["nonempty"]+=1
                    number=_numeric(v)
                    if number is not None:
                        stats[field]["numeric"]+=1
                        if number>0:stats[field]["positive"]+=1
                        if number!=0:stats[field]["nonzero"]+=1
            diagnostics.append({"run_file_name":p.rsplit("/",1)[-1],
                                "original_records":count,
                                "numeric_channel_counts":stats,
                                "logged_refrigerant_class_counts":dict(labels)})
        out["original_bitzer_instrument_channel_eligibility_diagnostics"]=diagnostics
    return out

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--download",action="store_true")
    parser.add_argument("--archive",type=Path)
    parser.add_argument("--output",type=Path,default=Path(
        "results/m1_8_ude_processed_table_field_metadata.json"))
    a=parser.parse_args()
    if a.download==(a.archive is not None):
        raise ValueError("choose --download xor --archive")
    raw=fetch() if a.download else a.archive.read_bytes()
    obj=audit_headers_and_channel_parse(raw)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    print("M1_8_PROCESSED_TABLE_META",obj["processed_column_count"],
          obj["processed_total_line_count"])
    for field in obj["processed_66_column_multiline_header_metadata"]:
        labels=[x["header"] for x in field["headings"]]
        print("M1_8_PROCESSED_COLUMN",field["column_0based"]," / ".join(labels))
    for v in obj["original_bitzer_instrument_channel_eligibility_diagnostics"]:
        print("M1_8_BITZER_SENSOR_NUMERIC_ELIGIBILITY",v)
    print("M1_8_PROVEN_NBUTANE_COMPRESSION_EFFICIENCY=False")

if __name__=="__main__":main()
