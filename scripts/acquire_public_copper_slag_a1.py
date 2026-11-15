"""Acquire public CC-BY experimental axial PBTES data with provenance and guards.

Exact public source:
Battisti et al. (2025), "Copper-slag packed-bed TES - temperature measurements",
DOI 10.17632/fgn79fzg7x.1. Mendeley public file UUID is frozen below.
We download, inspect and hash the ORIGINAL bytes; we do NOT redistribute them
in Git, invent geometry/flow-rate metadata, or claim model validation.

The zip route is a fallback if direct public-file access is unavailable.
Never treat a failed acquisition as an experimental validation PASS.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.error
import urllib.request
import zipfile


DOI = "10.17632/fgn79fzg7x.1"
SOURCE_PAGE = "https://data.mendeley.com/datasets/fgn79fzg7x/1"
DIRECT_URL = (
    "https://data.mendeley.com/public-files/datasets/fgn79fzg7x/"
    "files/4eee3c62-96ad-40fe-a0bf-d313f9e3a2a7/file_downloaded"
)
ZIP_URL = "https://data.mendeley.com/public-api/zip/fgn79fzg7x/download/1"
MAX_DOWNLOAD_BYTES = 4_000_000


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent":"CarnotBatteryLab/0.1 (+public open-science validation)"})
    with urllib.request.urlopen(request,timeout=45) as response:
        raw=response.read(MAX_DOWNLOAD_BYTES+1)
        if len(raw)>MAX_DOWNLOAD_BYTES:
            raise ValueError("unexpectedly large remote source; refusing download")
        return raw


def _as_csv(original: bytes) -> bytes:
    if original[:2]==b"PK":
        with zipfile.ZipFile(io.BytesIO(original)) as zf:
            candidates=[n for n in zf.namelist() if n.lower().endswith(".csv")]
            if len(candidates)!=1:
                raise ValueError(f"archive must contain exactly one CSV: {candidates}")
            info=zf.getinfo(candidates[0])
            if info.file_size>MAX_DOWNLOAD_BYTES:
                raise ValueError("unreasonably large CSV")
            return zf.read(candidates[0])
    if original[:200].lstrip().lower().startswith((b"<!doctype",b"<html",b"<head",b"{\"error\"")):
        raise ValueError("unexpected HTML/API error instead of experimental CSV")
    return original


def acquire(outdir: Path) -> dict:
    errors=[]
    downloaded=None
    route=None
    for url in (DIRECT_URL,ZIP_URL):
        try:
            downloaded=_download(url)
            csv_bytes=_as_csv(downloaded)
            # Reject a server error or insufficient measurement table.
            # Some laboratory CSV exports use Windows-1252 for degree
            # symbols; retain ORIGINAL bytes and log the decoding explicitly.
            try:
                text=csv_bytes.decode("utf-8-sig")
                encoding="utf-8-sig"
            except UnicodeDecodeError:
                text=csv_bytes.decode("cp1252")
                encoding="cp1252"
            if text.count("\x00")>0:
                raise ValueError("binary/UTF16 content must be explicitly converted and recorded")
            sample=text[:4096]
            dialect=csv.Sniffer().sniff(sample,delimiters=",;\t")
            rows=list(csv.reader(io.StringIO(text),dialect))
            rows=[r for r in rows if any(v.strip() for v in r)]
            if len(rows)<10 or max(map(len,rows))<2:
                raise ValueError("CSV does not contain a substantive multicolumn time series")
            route=url
            break
        except (OSError,urllib.error.URLError,ValueError,UnicodeError,
                zipfile.BadZipFile,csv.Error) as exc:
            errors.append({"url":url,"error":f"{type(exc).__name__}: {str(exc)[:250]}"})
    else:
        return {
            "status":"BLOCKED_EXTERNAL_DOWNLOAD",
            "data_origin":"EXPERIMENTAL_PUBLISHED_CC_BY_4_0",
            "doi":DOI,"attempts":errors,
            "missing_for_validation":[
                "raw experimental CSV","experimental geometry/porosity/particle size",
                "calibrated flow, inlet profile and sensor coordinate mapping",
            ],
            "independent_physical_validation":"NOT_RUN",
        }
    assert route is not None
    csv_sha=hashlib.sha256(csv_bytes).hexdigest()
    outdir.mkdir(parents=True,exist_ok=True)
    path=outdir/"copper_slag_axial_A1_radial_R4_original.csv"
    path.write_bytes(csv_bytes)
    header_preview=[r[:16] for r in rows[:7]]
    return {
        "status":"ACQUIRED_UNMAPPED",
        "data_origin":"EXPERIMENTAL_PUBLISHED_CC_BY_4_0",
        "doi":DOI,"source_page":SOURCE_PAGE,
        "direct_source":route,"licence":"CC BY 4.0, attribution required",
        "dataset_authors":"Cardemil Iglesias, Battisti, Calderon-Vasquez et al.",
        "experiment":"Axial A1 charge/discharge at 150C; radial R4 at 300C, separate geometries",
        "source_csv_sha256":csv_sha,
        "preview_decoding":encoding,
        "csv_bytes":len(csv_bytes),
        "row_count":len(rows),
        "row_widths":sorted(set(len(row) for row in rows))[:15],
        "header_preview":header_preview,
        "measured_data_file":str(path.name),
        "independent_physical_validation":"NOT_RUN",
        "missing_for_validation":[
            "source-backed A1 bed diameter, length, porosity and particle sizes",
            "full inlet and mass-flow time series (not inferred from setpoint)",
            "thermocouple labels, axial positions, time zero and errors",
            "whole-run blind validation and numerical convergence",
        ],
        "note":"DOWNLOAD SUCCESS IS NOT AN EXPERIMENTAL MODEL FIT OR VALIDATION",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=Path("results/external_a1"))
    p.add_argument("--require-download",action="store_true")
    args=p.parse_args()
    result=acquire(args.output_dir)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"acquisition_manifest.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("PUBLIC_DATA_ACQUISITION",json.dumps(result,sort_keys=True))
    if args.require_download and result["status"]!="ACQUIRED_UNMAPPED":
        raise SystemExit(3)


if __name__=="__main__":
    main()
