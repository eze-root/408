#!/usr/bin/env python3
"""Build exam booklets from reviewed Markdown, without calling OCR or rewriting sources."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pymupdf

try:
    from .paper_downloads import package_downloads
    from .typed_answers import load_typed
except ImportError:
    from paper_downloads import package_downloads
    from typed_answers import load_typed

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
            labels = list(OPTION.finditer(body))
            if labels:
                if [label[1] for label in labels] != list("ABCD"):
                    raise ValueError(f"{year} Q{number}: ambiguous option labels")
                for i, label in enumerate(labels):
                    stop = labels[i + 1].start() if i < 3 else len(body)
                    options.append(body[label.end():stop].strip())
                body = body[:labels[0].start()].strip()
                trailing_figures = [path for option in options for path in IMAGE.findall(option)]
                options = [IMAGE.sub("", option).strip() for option in options]
                body += "".join(f"\n\n![]({path})" for path in trailing_figures)
                if any(not option for option in options):
                    raise ValueError(f"{year} Q{number}: empty answer option")
            elif not figures and number not in metadata.get("incomplete_questions", []):
                raise ValueError(f"{year} Q{number}: no answer options or option figure")
        # Splitting an A-D list inside one code fence can leave the stem's
        # fence open and render a relocated diagram as a literal image path.
        for fragment in [body, *options]:
            if len(re.findall(r"^```", fragment, re.MULTILINE)) % 2:
                raise ValueError(f"{year} Q{number}: code fence crosses stem or option boundary")
        if number >= 41 and "essay_scores" in metadata:
            expected = metadata["essay_scores"]
            if len(expected) != 7 or sum(expected) != 70:
                raise ValueError(f"{year}: essay scores must contain seven values totalling 70")
            score = re.match(r"[（(]\s*(\d+)\s*分[）)]", body)
            if not score or int(score[1]) != expected[number - 41]:
                raise ValueError(f"{year} Q{number}: score does not match the recorded source")
        questions.append({"number": number, "body": body, "options": options})
    return {"year": year, **metadata, "questions": questions}


def prepare(year: str) -> dict:
    metadata = json.loads((PAPERS / "manifest.json").read_text())[year]
    paper = parse_paper((PAPERS / f"{year}.md").read_text(), year=year, metadata=metadata)
    answer_file = ROOT / "typst/answers" / f"{year}.md"
    paper.pop("answers", None)
    if answer_file.exists():
        paper["answers"] = parse_answers(answer_file.read_text(), year=year)
    if (ROOT / f"typst/answers/{year}.json").exists():
        paper["answers"] = load_typed(year)
    if metadata.get("answers") and "answers" not in paper:
        raise ValueError(f"{year}: missing editable answer source")
    paper["figures"] = {}
    for question in paper["questions"] + paper.get("answers", []):
        for path in IMAGE.findall(question["body"] + "\n" + "\n".join(question["options"])):
            asset = (ROOT / "typst" / path).resolve()
            if not asset.is_relative_to(ROOT / "typst/assets") or not asset.is_file():
                raise ValueError(f"{year}: missing or nonportable image {path}")
            if asset.suffix == ".svg":
                svg = ET.parse(asset).getroot()
                if "viewBox" in svg.attrib:
                    _, _, pixel_width, pixel_height = map(float, svg.attrib["viewBox"].split())
                else:
                    pixel_width = float(re.match(r"[\d.]+", svg.attrib["width"])[0])
                    pixel_height = float(re.match(r"[\d.]+", svg.attrib["height"])[0])
            else:
                pix = pymupdf.Pixmap(str(asset))
                pixel_width, pixel_height = pix.width, pix.height
            ratio = pixel_width / pixel_height
            width = metadata.get("figure_widths", {}).get(path, min(132, max(28, pixel_width / 5.5)))
            height = (width / ratio if path in metadata.get("figure_widths", {}) else
                      min(width / ratio, 50 if question["number"] <= 40 else 85))
            paper["figures"][path] = {"width": height * ratio, "height": height}
        lengths = [option_width(option) for option in question["options"]]
        question["option_columns"] = 2 if max(lengths, default=0) <= 24 else 1
        if "choice" not in question:
            score = re.match(r"[（(]\s*(\d+)\s*分[）)]\s*", question["body"])
            question["score"] = int(score[1]) if score else 2
            stem = question["body"][score.end():] if score else question["body"]
            first, separator, rest = stem.partition("\n\n")
            if question["number"] <= 40:
                first = re.sub(r"[（(]\s*[)）][。．]?\s*$", "", first).rstrip()
            question["display_body"] = first + f"（{question['score']}分）" + separator + rest
    paper.setdefault("essay_scores", [q["score"] for q in paper["questions"][40:]])
    if sum(paper["essay_scores"]) != 70:
        raise ValueError(f"{year}: essay scores must total 70")
    folder = ROOT / "build/papers"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{year}.json").write_text(json.dumps(paper, ensure_ascii=False, indent=2))
    return paper


def option_width(source: str) -> float:
    """Estimate typeset width in CJK ems; code/tables stay on their own row."""
    if "```" in source or "![" in source:
        return 100
    text = re.sub(r"\\[A-Za-z]+", "x", source)
    text = re.sub(r"[$^_{}]", "", text)
    return sum(1 if ord(c) > 255 else .55 for c in text)


def parse_answers(source: str, *, year: str) -> list[dict]:
    matches = list(QUESTION.finditer(source))
    if [int(m[1]) for m in matches] != list(range(1, 48)):
        raise ValueError(f"{year}: answers must contain questions 1–47")
    answers = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        body = (match[2] + source[match.end():end]).strip()
        n = int(match[1]); choice = None
        if n <= 40:
            key = re.match(r"^([ABCD])(?:\s|$)", body)
            if not key:
                raise ValueError(f"{year} Q{n}: missing answer letter")
            choice, body = key[1], body[1:].strip()
        elif not body:
            raise ValueError(f"{year} Q{n}: empty solution")
        answers.append({"number": n, "choice": choice, "body": body, "options": []})
    return answers



def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", default=sorted(json.loads((PAPERS / "manifest.json").read_text())))
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
            modes = [("paper", "paper"), ("answer-sheet", "answer-sheet")]
            if "answers" in paper:
                modes.append(("answers", "answers"))
            for mode, suffix in modes:
                entry = PAPERS / f"{year}.typ"
                subprocess.run(["typst", "compile", "--root", str(ROOT), "--input", f"mode={mode}",
                                "--input", f"serif-font={serif}", "--input", f"sans-font={sans}",
                                str(entry), str(OUTPUT / f"{year}-408-{suffix}.pdf")], check=True)
        print(f"{year}: 47 questions · {paper['edition']}", flush=True)
    all_years = sorted(json.loads((PAPERS / "manifest.json").read_text()))
    if not args.prepare_only and sorted(args.years) == all_years:
        print(package_downloads(OUTPUT, all_years))


if __name__ == "__main__":
    main()
