"""M2.1 experimental packed-bed DATA DISCOVERY, not model validation.

Independent real packed-bed air/particle measurements:
Weber, Schürg, Roeder, Grobbel, Neises-von Puttkamer & Sattler 2025
https://doi.org/10.17632/3pp86gdvh4.2, CC BY 4.0, N=9 experimental runs.
Control candidate: Cardemil et al. 2025 copper-slag axial/radial:
https://doi.org/10.17632/fgn79fzg7x.1, temperature traces but no asserted
differential pressure instrumentation. NO mass/temperature/dP values are
fabricated, and source data are not mixed across rigs.

This script verifies original Mendeley metadata without presuming its API is
accessible unauthenticated, or claiming file download success.
"""
from __future__ import annotations

import argparse,hashlib,json,urllib.request,urllib.error
from pathlib import Path
from collections import Counter

PUBLIC_DATASETS=(
  {"id":"3pp86gdvh4","version":2,
   "doi":"10.17632/3pp86gdvh4.2",
   "title":"Weber et al. original nine-test shallow air packed-bed temperature/pressure campaign",
   "source_url":"https://data.mendeley.com/datasets/3pp86gdvh4/2",
   "declared_experiment_count_in_publisher_description":9,
   "expected_physics":["air_flow","temperature_history","differential_pressure"],
   "experimental_topology":"shallow 0.5-aspect-ratio packed bed",
   "not_same_as_H_REF_gas_rock_bed":True},
  {"id":"fgn79fzg7x","version":1,
   "doi":"10.17632/fgn79fzg7x.1",
   "title":"Cardemil et al. original copper-slag axial and radial air-bed temperatures",
   "source_url":"https://data.mendeley.com/datasets/fgn79fzg7x/1",
   "declared_experiment_count_in_publisher_description":2,
   "expected_physics":["air_flow","temperature_history"],
   "experimental_topology":"axial/radial copper-slag not original H-REF bed",
   "not_same_as_H_REF_gas_rock_bed":True},
)
MAX_METADATA_BYTES=3_000_000
API="https://api.data.mendeley.com/datasets/{dataset_id}/snapshot?version={version}"

def _metadata_structure(snapshot:object)->dict:
    if not isinstance(snapshot,dict):
        return {"is_object":False,"root_type":type(snapshot).__name__}
    return {
      "is_object":True,
      "root_keys":sorted(snapshot.keys())[:80],
      "files_field_type":type(snapshot.get("files")).__name__,
      "file_count_if_list":(
          len(snapshot["files"]) if isinstance(snapshot.get("files"),list) else None),
      "folders_field_type":type(snapshot.get("folders")).__name__,
      "folder_count_if_list":(
          len(snapshot["folders"]) if isinstance(snapshot.get("folders"),list) else None),
      "entries_metadata_only":_file_entries(snapshot),
    }

def _file_entries(snapshot:dict)->list[dict]:
    records=[]
    for key in ("files","file_list","file_entries","dataset_files"):
        vals=snapshot.get(key)
        if not isinstance(vals,list):continue
        for row in vals[:2000]:
            if not isinstance(row,dict):continue
            records.append({
                "field_collection":key,
                "name":str(row.get("filename") or row.get("name") or "")[:240],
                "file_id":str(row.get("id") or row.get("uuid") or "")[:100],
                "size_bytes":row.get("size",row.get("size_bytes")),
                "type":str(row.get("content_type") or row.get("mime_type") or "")[:80],
                "original_content_SHA256_from_public_API_if_present":(
                    str(row.get("sha256")) if row.get("sha256") else None),
                "source_file_contents_downloaded":False,
            })
    return records

def fetch_dataset_metadata(source:dict)->dict:
    url=API.format(dataset_id=source["id"],version=source["version"])
    request=urllib.request.Request(url,headers={
      "Accept":"application/json",
      "User-Agent":"CarnotBatteryLab-Experimental-PackedBed-DataAudit/1.0"})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            status=response.status
            raw=response.read(MAX_METADATA_BYTES+1)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
        return {**source,"api_url":url,
          "metadata_retrieval_status":"UNAVAILABLE_NO_MEASUREMENT_CLAIM",
          "http_error_category":type(exc).__name__,
          "actual_experiment_data_downloaded":False,
          "measured_temperature_or_pressure_validated":False,
          "raw_source_data_redistributed":False}
    if len(raw)>MAX_METADATA_BYTES:
        raise ValueError("bounded original experimental metadata size exceeded")
    if status!=200:
        return {**source,"api_url":url,
          "metadata_retrieval_status":f"HTTP_{status}_NO_MEASUREMENT_CLAIM",
          "actual_experiment_data_downloaded":False,
          "measured_temperature_or_pressure_validated":False,
          "raw_source_data_redistributed":False}
    try:obj=json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("original metadata returned non-JSON") from exc
    return {**source,"api_url":url,
      "metadata_retrieval_status":"SOURCE_API_JSON_RETRIEVED",
      "source_API_metadata_sha256":hashlib.sha256(raw).hexdigest(),
      "original_json_metadata_byte_count":len(raw),
      "snapshot_shape":_metadata_structure(obj),
      "actual_experiment_data_downloaded":False,
      "measured_temperature_or_pressure_validated":False,
      "raw_source_data_redistributed":False}

def discover_all()->dict:
    rows=[fetch_dataset_metadata(source) for source in PUBLIC_DATASETS]
    return {
      "research_stage":"M2_1_EXTERNAL_SOURCE_MANIFEST_AND_INDEPENDENT_DATA_VALIDATION_DESIGN",
      "dataset_sources":rows,
      "access_outcomes":dict(Counter(x["metadata_retrieval_status"] for x in rows)),
      "source_explicitly_original_packed_bed_air_data":True,
      "cross_rig_parameter_fit_or_score_pooleD":False,
      "manufacturer_compressor_dependency":False,
      "original_H_REF_packed_bed_model_experimentally_qualified":False,
      "entire_Carnot_battery_architecture_matched_service":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path(
        "results/m2_1_external_packed_bed_primary_metadata.json"))
    a=p.parse_args()
    out=discover_all()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    for x in out["dataset_sources"]:
        print("M2_1_PRIMARY_EXPERIMENTAL_SOURCE",x["doi"],
              x["metadata_retrieval_status"])
        shape=x.get("snapshot_shape",{})
        print("M2_1_ORIGINAL_DATASET_API_SCHEMA",x["id"],shape.get("root_keys"),
              "files",shape.get("file_count_if_list"),
              "individual_file_metadata",shape.get("entries_metadata_only",[])[:15])
    print("M2_1_PACKEDBED_MEASURED_HISTORY_VALIDATED=False")
    print("M2_1_COMPRESSOR_MAP_REQUIRED_TO_RUN_THIS_DISCOVERY=False")

if __name__=="__main__":main()
