"""M1.8 preliminary schema-only UDE n-butane experimental run discovery.

Directly inspected source bytes have pinned Zenodo MD5; model source code is
never opened, imported or executed. The report contains ONLY schema metadata,
file sizes, run identifiers and accepted sensor column names -- no raw values.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,re,urllib.request,zipfile
from pathlib import Path

URL="https://zenodo.org/records/18712882/files/data.zip?download=1"
SOURCE_MD5="d17bf8b134977f4672c1ec22f085f0ea"
LOG_ROOT="data/GitLab Code/measurement_data/Bitzer Data Log/"
SELECTED_COLUMNS=(
    "Time","Compressor speed","Low pressure [bar(a)]",
    "High pressure [bar(a)]","Motor power","Motor current",
    "Compressor frequency","Motor torque","Compressor model","Refrigerant",
)
MAX_BYTES=45_000_000

def fetch()->bytes:
    with urllib.request.urlopen(urllib.request.Request(
        URL,headers={"User-Agent":"CarnotBatteryLab-M1.8/1.0"}),timeout=90) as r:
        if r.status!=200:
            raise ValueError("failed to retrieve UDE original archive")
        raw=r.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError("oversized original archive")
    return raw

def schema_inventory(raw:bytes,expected_md5:str=SOURCE_MD5)->dict:
    if hashlib.md5(raw).hexdigest()!=expected_md5:
        raise ValueError("published UDE archive MD5 mismatch")
    logs=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for meta in z.infolist():
            path=meta.filename.replace(chr(92),"/")
            if ".." in path.split("/") or path.startswith("/"):
                raise ValueError("unsafe archive path")
            if (not path.startswith(LOG_ROOT) or
                "n-butane" not in path.casefold() or
                not path.lower().endswith(".csv")):
                continue
            # Only already-published measured data, never compressor-model dir.
            if meta.file_size>25_000_000:
                raise ValueError("one experimental log unexpectedly oversized")
            with z.open(meta) as f:
                data=f.read()
            text=data.decode("utf-8-sig",errors="replace")
            first=next((v for v in text.splitlines() if v.strip()),"")
            delimiter=max((chr(9),";",","),key=lambda s:first.count(s))
            reader=csv.reader(io.StringIO(text),delimiter=delimiter)
            header=next(reader)
            names=[v.strip() for v in header]
            counts={"total_records":0,"width_matches":0,"blank_records":0}
            for record in reader:
                if not any(s.strip() for s in record):
                    counts["blank_records"]+=1
                    continue
                counts["total_records"]+=1
                if len(record)==len(names):
                    counts["width_matches"]+=1
            logs.append({
                "run_filename":path.rsplit("/",1)[-1],
                "run_path":path,
                "uncompressed_bytes":meta.file_size,
                "delimiter":{"\\t":"TAB",";":"SEMICOLON",",":"COMMA"}.get(
                    delimiter,"TAB"),
                "field_count":len(names),
                "available_fields":{c:c in names for c in SELECTED_COLUMNS},
                "headers_selected":[c for c in SELECTED_COLUMNS if c in names],
                "record_counts":counts,
                "all_headers":names,
            })
        # CSV_MIRROR could contain a processed steady-state experiment table;
        # determine its preamble/schema layout without copying measured data.
        mirror={}
        for path in ("data/CSV_mirror/experimental_data.CSV",
                     "data/CSV_mirror/metadata_sensors.CSV"):
            if path not in z.namelist(): continue
            with z.open(path) as f:text=f.read(80_000).decode(
                "utf-8-sig",errors="replace")
            lines=text.splitlines()
            patterns=[]
            for i,line in enumerate(lines[:32]):
                # Schema shape: never emit original values/metadata text.
                delimiter=max((chr(9),";",","),key=lambda s:line.count(s))
                ncols=len(next(csv.reader([line],delimiter=delimiter)))
                alpha_tokens=sum(bool(re.search("[A-Za-z]",s)) for s in
                    next(csv.reader([line],delimiter=delimiter)))
                patterns.append({"line_0based":i,
                                 "field_count":ncols,
                                 "alphabetic_fields":alpha_tokens,
                                 "delimiter":("TAB" if delimiter==chr(9) else
                                              "SEMICOLON" if delimiter==";" else
                                              "COMMA")})
            mirror[path]={"bytes_examined":len(text.encode("utf8")),
                          "total_lines_in_prefix":len(lines),
                          "first_32_line_schemas":patterns}
    if not logs: raise ValueError("no n-butane measured Bitzer sensor logs")
    return {"state":"SOURCE_VERIFIED_N_BUTANE_SCHEMA_ONLY",
            "origin_DOI":"10.5281/zenodo.18712882",
            "publisher_md5":SOURCE_MD5,
            "download_sha256":hashlib.sha256(raw).hexdigest(),
            "independent_run_log_count":len(logs),
            "bitzer_measured_n_butane_runs":sorted(logs,key=lambda x:x["run_filename"]),
            "processed_mirror_table_structure":mirror,
            "original_sensor_values_or_model_source_redistributed":False,
            "calibration_and_meter_boundary_accepted":False,
            "OST_M1_7_five_holdouts_changed":False,
            "in_envelope_model_validation_supported":False,
            "H_REF_hardware_qualified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--download",action="store_true")
    p.add_argument("--archive",type=Path)
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_8_ude_nbutane_schema_only.json"))
    a=p.parse_args()
    if a.download==(a.archive is not None):
        raise ValueError("choose exactly --download or --archive")
    raw=fetch() if a.download else a.archive.read_bytes()
    out=schema_inventory(raw)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("M1_8_UDE_ARCHIVE_MD5_PASS",out["publisher_md5"])
    for log in out["bitzer_measured_n_butane_runs"]:
        print("M1_8_EXPERIMENTAL_NBUTANE_SCHEMA",
              log["run_filename"],log["record_counts"],
              log["field_count"],log["delimiter"],log["available_fields"])
    for key,v in out["processed_mirror_table_structure"].items():
        print("M1_8_MIRROR_SCHEMA",key,v["first_32_line_schemas"])
    print("M1_8_PROVEN_PHYSICAL_VALIDATION=False")

if __name__=="__main__":main()
