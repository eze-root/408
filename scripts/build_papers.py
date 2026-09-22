#!/usr/bin/env python3
"""Build exam booklets from reviewed Markdown, without calling OCR or rewriting sources."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "typst/papers"
OUTPUT = ROOT / "source/_static/files/papers"
QUESTION = re.compile(r"^## (\d{1,2})[.．]\s*(.*)$", re.MULTILINE)
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
OPTION = re.compile(r"(?<!\S)([ABCD])\.[ \t]*")
ANSWER = re.compile(r"【(?:答案|解析|参考答案)】|这题全选|暂无解析|知识点参考")


def parse_paper(source: str, *, year: str, metadata: dict) -> dict:
    # A trailing Markdown backslash becomes literal when a stem or option is
    # split off and stripped. Two spaces preserve internal hard breaks without
    # leaking a backslash at the end of the resulting fragment.
    lines = []
    in_code = False
    for line in source.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code:
            line = re.sub(r"(?<!\\)\\[ \t]*$", "  ", line)
        lines.append(line)
    source = "\n".join(lines)
    matches = list(QUESTION.finditer(source))
    numbers = [int(match[1]) for match in matches]
    if numbers != list(range(1, 48)):
        raise ValueError(f"{year}: expected questions 1–47 exactly once, got {numbers}")
    questions = []
    for index, match in enumerate(matches):
        number = int(match[1])
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        body = (match[2] + source[match.end():end]).strip()
        if ANSWER.search(body):
            raise ValueError(f"{year} Q{number}: answer or explanation leaked into paper")
        options = []
        if number <= 40:
            # OCR often places a question's diagram after D; keep it with the stem.
            figures = IMAGE.findall(body)
            body = IMAGE.sub("", body)
            labels = list(OPTION.finditer(body))
            if labels:
                if [label[1] for label in labels] != list("ABCD"):
                    raise ValueError(f"{year} Q{number}: ambiguous option labels")
                for i, label in enumerate(labels):
                    stop = labels[i + 1].start() if i < 3 else len(body)
                    options.append(body[label.end():stop].strip())
                body = body[:labels[0].start()].strip()
                if any(not option for option in options):
                    raise ValueError(f"{year} Q{number}: empty answer option")
            elif not figures and number not in metadata.get("incomplete_questions", []):
                raise ValueError(f"{year} Q{number}: no answer options or option figure")
            body += "".join(f"\n\n![]({path})" for path in figures)
        questions.append({"number": number, "body": body, "options": options})
    return {"year": year, **metadata, "questions": questions}


def prepare(year: str) -> dict:
    metadata = json.loads((PAPERS / "manifest.json").read_text())[year]
    paper = parse_paper((PAPERS / f"{year}.md").read_text(), year=year, metadata=metadata)
    paper["figures"] = {}
    for question in paper["questions"]:
        for path in IMAGE.findall(question["body"] + "\n" + "\n".join(question["options"])):
            asset = (ROOT / "typst" / path).resolve()
            if not asset.is_relative_to(ROOT / "typst/assets") or not asset.is_file():
                raise ValueError(f"{year}: missing or nonportable image {path}")
            pix = pymupdf.Pixmap(str(asset))
            ratio = pix.width / pix.height
            width = min(148, max(30, pix.width / 4.5))
            height = min(width / ratio, 55 if question["number"] <= 40 else 92)
            paper["figures"][path] = {"width": height * ratio, "height": height}
    folder = ROOT / "build/papers"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{year}.json").write_text(json.dumps(paper, ensure_ascii=False, indent=2))
    return paper


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", default=[str(y) for y in range(2009, 2025)])
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    fonts = set(subprocess.check_output(["typst", "fonts"], text=True).splitlines())
    serif = next((font for font in ["Noto Serif CJK SC", "Songti SC", "STSong"] if font in fonts), None)
    sans = next((font for font in ["Noto Sans CJK SC", "Heiti SC", "Hei"] if font in fonts), None)
    if not serif or not sans:
        raise SystemExit("Install Chinese fonts (Linux: fonts-noto-cjk) before compiling papers.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for year in args.years:
        paper = prepare(year)
        if not args.prepare_only:
            for mode, suffix in [("paper", "paper"), ("answer-sheet", "answer-sheet")]:
                subprocess.run(["typst", "compile", "--root", str(ROOT), "--input", f"mode={mode}",
                                "--input", f"serif-font={serif}", "--input", f"sans-font={sans}",
                                str(PAPERS / f"{year}.typ"), str(OUTPUT / f"{year}-408-{suffix}.pdf")], check=True)
        print(f"{year}: 47 questions · {paper['edition']}", flush=True)


if __name__ == "__main__":
    main()
