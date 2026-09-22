#!/usr/bin/env python3
"""Build clean, image-only PDFs for a second OCR pass.

The MinerU diagnostic PDFs in 资料1 draw colored layout annotations over a
full-page scan. This script keeps the original compressed page image and drops
the diagnostic drawing layer without resampling or recompressing the image.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "resources/真题/资料1"
OUTPUT_ROOT = ROOT / "resources/真题/资料2/待识别"


def content_streams(page) -> list:
    contents = page.get("/Contents")
    return list(contents) if isinstance(contents, list) else [contents]


def clean_pdf(sources: dict[str, Path], destination: Path) -> tuple[int, list[int]]:
    readers = {kind: PdfReader(str(path)) for kind, path in sources.items()}
    reader = readers["layout"]
    page_counts = {len(item.pages) for item in readers.values()}
    if len(page_counts) != 1:
        raise ValueError(f"diagnostic PDFs have different page counts: {sources}")
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    retained_counts: list[int] = []

    page_sets = zip(*(item.pages for item in readers.values()), writer.pages, strict=True)
    for *source_pages, page in page_sets:
        stream_sets = [content_streams(source_page) for source_page in source_pages]
        retained = 0
        for candidates in zip(*stream_sets):
            digests = {
                hashlib.sha256(item.get_object().get_data()).digest()
                for item in candidates
            }
            if len(digests) != 1:
                break
            retained += 1
        if retained == 0:
            raise ValueError("no common original content stream found")
        cloned_streams = content_streams(page)
        page[NameObject("/Contents")] = ArrayObject(cloned_streams[:retained])
        page.pop(NameObject("/Annots"), None)
        retained_counts.append(retained)

    writer.add_metadata(
        {
            "/Title": destination.stem,
            "/Subject": "第二轮 OCR 输入；保留原始扫描图，已移除 MinerU 标注层",
        }
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        writer.write(output)

    check = PdfReader(str(destination))
    if len(check.pages) != len(reader.pages):
        raise ValueError(f"page count changed: {destination}")
    return len(reader.pages), retained_counts


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    count = 0
    for year_dir in sorted(SOURCE_ROOT.glob("20*")):
        match = re.match(r"(20\d{2})", year_dir.name)
        if not match or not year_dir.is_dir():
            continue
        sources = {
            kind: next(year_dir.glob(f"*_{kind}.pdf"), None)
            for kind in ("layout", "model", "spans")
        }
        if any(path is None for path in sources.values()):
            raise ValueError(f"missing diagnostic PDF in {year_dir}")
        year = match.group(1)
        destination = OUTPUT_ROOT / f"{year}-408-待OCR.pdf"
        pages, retained = clean_pdf(sources, destination)
        print(
            f"{year}: {pages} pages, retained {min(retained)}-{max(retained)} "
            "common source streams per page"
        )
        count += 1
    print(f"Prepared {count} clean OCR input PDFs in {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
