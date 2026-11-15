"""Inspect original source supplementary PDF for geometry, sensors and pressure units.

This is a SOURCE EXTRACTION only, not a numerical simulation. Source bytes and
page count are pinned; all extracted statements require manual verification of
tables/figures against the PDF before authoritative model parameter adoption.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
from pypdf import PdfReader

EXPECTED_SHA256="ca020dd17e9af13c8a6f4417786a17f3d94366230b5db93576934af67ff527fc"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("results/external_horizontal_bed/Electronic Supplementary Information.pdf"))
    p.add_argument("--outdir",type=Path,default=Path("results/external_horizontal_bed"))
    args=p.parse_args()
    raw=args.input.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=EXPECTED_SHA256:
        raise ValueError("supplementary PDF has unexpected SHA-256; do not use as frozen evidence")
    pdf=PdfReader(str(args.input))
    full=[]
    for i,page in enumerate(pdf.pages):
        s=page.extract_text() or ""
        full.append({"page_number":i+1,"text":s})
    args.outdir.mkdir(parents=True,exist_ok=True)
    (args.outdir/"supplement_pages_extracted.json").write_text(
        json.dumps({"doi":"10.17632/j37x6ptpk2.1",
                    "sha256":digest,"pages":full,
                    "status":"PDF_TEXT_EXTRACTED_NOT_ALL_FIGURES_VERIFIED"},
                   indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("SUPPLEMENT_PAGES",len(full),"SHA",digest)
    for page in full:
        text=page["text"].replace("\r","")
        print(f"SUPPLEMENT_PAGE_{page['page_number']}_BEGIN\n{text[:13000]}\nSUPPLEMENT_PAGE_END")


if __name__=="__main__":
    main()
