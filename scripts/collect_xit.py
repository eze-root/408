#!/usr/bin/env python3
"""Download the 408 exam attachments linked by Xiamen Institute of Technology."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'https://www.xit.edu.cn/yjsfk/kyzykwtkw/list.htm'
AGENT = '408-course-archive/1.0'


def attachments(page: bytes) -> list[dict]:
    found = {}
    for anchor in BeautifulSoup(page, 'html.parser').select('a[href]'):
        url = urljoin(PAGE, anchor['href'])
        if not urlsplit(url).path.lower().endswith('.pdf'):
            continue
        if urlsplit(url).scheme != 'https' or urlsplit(url).netloc != 'www.xit.edu.cn':
            raise ValueError(f'Attachment is outside the requested site: {url}')
        title = anchor.get_text(' ', strip=True)
        year = re.search(r'(20\d{2})年', title)
        if not year or '408' not in title:
            continue
        kind = 'answers' if re.search('答案|解析', title) else 'paper'
        key = (int(year[1]), kind)
        item = {'year': key[0], 'kind': kind, 'title': title, 'url': url}
        if key in found and found[key]['url'] != url:
            raise ValueError(f'Multiple files for {key}: inspect before replacing')
        found[key] = item
    if not found:
        raise ValueError('No 408 PDF attachments found')
    return [found[key] for key in sorted(found)]


def fetch(url: str) -> bytes:
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': AGENT}), timeout=45) as response:
                if urlsplit(response.geturl()).netloc != 'www.xit.edu.cn':
                    raise ValueError('Unexpected off-site redirect')
                return response.read(150 * 1024 * 1024)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError('Download did not complete')


def inspect_pdf(data: bytes) -> tuple[int, str]:
    if not data.startswith(b'%PDF-'):
        raise ValueError('Attachment is not a PDF')
    with pymupdf.open(stream=data, filetype='pdf') as doc:
        if doc.is_encrypted or not len(doc):
            raise ValueError('PDF is encrypted or empty')
        return len(doc), '\n\f\n'.join(page.get_text() for page in doc)


def save_manifest(folder, manifest):
    temporary = folder / 'manifest.json.tmp'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(folder / 'manifest.json')


def catalog(folder: Path, records: list[dict]):
    rows = []
    for year in sorted({r['year'] for r in records}, reverse=True):
        cells = []
        for kind, label in [('paper', '试题'), ('answers', '答案与解析')]:
            item = next((r for r in records if r['year'] == year and r['kind'] == kind), None)
            if item and item.get('status') == 'downloaded':
                cells.append(f'<td><a href="{html.escape(item["file"])}">{label} PDF · {item["pages"]} 页</a></td>')
            else:
                cells.append('<td>未收录</td>')
        rows.append(f'<tr><th>{year}</th>{"".join(cells)}</tr>')
    (folder / 'catalog.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>408 历年真题原文件</title>
<style>body{max-width:900px;margin:60px auto;padding:0 24px;font:18px/1.8 system-ui;color:#203047;background:#f7f8fa}h1{font-size:32px}table{width:100%;border-collapse:collapse;background:white}th,td{padding:15px 20px;border-bottom:1px solid #dde3e9;text-align:left}a{color:#155bb5}small{color:#5b6674}</style>
<h1>408 历年真题与答案</h1><p>厦门工学院公开资料 · 按年份整理的原始 PDF</p>
<p><a href="''' + PAGE + '''">查看来源页面</a> · <a href="manifest.json">文件清单与来源记录</a></p>
<table><thead><tr><th>年份</th><th>试题</th><th>答案与解析</th></tr></thead><tbody>''' + ''.join(rows) + '</tbody></table></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'resources/xit')
    parser.add_argument('--offline', action='store_true', help='Verify cached files and rebuild the catalog without network access')
    args = parser.parse_args()
    folder = args.output
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / 'manifest.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    cached = {(r['year'], r['kind']): r for r in old.get('files', [])}
    robots = None
    robots_status = old.get('robots', {})
    if not args.offline:
        try:
            data = fetch('https://www.xit.edu.cn/robots.txt')
            (folder / 'robots.txt').write_bytes(data)
            robots = RobotFileParser()
            robots.parse(data.decode('utf-8', errors='replace').splitlines())
            robots_status = {'status': 'read'}
            if not robots.can_fetch(AGENT, PAGE):
                raise ValueError('robots.txt excludes the requested page')
        except (HTTPError, URLError, TimeoutError) as error:
            robots_status = {'status': 'unavailable', 'detail': str(error)}
        page = fetch(PAGE)
        (folder / 'source-index.html').write_bytes(page)
    else:
        page = (folder / 'source-index.html').read_bytes()
    records = attachments(page)
    manifest = {'source_page': PAGE, 'retrieved_at': old.get('retrieved_at') if args.offline else datetime.now(timezone.utc).isoformat(),
                'robots': robots_status, 'source_html_sha256': hashlib.sha256(page).hexdigest(), 'files': records}
    failures = []
    for index, item in enumerate(records):
        path = folder / str(item['year']) / f'{item["year"]}-408-{item["kind"]}-original.pdf'
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            previous = cached.get((item['year'], item['kind']), {})
            if path.exists() and previous.get('url') == item['url']:
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != previous['sha256']:
                    raise ValueError('Cached PDF checksum mismatch')
            else:
                if args.offline:
                    raise ValueError('File is missing from the verified cache')
                if path.exists():
                    raise ValueError('Existing file has no matching source record')
                if robots and not robots.can_fetch(AGENT, item['url']):
                    raise ValueError('robots.txt excludes this attachment')
                time.sleep(.6)
                data = fetch(item['url'])
            pages, text = inspect_pdf(data)
            if not path.exists():
                temporary = path.with_suffix('.part')
                temporary.write_bytes(data)
                temporary.replace(path)
            path.with_suffix('.txt').write_text(text)
            item.update(status='downloaded', file=path.relative_to(folder).as_posix(),
                        bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), pages=pages,
                        extracted_text_chars=len(text.strip()))
            print(f'{index+1}/{len(records)} {item["year"]} {item["kind"]}: {pages} pages', flush=True)
        except Exception as error:
            item.update(status='failed', error=str(error));failures.append(item)
            print(f'FAILED {item["title"]}: {error}', flush=True)
        save_manifest(folder, manifest)
    catalog(folder, records)
    manifest['summary'] = {'files': len(records), 'downloaded': len(records)-len(failures),
                           'years': sorted({r['year'] for r in records}),
                           'pages': sum(r.get('pages', 0) for r in records),
                           'bytes': sum(r.get('bytes', 0) for r in records)}
    save_manifest(folder, manifest)
    print(json.dumps(manifest['summary'], ensure_ascii=False), flush=True)
    if failures:
        raise SystemExit(f'{len(failures)} attachment(s) failed; inspect manifest.json')


if __name__ == '__main__':
    main()
