#!/usr/bin/env python3
"""Convert the supplied 408 syllabus and OCR papers into site/Typst sources."""

from __future__ import annotations

import re
import argparse
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYLLABUS_DOCX = ROOT / "resources/考纲/2025年408考纲.docx"
SYLLABUS_MD = ROOT / "source/resources/exam-syllabus-2025.md"
PAPERS_DIR = ROOT / "resources/真题/资料1"
TYPST_PAPERS = ROOT / "typst/papers"
PDF_DIR = ROOT / "source/_static/files/papers"

SUBJECTS = {
    "数据结构考纲": "数据结构",
    "计算机组成原理考纲": "计算机组成原理",
    "操作系统考纲": "操作系统",
    "计算机网络考纲": "计算机网络",
}


def syllabus_markdown() -> str:
    raw = subprocess.check_output(
        ["textutil", "-convert", "txt", "-stdout", str(SYLLABUS_DOCX)],
        text=True,
    )
    lines = [line.replace("\xa0", " ").rstrip() for line in raw.splitlines()]
    out = [
        "---",
        'title: "2025 年 408 计算机学科专业基础考试大纲"',
        "date: 2026-09-05",
        'author: "eze-root"',
        "tags: [408, 考纲, 复习范围]",
        "---",
        "",
        "# 2025 年 408 计算机学科专业基础考试大纲",
        "",
        "```{article-info}",
        ":avatar-outline: muted",
        ":author: eze-root updated on",
        ":date: 2026-09-05",
        ":class-container: sd-p-2 sd-outline-muted sd-rounded-1",
        "```",
        "",
        "本页由仓库中的《2025 年 408 考纲》整理为可检索的 Markdown。内容按数据结构、计算机组成原理、操作系统和计算机网络四科组织；标注“新增”的条目沿用原资料。复习与命题范围请以当年教育主管部门正式发布的考试大纲为准。",
        "",
    ]
    in_targets = False
    current_subject = "408"
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text in SUBJECTS:
            current_subject = SUBJECTS[text]
            out.extend([f"## {current_subject}", ""])
            in_targets = False
        elif text == "考察目标":
            out.extend([f"### {current_subject} · 考查目标", ""])
            in_targets = True
        elif text == "考察内容":
            out.extend([f"### {current_subject} · 考查内容", ""])
            in_targets = False
        elif re.match(r"^第[一二三四五六七八九十]+章\s*", text):
            out.extend([f"#### {text}", ""])
        elif re.match(r"^[（(][一二三四五六七八九十]+[）)]", text):
            out.extend([f"**{text}**", ""])
        elif line.lstrip().startswith("•"):
            out.append(f"- {text[1:].strip()}")
        elif in_targets:
            out.append(f"- {text}")
        else:
            out.append(text)
    return "\n".join(out).strip() + "\n"


QUESTION_RE = re.compile(r"^\s*(?:0?[1-9]|[1-3]\d|4[0-7])\s*[.．、)）]\s*")
ANSWER_MARK_RE = re.compile(
    r"【(?:参考答案|答案|解析|知识点参考)】|^\s*(?:参考)?答案(?:与解析)?\s*$|^\s*解析[:：]\s*$"
)
TITLE_LINE_RE = re.compile(
    r"^(?:#\s*)?.*(?:全国硕士研究生.*考试|计算机科学与技术学科联考|计算机学科专业基础(?:综合)?试题|科目代码|^20\d{2}\s*年).*$"
)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            value = re.sub(r"\s+", " ", "".join(self.cell)).strip()
            self.row.append(value)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.rows.append(self.row)
            self.row = None


def normalize_html_tables(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        parser = _TableParser()
        parser.feed(match.group(0))
        rows = parser.rows
        if not rows:
            return ""
        flat = " ".join(cell for row in rows for cell in row)
        if "考生编号" in flat and "考生姓名" in flat:
            return "\n| 考生信息 | 填写处 |\n| --- | --- |\n| 考生编号 | 　　　　　　 |\n| 考生姓名 | 　　　　　　 |\n"
        columns = max(len(row) for row in rows)
        padded = [row + [""] * (columns - len(row)) for row in rows]
        escaped = [[cell.replace("|", r"\|") for cell in row] for row in padded]
        result = ["| " + " | ".join(escaped[0]) + " |"]
        result.append("| " + " | ".join(["---"] * columns) + " |")
        result.extend("| " + " | ".join(row) + " |" for row in escaped[1:])
        return "\n" + "\n".join(result) + "\n"

    text = re.sub(r"<table\b.*?</table>", replace, text, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"</?html>", "", text, flags=re.IGNORECASE)


def clean_paper(source: Path, year: str) -> str:
    lines = source.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    hiding_answer = False
    in_preamble = True
    for line in lines:
        stripped = line.strip()
        if in_preamble and TITLE_LINE_RE.match(stripped.lstrip("# ")):
            continue
        if stripped and (
            QUESTION_RE.match(stripped)
            or re.search(r"(?:考生注意事项|单项选择题|综合应用题)", stripped)
        ):
            in_preamble = False
        if re.match(r"^#\s*(?:【)?(?:参考)?答案", stripped):
            hiding_answer = True
            continue
        if ANSWER_MARK_RE.search(stripped):
            hiding_answer = True
            continue
        if hiding_answer:
            if QUESTION_RE.match(stripped):
                hiding_answer = False
            else:
                continue
        # Keep the exam paper neutral and remove third-party promotional references.
        if "知识点参考" in stripped or "官网（www." in stripped:
            continue
        out.append(line.rstrip())

    text = normalize_html_tables("\n".join(out))
    relative_dir = source.parent.relative_to(ROOT).as_posix()
    text = re.sub(
        r"\]\((?:\./)?images/",
        # cmarker evaluates image() in exam-template.typ, one level below root.
        f"](../{relative_dir}/images/",
        text,
    )
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import raw materials into review drafts; never overwrite edited papers.")
    parser.add_argument("--syllabus", action="store_true", help="Also regenerate the syllabus (requires macOS textutil)")
    args = parser.parse_args()
    if args.syllabus:
        write_if_changed(SYLLABUS_MD, syllabus_markdown())
    drafts = ROOT / "resources/真题/待校对"
    drafts.mkdir(parents=True, exist_ok=True)

    converted = 0
    for source in sorted(PAPERS_DIR.glob("*/*.md")):
        match = re.match(r"(20\d{2})", source.name)
        if not match:
            continue
        year = match.group(1)
        md_path = drafts / f"{year}.md"
        write_if_changed(md_path, clean_paper(source, year))
        converted += 1

    print(f"Imported {converted} review drafts into {drafts}; edited Typst papers unchanged.")


if __name__ == "__main__":
    main()
