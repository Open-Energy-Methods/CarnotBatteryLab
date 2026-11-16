"""M1.6 archive discovery for real Carnot-battery HP + TES measurements.

The 36.1 MB public UDE Zenodo archive is not an exact H-REF compressor map.
This performs checksummed manifest inspection only; it never extracts archive
paths, treats model files as measured compressor data, or releases any raw
third-party experiment. Future physics validation must document actual
sensors, units, time alignment and independent holdouts.
"""
from __future__ import annotations

import argparse
from hashlib import md5,sha256
import io
import json
from pathlib import Path
from zipfile import ZipFile,BadZipFile
import urllib.request

DOI="10.5281/zenodo.18712882"
URL="https://zenodo.org/records/18712882/files/data.zip?download=1"
PUBLISHED_MD5="d17bf8b134977f4672c1ec22f085f0ea"
MAX_ARCHIVE_BYTES=45_000_000


def fetch_archive()->bytes:
    req=urllib.request.Request(URL,headers={
        "User-Agent":"CarnotBatteryLab-EvidenceAudit/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r:
        if r.status!=200:
            raise ValueError("UDE archive unavailable by HTTP status")
        data=r.read(MAX_ARCHIVE_BYTES+1)
    if len(data)>MAX_ARCHIVE_BYTES:
        raise ValueError("UDE archive exceeded bounded size")
    return data


def inspect_archive(raw:bytes,expected_md5:str=PUBLISHED_MD5)->dict:
    if md5(raw).hexdigest()!=expected_md5:
        raise ValueError("UDE published archive checksum mismatch")
    try:
        zipfile=ZipFile(io.BytesIO(raw))
    except BadZipFile as exc:
        raise ValueError("UDE archive not a valid ZIP") from exc
    with zipfile:
        members=zipfile.infolist()
        if len(members)>5000:
            raise ValueError("UDE archive suspicious number of members")
        seen=set()
        inventory={}
        relevant=[]
        names=[]
        for item in members:
            name=item.filename.replace("\\","/")
            clean_parts=name.split("/")
            if (name.startswith("/") or ".." in clean_parts or
                "\x00" in name or
                any(not part for part in clean_parts[:-1])):
                raise ValueError("UDE zip entry with unsafe traversal path")
            if name in seen:
                raise ValueError("duplicate UDE ZIP entry")
            seen.add(name)
            names.append(name)
            if item.is_dir():
                continue
            if item.file_size>1_000_000_000:
                raise ValueError("unbounded individual archive file")
            suffix=Path(name).suffix.lower() or "<noext>"
            inventory[suffix]=inventory.get(suffix,0)+1
            if any(term in name.casefold() for term in
                   ("readme","compressor","model","metadata","calibrat",
                    "steady","mean")):
                relevant.append(name)
        return {
            "status":"UDE_OPEN_ARCHIVE_CHECKSUM_AND_MANIFEST_INSPECTED_ONLY",
            "doi":DOI,"source":URL,"source_md5":expected_md5,
            "sha256":sha256(raw).hexdigest(),
            "zip_entries_total":len(members),
            "by_extension":inventory,
            "relevant_metadata_or_model_file_paths":sorted(relevant)[:120],
            "relevant_metadata_or_model_path_count":len(relevant),
            "raw_sensor_time_series_checked_for_units":False,
            "compressor_map_columns_and_uncertainties_accepted":False,
            "complete_H_REF_80_70_110_150_map_qualified":False,
            "licence_review_required_before_raw_redistribution":True,
            "raw_archive_data_redistributed":False,
        }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-archive",type=Path)
    p.add_argument("--download",action="store_true")
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_6_ude_carnot_hp_tes_archive_inventory.json"))
    args=p.parse_args()
    if args.download==(args.input_archive is not None):
        raise ValueError("choose exactly --download or --input-archive")
    raw=fetch_archive() if args.download else args.input_archive.read_bytes()
    obj=inspect_archive(raw)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    print("UDE_ARCHIVE_MD5_VERIFIED",obj["source_md5"],
          "ENTRIES",obj["zip_entries_total"],
          "SUFFIXES",obj["by_extension"],
          "RELEVANT_PATHS",obj["relevant_metadata_or_model_file_paths"][:60])
    print("UDE_H_REF_COMPRESSOR_MAP_QUALIFIED=False")


if __name__=="__main__":
    main()
