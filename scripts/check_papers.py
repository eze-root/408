#!/usr/bin/env python3
"""Check generated A4 PDFs for missing content, broken code fences and page overflow."""
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def visible_question_numbers(doc):
    numbers = []
    for page in doc:
        # Font metrics can merge a number with the first word of the stem.
        # Match the prefix at the number column's 22 mm left edge; keep the
        # sequence intact so an absent, duplicated or reordered number fails.
        for x0, y0, x1, y1, word, *_ in page.get_text("words"):
            match = re.match(r"(\d{1,2})\.", word)
            if 61 <= x0 <= 65 and match:
                numbers.append(int(match[1]))
    return numbers


def answer_headings(text):
    """Require the score suffix: a wrapped percentage is not a question heading."""
    return [(int(number), int(score)) for number, score in re.findall(
        r"^(\d{2})\.\s*[（(]\s*(\d+)\s*分[）)]", text, re.MULTILINE)]


def main():
    folder = ROOT / "source/_static/files/papers"
    files = sorted(folder.glob("*.pdf"))
    manifest = json.loads((ROOT / "typst/papers/manifest.json").read_text())
    expected = {f"{year}-408-{kind}.pdf" for year, meta in manifest.items()
                for kind in ["paper", "answer-sheet"] + (["answers"] if meta.get("answers") else [])}
    actual = {path.name for path in files}
    if actual != expected:
        raise ValueError(f"PDF file mismatch: missing={expected - actual}, extra={actual - expected}")
    pages = 0
    for path in files:
        with pymupdf.open(path) as doc:
            text = "\n".join(page.get_text() for page in doc)
            if any(marker in text for marker in ("```", "![", "assets/", "【答案】", "【解析】", "【参考答案】", "**（")):
                raise ValueError(f"{path.name}: raw markup or answer leaked into PDF")
            if "answer-sheet" in path.name:
                if len(doc) != 8:
                    raise ValueError(f"{path.name}: answer sheet should have 8 pages")
                for n, page in enumerate(doc):
                    if n and f"第 {n + 40} 题" not in page.get_text():
                        raise ValueError(f"{path.name}: missing answer area {n + 40}")
            elif "-answers" in path.name:
                from build_papers import prepare
                paper = prepare(path.name[:4])
                keys = re.findall(r"^[ABCD]$", doc[0].get_text(), re.MULTILINE)
                headings = answer_headings(text)
                if headings != list(zip(range(41, 48), paper["essay_scores"])):
                    raise ValueError(f"{path.name}: essay answer headings mismatch: {headings}")
                if keys != [q["choice"] for q in paper["answers"][:40]]:
                    raise ValueError(f"{path.name}: rendered answer key differs from source")
                if int(path.name[:4]) <= 2024:
                    choices = [int(n) for n in re.findall(r"^(\d{1,2})\.\s*答案：[ABCD]", text, re.MULTILINE)]
                    if choices != list(range(1, 41)):
                        raise ValueError(f"{path.name}: missing or duplicate choice explanations")
                    if any(page.get_images() for page in doc):
                        raise ValueError(f"{path.name}: raster pages or figures in native answer book")
                    if len(doc.get_toc()) < 8:
                        raise ValueError(f"{path.name}: missing question bookmarks")

            else:
                question_numbers = visible_question_numbers(doc)
                if question_numbers != list(range(1, 48)):
                    raise ValueError(f"{path.name}: missing or duplicate visible question numbers: {question_numbers}")
            for page in doc:
                if abs(page.rect.width - 595.276) > 1 or abs(page.rect.height - 841.89) > 1:
                    raise ValueError(f"{path.name}: not A4")
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        for span in line["spans"]:
                            if span["text"].strip() and span["size"] < 4:
                                raise ValueError(f"{path.name} page {page.number + 1}: text smaller than 4 pt")
                for block in page.get_text("blocks"):
                    if block[0] < 12 or block[1] < 8 or block[2] > page.rect.width - 12 or block[3] > page.rect.height - 8:
                        raise ValueError(f"{path.name} page {page.number + 1}: content overflows printable page")
            pages += len(doc)
            print(f"{path.name}: {len(doc)} A4 pages")
    print(f"Checked {len(files)} PDFs, {pages} pages.")


if __name__ == "__main__":
    main()
