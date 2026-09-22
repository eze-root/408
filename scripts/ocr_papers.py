#!/usr/bin/env python3
"""Opt-in PaperBeam OCR; raw inputs and receipts stay in ignored resources/."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def convert(endpoint: str, year: int, engine: str) -> None:
    folder = ROOT / "resources/真题/资料2" / f"{year}-{engine}"
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder / "job.json"
    archive = folder / "result.zip"
    if not receipt.exists():
        source = ROOT / "resources/真题/资料2/待识别" / f"{year}-408-待OCR.pdf"
        boundary = uuid.uuid4().hex
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="engine"\r\n\r\n{engine}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{year}-408.pdf"\r\n'
            'Content-Type: application/pdf\r\n\r\n'
        ).encode() + source.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(endpoint + "/api/v1/jobs", data=body,
                                         headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(request, timeout=180) as response:
            job = json.load(response)
        receipt.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    job = json.loads(receipt.read_text())
    print(f"{year}: {job['status']}", flush=True)
    deadline = time.monotonic() + 1200
    while not archive.exists():
        with urllib.request.urlopen(endpoint + "/api/v1/jobs/" + job["job_id"], timeout=60) as response:
            job = json.load(response)
        receipt.write_text(json.dumps(job, ensure_ascii=False, indent=2))
        if job["status"] == "failed":
            raise RuntimeError(f"{year}: {job.get('error')}")
        if job["status"] == "completed":
            with urllib.request.urlopen(endpoint + f"/api/v1/jobs/{job['job_id']}/download", timeout=180) as response:
                archive.write_bytes(response.read())
            break
        if time.monotonic() > deadline:
            raise TimeoutError(f"{year}: OCR exceeded 20 minutes; rerun to resume")
        time.sleep(10)
    with zipfile.ZipFile(archive) as result:
        for entry in result.infolist():
            target = (folder / entry.filename).resolve()
            if not target.is_relative_to(folder.resolve()):
                raise ValueError("Unsafe path in OCR archive")
        result.extractall(folder)
    print(f"{year}: downloaded", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="User-selected PaperBeam base URL")
    parser.add_argument("--engine", choices=["mineru", "paddleocr"], default="paddleocr")
    parser.add_argument("--years", nargs="+", type=int, required=True)
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(convert, args.endpoint.rstrip("/"), year, args.engine) for year in args.years]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
