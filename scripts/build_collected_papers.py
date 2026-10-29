"""Build paired Typst question/answer PDFs without replacing the local paper edition."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from bs4 import BeautifulSoup, NavigableString, Comment
import pymupdf

from scripts.build_papers import ROOT
from scripts.collect_beokayy import write_file, write_json


DISPLAY_CORRECTIONS = [{"id": "2026-46", "field": "answer", "old": "≤ft⌊", "new": "⌊",
                        "reason": "原站将 LaTeX left 指令错误显示为 ≤ft；保留取整符号与原公式，移除显示残片。"}]


def corrected_html(question, field):
    value = question[field]["html"]
    for correction in DISPLAY_CORRECTIONS:
        if question["id"] == correction["id"] and field == correction["field"]:
            if value.count(correction["old"]) != 1:
                raise ValueError(f"显示订正前提已变化：{question['id']}")
            value = value.replace(correction["old"], correction["new"])
    return value


def image_size(path):
    if path.suffix == ".svg":
        root = ET.fromstring(path.read_text())
        view = root.get("viewBox")
        if view:
            _, _, w, h = map(float, re.split(r"[ ,]+", view.strip()))
        else:
            w, h = (float(re.match(r"[\d.]+", root.get(key)).group()) for key in ("width", "height"))
    else:
        pix = pymupdf.Pixmap(str(path))
        w, h = pix.width, pix.height
    width = min(150, max(45, w / 4.5))
    height = min(90, width * h / w)
    return round(height * w / h, 2), round(height, 2)


class Converter:
    def __init__(self, dataset, source):
        self.dataset, self.source = dataset, source
        self.assets = {a["url"]: a for a in json.loads((dataset / "assets.json").read_text())}
        self.counts = Counter()

    def nodes(self, parent):
        result = []
        for child in parent.children:
            converted = self.node(child)
            if converted is not None:
                result.append(converted)
        return result

    def node(self, tag):
        if isinstance(tag, Comment):
            return None
        if isinstance(tag, NavigableString):
            return {"kind": "text", "value": str(tag).replace("\n", " ")} if str(tag) else None
        name, classes = tag.name, tag.get("class", [])
        if name in {"script", "style"}:
            raise ValueError("Unexpected executable HTML")
        if name == "img":
            asset = self.assets[tag["src"]]
            source = self.dataset / asset["path"]
            if hashlib.sha256(source.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(f"Image checksum mismatch: {source}")
            target = self.source / asset["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            width, height = image_size(source)
            self.counts["images"] += 1
            return {"kind": "image", "path": asset["path"], "width": width, "height": height}
        if name == "pre":
            code = tag.find("code")
            langs = code.get("class", []) if code else []
            self.counts["code_blocks"] += 1
            return {"kind": "code", "value": tag.get_text(), "block": True,
                    "lang": next((c.removeprefix("language-") for c in langs if c.startswith("language-")), "text")}
        if name == "code":
            return {"kind": "code", "value": tag.get_text(), "block": False, "lang": "text"}
        if "markdown-math-fraction" in classes:
            self.counts["fractions"] += 1
            return {"kind": "fraction", "top": self.nodes(tag.select_one(".markdown-math-numerator")),
                    "bottom": self.nodes(tag.select_one(".markdown-math-denominator"))}
        if "markdown-math-overline" in classes:
            self.counts["overlines"] += 1
            return {"kind": "overline", "children": self.nodes(tag)}
        if name == "table":
            rows = tag.find_all("tr")
            if "markdown-matrix-grid" in classes:
                self.counts["matrices"] += 1
                return {"kind": "matrix", "rows": [[self.nodes(cell) for cell in row.find_all(["td", "th"], recursive=False)] for row in rows]}
            self.counts["tables"] += 1
            cells, occupied, columns = [], set(), 0
            for y, row in enumerate(rows):
                x = 0
                for cell in row.find_all(["td", "th"], recursive=False):
                    while (x, y) in occupied:
                        x += 1
                    colspan, rowspan = int(cell.get("colspan", 1)), int(cell.get("rowspan", 1))
                    cells.append({"x": x, "y": y, "colspan": colspan, "rowspan": rowspan,
                                  "header": cell.name == "th", "children": self.nodes(cell)})
                    occupied.update((xx, yy) for xx in range(x,x+colspan) for yy in range(y,y+rowspan))
                    x += colspan
                    columns = max(columns, x)
            return {"kind": "table", "columns": columns, "cells": cells}
        if name in {"ol", "ul"}:
            return {"kind": "list", "ordered": name == "ol", "items": [self.nodes(li) for li in tag.find_all("li", recursive=False)]}
        mapping = {"p": "p", "strong": "strong", "em": "em", "sup": "sup", "sub": "sub", "br": "br", "h3": "heading", "h4": "heading"}
        if name not in mapping and name not in {"div", "span", "figure"}:
            raise ValueError(f"Unsupported HTML element: {name}")
        return {"kind": mapping.get(name, "group"), "children": self.nodes(tag)}

    def content(self, value):
        return self.nodes(BeautifulSoup(value, "html.parser"))


def notices(year, comparisons):
    results = []
    for r in comparisons:
        if r["year"] != year:
            continue
        if "单题分值不同" in r.get("flags", []):
            results.append(f"第 {r['number']} 题：本地稿 {r['local_score']} 分，采集版 {r['remote_score']} 分；本册采用采集版分值，待核。")
    if year == 2024:
        results.append("第 4 题两版的图与选项均有差异。答案字母只适用于本册采集版题面，不可直接套用于原本地稿。")
    if year == 2023:
        results.append("本地已记录第 43、44 题的来源疑点；本册保留采集版题面与解答，不据两版局部一致宣布疑点已解决。")
    if year in (2025, 2026):
        results.append("本地可编辑试卷原收录至 2024 年，本年份为新增采集资料，尚未经独立原卷逐题校对。")
    if year == 2026:
        results.append("第 46 题答案中的 LaTeX left 指令显示残片已移除，取整公式保留。订正日志随源文件保存。")
    return results


def check_pdf(path, year, mode):
    with pymupdf.open(path) as doc:
        alltext = "\n".join(p.get_text() for p in doc)
        numbers = []
        for page in list(doc)[1:]:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line["spans"])
                    m = re.match(r"(\d{1,2})\.\s*[（(]\s*\d+\s*分[）)]", text)
                    if 61 <= line["bbox"][0] <= 65 and m:
                        numbers.append(int(m[1]))
        if mode == "questions" and numbers != list(range(1,48)):
            raise ValueError(f"{path.name}: question numbers {numbers}")
        if mode == "questions" and any(t in alltext for t in ("答案：", "答案:", "【答案】", "【解析】")):
            raise ValueError(f"{path.name}: answer leaked into questions")
        if mode == "answers":
            for n in range(41,48):
                if not re.search(rf"第\s*{n}\s*题", alltext):
                    raise ValueError(f"{path.name}: missing answer {n}")
        for page in doc:
            if abs(page.rect.width-595.276)>1 or abs(page.rect.height-841.89)>1:
                raise ValueError(f"{path.name}: not A4")
            body_text = page.get_text(clip=pymupdf.Rect(55, 55, 550, 795))
            if len(re.sub(r"\s+", "", body_text)) < 20 and not page.get_images():
                raise ValueError(f"{path.name} p{page.number+1}: empty or orphan page")
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if span["text"].strip() and span["size"] < 4:
                            raise ValueError(f"{path.name} p{page.number+1}: unreadably small text {span['text']!r}")
            for rect in page.get_text("blocks"):
                if rect[0]<35 or rect[1]<8 or rect[2]>page.rect.width-35 or rect[3]>page.rect.height-8:
                    raise ValueError(f"{path.name} p{page.number+1}: overflow {rect[:4]}")
        for marker in ("![", "```", "assets/", "markdown-math-", "\ufffd"):
            if marker in alltext:
                raise ValueError(f"{path.name}: raw marker {marker}")
        return {"file": str(path), "year": year, "mode": mode, "pages": len(doc), "a4": True,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def build(args):
    dataset, output = args.dataset.resolve(), args.output.resolve()
    source = output / "typst-source"
    source.mkdir(parents=True, exist_ok=True)
    converter = Converter(dataset, source)
    comparison = json.loads((dataset / "comparison/comparison.json").read_text())
    qs = [json.loads(x) for x in (dataset / "questions.jsonl").read_text().splitlines()]
    years = sorted(set(args.years or [q["year"] for q in qs]))
    shutil.copyfile(ROOT / "typst/collected-exam.typ", source / "template.typ")
    fonts = set(subprocess.check_output(["typst", "fonts"], text=True).splitlines())
    serif = next(f for f in ("Noto Serif CJK SC", "Songti SC", "STSong") if f in fonts)
    sans = next(f for f in ("Noto Sans CJK SC", "Heiti SC", "Hei") if f in fonts)
    annual = output / "by-year"
    annual.mkdir(exist_ok=True)
    checked = []
    for year in years:
        questions = sorted([q for q in qs if q["year"] == year], key=lambda q:q["number"])
        if [q["number"] for q in questions] != list(range(1,48)) or sum(q["score"] for q in questions) != 150:
            raise ValueError(f"{year}: invalid paper data")
        converted = []
        for q in questions:
            lengths = [len(o["text"]) for o in q["options"]]
            cols = 4 if lengths and max(lengths)<14 else 2 if lengths and max(lengths)<35 else 1
            if any(o["image_urls"] for o in q["options"]):
                cols = 1
            converted.append({"id": q["id"], "number": q["number"], "score": q["score"], "subject": q["subject"],
                              "stem": converter.content(corrected_html(q, "stem")),
                              "options": [{"label": o["label"], "content": converter.content(o["html"])} for o in q["options"]],
                              "option_columns": cols, "answer_choice": q["answer_choice"],
                              "answer": converter.content(corrected_html(q, "answer"))})
        paper = {"year": year, "questions": converted, "notices": notices(year, comparison["questions"]),
                 "fetched_date": questions[0]["source"]["fetched_at"][:10]}
        write_json(source / f"{year}.json", paper)
        write_file(source / f"{year}.typ", f'#import "template.typ": exam\n#exam(json("{year}.json"))\n')
        for mode in ("questions", "answers"):
            path = annual / f"{year}-408-{mode}.pdf"
            result = subprocess.run(["typst", "compile", "--root", str(source), "--input", f"mode={mode}",
                                     "--input", f"serif-font={serif}", "--input", f"sans-font={sans}",
                                     str(source / f"{year}.typ"), str(path)], capture_output=True, text=True)
            write_file(output / "logs" / f"{year}-{mode}.log", result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(result.stderr)
            if "warning:" in result.stderr:
                raise RuntimeError("Typst warning requires review: " + result.stderr)
            checked.append(check_pdf(path, year, mode))
            if mode == "answers":
                with pymupdf.open(path) as doc:
                    letters = re.findall(r"(?m)^([ABCD])$", doc[1].get_text())
                    if letters != [q["answer_choice"] for q in questions[:40]]:
                        raise ValueError(f"{year}: PDF answer key differs from source")
            print(f"{year} {mode}: {checked[-1]['pages']} A4 pages", flush=True)
    for mode in ("questions", "answers"):
        combined = pymupdf.open()
        toc = []
        for year in years:
            toc.append([1, f"{year} 年 408 {'试题' if mode=='questions' else '参考答案'}", len(combined)+1])
            with pymupdf.open(annual / f"{year}-408-{mode}.pdf") as part:
                combined.insert_pdf(part)
        combined.set_toc(toc)
        combined.set_metadata({"title": f"408 {years[0]}-{years[-1]} {'试题合集' if mode=='questions' else '参考答案合集'}", "author": "408 资料整理"})
        combined.save(output / f"408-{years[0]}-{years[-1]}-{mode}.pdf", garbage=4, deflate=True)
        combined.close()
    write_json(output / "build-report.json", {"created_at": datetime.now().isoformat(), "years": years,
               "content_elements": dict(converter.counts), "files": checked,
               "edition": "采集题面与答案配套，不覆盖本地人工稿", "comparison_summary": comparison["summary"]})
    write_json(source / "display-corrections.json", [c for c in DISPLAY_CORRECTIONS if int(c["id"][:4]) in years])
    write_file(source / "README.txt", "Typst 0.15.1 可编辑来源。数据来自公开题库，未经逐题独立校对。\n"
               "macOS 默认使用宋体/黑体，Linux 请安装 Noto CJK 并传入字体参数。\n"
               "编译示例：typst compile --input mode=questions 2026.typ 2026-questions.pdf\n"
               "参考答案：typst compile --input mode=answers 2026.typ 2026-answers.pdf\n"
               "Linux 添加 --input serif-font=\"Noto Serif CJK SC\" --input sans-font=\"Noto Sans CJK SC\"\n")
    with zipfile.ZipFile(output / "408-papers-answers-and-typst.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for directory in (annual, source):
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(output))
        archive.write(output / "build-report.json", "build-report.json")
        archive.write(dataset / "comparison/comparison.json", "comparison.json")
        # Preserve the readable side-by-side report and both editions' images.
        for path in sorted((dataset / "comparison").rglob("*")):
            if path.is_file():
                archive.write(path, Path("review/comparison") / path.relative_to(dataset / "comparison"))
        for path in sorted((dataset / "assets").rglob("*")):
            if path.is_file():
                archive.write(path, Path("review/assets") / path.relative_to(dataset / "assets"))
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "resources/beokayy")
    parser.add_argument("--output", type=Path, default=ROOT / "output/pdf")
    parser.add_argument("--years", nargs="+", type=int)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
