"""Collect public 408 papers into a local, review-only dataset.

Run explicitly; never imported by the site build or CI. No account or API access.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup, Comment


BASE = "https://zhenti.beokayy.club/"
USER_AGENT = "408-study-collector/1.0"
ROOT = Path(__file__).resolve().parents[1]
QUESTION_ID = re.compile(r"(\d{4})-(\d{2})")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_file(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    temporary.replace(path)


def write_json(path: Path, value) -> None:
    write_file(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def public_url(value: str, base: str = BASE) -> str:
    url = urljoin(base, value)
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != urlsplit(BASE).netloc
            or parts.username or parts.password):
        raise ValueError(f"拒绝站外或非 HTTPS 资源：{url}")
    return parts._replace(fragment="").geturl()


class AccessBlocked(RuntimeError):
    """Stop the run on access restrictions rather than trying other routes."""


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        if re.search(r"/(?:login|signin|auth)(?:/|$)", urlsplit(newurl).path):
            raise AccessBlocked("页面要求登录，停止采集")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Fetcher:
    def __init__(self, output: Path, delay=1.0, offline=False, refresh=False):
        self.output = output
        self.delay = max(1.0, delay)
        self.offline = offline
        self.refresh = refresh
        self.last_request = 0.0
        self.seen = set()
        self.records = {}
        self.robots = None
        self.opener = build_opener(SameOriginRedirect())

    def get(self, url: str, *, robots=False) -> tuple[bytes, dict]:
        url = public_url(url)
        if not robots and self.robots and not self.robots.can_fetch(USER_AGENT, url):
            raise AccessBlocked(f"robots.txt 不允许访问：{url}")
        key = hashlib.sha256(url.encode()).hexdigest()
        raw = self.output / "raw" / f"{key}.bin"
        sidecar = raw.with_suffix(".json")
        # Always recheck robots on a live run; all other resources resume from cache.
        cached = self.offline or (not robots and (not self.refresh or url in self.seen))
        if cached and raw.exists() and sidecar.exists():
            data = raw.read_bytes()
            meta = json.loads(sidecar.read_text())
            if meta["url"] != url or hashlib.sha256(data).hexdigest() != meta["sha256"]:
                raise ValueError(f"缓存校验失败：{raw}；用 --refresh 重新采集")
            self.records[url] = meta
            return data, meta
        if self.offline:
            raise FileNotFoundError(f"离线缓存缺失：{url}")
        for attempt in range(3):
            time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
                with self.opener.open(request, timeout=30) as response:
                    public_url(response.url)
                    data = response.read(25 * 1024 * 1024 + 1)
                    if len(data) > 25 * 1024 * 1024:
                        raise ValueError(f"资源超过 25 MiB：{url}")
                    status = response.status
                    content_type = response.headers.get("Content-Type", "")
                break
            except HTTPError as exc:
                if robots and exc.code == 404:
                    data, status, content_type = b"", 404, "text/plain"
                    break
                if exc.code in (401, 403):
                    raise AccessBlocked(f"HTTP {exc.code}，停止采集：{url}") from exc
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                retry_after = exc.headers.get("Retry-After", "")
                try:
                    wait = float(retry_after)
                except ValueError:
                    try:
                        wait = parsedate_to_datetime(retry_after).timestamp() - time.time()
                    except (ValueError, TypeError):
                        wait = 2 ** (attempt + 1)
                if wait > 60:
                    raise AccessBlocked(f"服务器要求等待 {wait:.0f} 秒，请稍后重跑") from exc
                time.sleep(max(0, wait))
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))
        meta = {"url": url, "fetched_at": timestamp(), "status": status,
                "content_type": content_type, "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "raw_path": raw.relative_to(self.output).as_posix()}
        write_file(raw, data)
        write_json(sidecar, meta)
        self.seen.add(url)
        self.records[url] = meta
        return data, meta

    def check_robots(self):
        data, meta = self.get(urljoin(BASE, "robots.txt"), robots=True)
        self.robots = RobotFileParser(urljoin(BASE, "robots.txt"))
        self.robots.parse(data.decode("utf-8").splitlines())
        self.delay = max(self.delay, self.robots.crawl_delay(USER_AGENT) or 0)
        rate = self.robots.request_rate(USER_AGENT)
        if rate and rate.requests:
            self.delay = max(self.delay, rate.seconds / rate.requests)
        return meta


def soup_of(data: str | bytes) -> BeautifulSoup:
    return BeautifulSoup(data.decode("utf-8") if isinstance(data, bytes) else data, "html.parser")


def discover_papers(data: str | bytes) -> dict[int, dict]:
    papers = {}
    for card in soup_of(data).select("a.archive-year-card[href]"):
        url = public_url(card["href"])
        match = re.fullmatch(r"/paper/(\d{4})", urlsplit(url).path)
        if not match:
            continue
        values = {item.dt.get_text(strip=True): int(re.search(r"\d+", item.dd.get_text()).group())
                  for item in card.select("dl > div")}
        year = int(match[1])
        papers[year] = {"year": year, "url": url, "expected_questions": values["题目"],
                        "expected_score": values["总分"], "advertised_answers": values["答案"]}
    if not papers:
        raise ValueError("首页未找到年份卡片，页面结构可能已变化")
    return papers


def block(node, page_url: str) -> dict:
    if node is None:
        return {"html": "", "text": "", "image_urls": []}
    fragment = soup_of(node.decode_contents())
    for item in fragment.select("script,style,iframe,object,embed,form"):
        item.decompose()
    for comment in fragment.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    images = []
    for tag in fragment.find_all(True):
        for attr in list(tag.attrs):
            if attr not in {"class", "src", "alt", "href", "colspan", "rowspan"}:
                del tag[attr]
        if tag.name == "img":
            src = public_url(tag.get("src", ""), page_url)
            tag["src"] = src
            images.append(src)
        if tag.name == "a":
            href = urljoin(page_url, tag.get("href", ""))
            if urlsplit(href).scheme in {"https", "http"}:
                tag["href"] = href
            else:
                tag.attrs.pop("href", None)
    canonical = str(fragment)
    # Plain text is for search; HTML remains authoritative for formulae/tables/code.
    for fraction in fragment.select(".markdown-math-fraction"):
        top = fraction.select_one(".markdown-math-numerator")
        bottom = fraction.select_one(".markdown-math-denominator")
        if top and bottom:
            fraction.replace_with(f"({top.get_text()})/({bottom.get_text()})")
    for tag in fragment.find_all(["p", "div", "pre", "tr", "li", "br"]):
        tag.insert_after("\n")
    for tag in fragment.find_all(["td", "th"]):
        tag.insert_after("\t")
    for image in fragment.find_all("img"):
        image.replace_with(f"[图片: {image.get('alt', '')}]")
    text = re.sub(r"\n{3,}", "\n\n", fragment.get_text()).strip()
    return {"html": canonical, "text": text, "image_urls": sorted(set(images))}


def parse_paper(data: str | bytes, paper: dict, meta: dict) -> list[dict]:
    questions = []
    for card in soup_of(data).select("article.question-card"):
        qid = card.get("id", "")
        match = QUESTION_ID.fullmatch(qid)
        if not match or int(match[1]) != paper["year"]:
            raise ValueError(f"题号或年份异常：{qid}")
        header = card.select_one(".question-meta")
        parts = header.find_all("span", recursive=False) if header else []
        subject = card.select_one(".question-kicker")
        body = card.select_one(".question-body")
        if len(parts) < 2 or subject is None or body is None:
            raise ValueError(f"{qid} 缺少必需字段，页面结构可能已变化")
        options = []
        for option in card.select(".choice-option"):
            label = option.select_one(".choice-letter").get_text(strip=True)
            options.append({"label": label, **block(option.select_one(".choice-text"), paper["url"])})
        answer = block(card.select_one(".answer-content"), paper["url"])
        choice = re.match(r"^答案\s*[：:]\s*([ABCD])(?:\s|$|[。；;])", answer["text"])
        source_subject = subject.get_text(strip=True)
        normalized_subject = {"组成原理": "计算机组成原理"}.get(source_subject, source_subject)
        questions.append({
            "id": qid, "year": paper["year"], "number": int(match[2]),
            "subject": normalized_subject, "type": parts[0].get_text(strip=True),
            "score": int(re.search(r"\d+", parts[1].get_text()).group()),
            "stem": block(body, paper["url"]), "options": options, "answer": answer,
            "answer_choice": choice[1] if choice else None,
            "video_urls": sorted({urljoin(paper["url"], a["href"])
                                  for a in card.select(".video-link-row a[href]")}),
            "knowledge_point_ids": [], "review_status": "unverified",
            "source": {"url": paper["url"] + "#" + qid, "page_url": paper["url"],
                       "fetched_at": meta["fetched_at"], "page_sha256": meta["sha256"],
                       "subject": source_subject},
        })
    numbers = [q["number"] for q in questions]
    if sorted(numbers) != list(range(1, paper["expected_questions"] + 1)):
        raise ValueError(f"{paper['year']} 题号缺失、重复或数量不符：{numbers}")
    if sum(q["score"] for q in questions) != paper["expected_score"]:
        raise ValueError(f"{paper['year']} 分值合计与首页不符")
    for q in questions:
        if not q["stem"]["html"].strip():
            raise ValueError(f"{q['id']} 题干为空")
        if q["type"] == "选择题" and [o["label"] for o in q["options"]] != list("ABCD"):
            raise ValueError(f"{q['id']} 选项不完整或重复")
    return sorted(questions, key=lambda q: q["number"])


def parse_knowledge(data: str | bytes, url: str) -> list[dict]:
    soup = soup_of(data)
    subject = soup.select_one("h2")
    points = []
    for entry in soup.select(".knowledge-point-entry"):
        label = entry.select_one(".knowledge-point-label")
        chapter = entry.find_parent("article", class_="knowledge-chapter-card")
        if label is None or chapter is None or subject is None:
            raise ValueError("知识点索引结构变化")
        ids = set()
        for link in entry.select(".knowledge-question-links a[href]"):
            match = re.fullmatch(r"/question/(\d{4}-\d{2})", urlsplit(link["href"]).path)
            if match:
                ids.add(match[1])
        points.append({"id": entry["id"].removeprefix("point-"),
                       "name": label.get_text(strip=True), "subject": subject.get_text(strip=True),
                       "chapter": chapter.h3.get_text(strip=True), "question_ids": sorted(ids),
                       "source_url": url + "#" + entry["id"]})
    if not points:
        raise ValueError(f"未找到知识点：{url}")
    return points


def content_blocks(question):
    return [question["stem"], *question["options"], question["answer"]]


STYLE = """
body{max-width:960px;margin:40px auto;padding:0 24px;font:17px/1.8 system-ui;color:#21352e;background:#fafbf8}
a{color:#176d5b}article{border-top:1px solid #bccdc5;margin:36px 0;padding-top:20px}
img{display:block;max-width:100%;height:auto;margin:1em auto}pre{overflow:auto;padding:16px;background:#eaf0eb}
table{border-collapse:collapse;max-width:100%}td,th{border:1px solid #bacbc1;padding:6px 12px}
details{background:#eef4ef;padding:12px;margin-top:16px}summary{cursor:pointer}
.markdown-math-fraction{display:inline-flex;vertical-align:middle;flex-direction:column;text-align:center;line-height:1.3}
.markdown-math-numerator{border-bottom:1px solid}.markdown-math-inline{white-space:normal}
.markdown-math-overline{text-decoration:overline}.markdown-matrix-expression{display:inline-flex;align-items:center;gap:.4em}
.markdown-matrix-brackets{border-left:2px solid;border-right:2px solid;padding:0 .4em}.markdown-matrix-grid td{border:0;padding:2px 8px}
"""


def html_document(title, body):
    return (f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'img-src \'self\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            f'<title>{html.escape(title)}</title><style>{STYLE}</style><body>{body}</body></html>')


def render_paper(year, questions, assets):
    def local(block):
        fragment = soup_of(block["html"])
        for image in fragment.select("img[src]"):
            asset = assets.get(image["src"])
            if asset and asset.get("path"):
                image["src"] = "../" + asset["path"]
            else:
                image.replace_with(f"[配图未下载：{image['src']}]")
        return str(fragment)
    body = [f'<a href="../index.html">返回采集目录</a><h1>{year} 年 408 真题采集稿</h1>',
            '<p>来源：四〇八档案室。题目与答案未经人工校对；保留来源，不代表获得转载授权。</p>']
    for q in questions:
        body.append(f'<article id="{q["id"]}"><h2>{q["id"]} · {html.escape(q["subject"])} · {q["score"]} 分</h2>')
        body.append(f'<a href="{html.escape(q["source"]["url"], quote=True)}">原站题目</a>')
        body.append(local(q["stem"]))
        for option in q["options"]:
            body.append(f'<div><b>{html.escape(option["label"])}.</b>{local(option)}</div>')
        body.append('<details><summary>查看原站答案与解析</summary>' + local(q["answer"]) + '</details></article>')
    return html_document(f"{year} 年 408 真题采集稿", "\n".join(body))


def collect(args):
    output = args.output.resolve()
    fetcher = Fetcher(output, args.delay, args.offline, args.refresh)
    report = {"schema_version": 1, "started_at": timestamp(), "source": BASE,
              "status": "running", "papers": [], "errors": []}
    try:
        report["robots"] = fetcher.check_robots()
        home, _ = fetcher.get(BASE)
        inventory = discover_papers(home)
        years = sorted(set(args.years or inventory))
        if set(years) - inventory.keys():
            raise ValueError(f"首页未收录年份：{sorted(set(years) - inventory.keys())}")
        report["requested_years"] = years
        questions = []
        for year in years:
            paper = inventory[year]
            data, meta = fetcher.get(paper["url"])
            parsed = parse_paper(data, paper, meta)
            questions.extend(parsed)
            report["papers"].append({**paper, "questions": len(parsed),
                                     "answers": sum(bool(q["answer"]["text"] or q["answer"]["image_urls"]) for q in parsed)})
            print(f"{year}: {len(parsed)} questions", flush=True)

        knowledge_url = urljoin(BASE, "knowledge")
        data, _ = fetcher.get(knowledge_url)
        knowledge_pages = {knowledge_url: data}
        for link in soup_of(data).select('a[href^="/knowledge?subject="]'):
            url = public_url(link["href"])
            if url not in knowledge_pages:
                knowledge_pages[url] = fetcher.get(url)[0]
        points = {}
        for url, page in knowledge_pages.items():
            for point in parse_knowledge(page, url):
                points[point["id"]] = point
        by_id = {q["id"]: q for q in questions}
        for point in points.values():
            for qid in point["question_ids"]:
                if qid in by_id:
                    by_id[qid]["knowledge_point_ids"].append(point["id"])

        urls = sorted({url for q in questions for b in content_blocks(q) for url in b["image_urls"]})
        assets = {}
        for number, url in enumerate(urls, 1):
            try:
                data, meta = fetcher.get(url)
                suffix = Path(urlsplit(url).path).suffix.lower()
                if suffix not in {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                    raise ValueError(f"无法识别图片格式：{url}")
                if not meta["content_type"].startswith("image/"):
                    raise ValueError(f"图片响应类型异常：{meta['content_type']}")
                path = "assets/" + hashlib.sha256(url.encode()).hexdigest()[:20] + suffix
                write_file(output / path, data)
                assets[url] = {**meta, "path": path}
            except (AccessBlocked, HTTPError) as exc:
                if isinstance(exc, AccessBlocked) or getattr(exc, "code", None) != 404:
                    raise
                assets[url] = {"url": url, "error": str(exc)}
                report["errors"].append({"url": url, "error": str(exc)})
            if number % 25 == 0 or number == len(urls):
                print(f"images: {number}/{len(urls)}", flush=True)

        for q in questions:
            q["knowledge_point_ids"].sort()
            q["assets"] = [assets[url] for url in sorted({u for b in content_blocks(q) for u in b["image_urls"]})]
        for year in years:
            paper_questions = [q for q in questions if q["year"] == year]
            write_json(output / "papers" / f"{year}.json", {"schema_version": 1, **inventory[year], "questions": paper_questions})
            write_file(output / "papers" / f"{year}.html", render_paper(year, paper_questions, assets))
        write_file(output / "questions.jsonl", "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions))
        write_json(output / "knowledge-points.json", sorted(points.values(), key=lambda p: p["id"]))
        write_json(output / "assets.json", list(assets.values()))
        report.update({"status": "complete" if not report["errors"] else "partial",
                       "question_count": len(questions), "image_count": len(urls),
                       "downloaded_images": sum("path" in a for a in assets.values()),
                       "knowledge_point_count": len(points),
                       "tagged_questions": sum(bool(q["knowledge_point_ids"]) for q in questions),
                       "subjects": dict(Counter(q["subject"] for q in questions)),
                       "question_types": dict(Counter(q["type"] for q in questions)),
                       "parsed_choice_answers": sum(q["answer_choice"] is not None for q in questions),
                       "missing_answers": [q["id"] for q in questions if not q["answer"]["text"] and not q["answer"]["image_urls"]]})
        if report["missing_answers"]:
            report["status"] = "partial"
        body = '<h1>408 真题采集目录</h1><p>本地校对资料，来源：<a href="' + BASE + '">四〇八档案室</a>。</p>'
        body += f'<p>{len(questions)} 道题 · {len(points)} 个知识点 · {report["downloaded_images"]}/{len(urls)} 张配图。状态：{report["status"]}</p><ul>'
        body += "".join(f'<li><a href="papers/{year}.html">{year} 年试卷与答案</a> · <a href="papers/{year}.json">JSON</a></li>' for year in reversed(years))
        body += '</ul><p><a href="report.json">完整性报告</a> · <a href="knowledge-points.json">知识点索引</a></p>'
        write_file(output / "index.html", html_document("408 真题采集目录", body))
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"error": str(exc)})
        raise
    finally:
        report["finished_at"] = timestamp()
        report["resources"] = list(fetcher.records.values())
        write_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "resources" / "beokayy")
    parser.add_argument("--years", nargs="+", type=int, help="仅采集指定年份；默认首页列出的全部年份")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数，至少 1 秒")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="只从已校验的缓存重新导出，不联网")
    mode.add_argument("--refresh", action="store_true", help="重新下载所选年份和资源，替换缓存")
    args = parser.parse_args()
    try:
        report = collect(args)
    except Exception as exc:
        parser.exit(1, f"采集未完成：{exc}\n已保存缓存与 report.json，可修复后重跑。\n")
    print(f"{report['status']}: {report['question_count']} questions; {args.output.resolve()}")
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
