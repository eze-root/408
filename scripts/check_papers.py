#!/usr/bin/env python3
"""Check generated A4 PDFs for missing content, broken code fences and page overflow."""
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "source/_static/files/papers"
    files = sorted(folder.glob("*.pdf"))
    if len(files) != 32:
        raise ValueError(f"Expected 32 generated PDFs, found {len(files)}")
    pages = 0
    for path in files:
        with pymupdf.open(path) as doc:
            text = "\n".join(page.get_text() for page in doc)
            if "```" in text or "【答案】" in text or "【解析】" in text:
                raise ValueError(f"{path.name}: raw markup or answer leaked into PDF")
            if "answer-sheet" in path.name:
                if len(doc) != 8:
                    raise ValueError(f"{path.name}: answer sheet should have 8 pages")
                for n, page in enumerate(doc):
                    if n and f"第 {n + 40} 题" not in page.get_text():
                        raise ValueError(f"{path.name}: missing answer area {n + 40}")
            else:
                question_numbers = []
                for page in doc:
                    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
                        if 61 <= x0 <= 65 and re.fullmatch(r"\d{1,2}\.", word):
                            question_numbers.append(int(word[:-1]))
                if question_numbers != list(range(1, 48)):
                    raise ValueError(f"{path.name}: missing or duplicate visible question numbers: {question_numbers}")
            for page in doc:
                if abs(page.rect.width - 595.276) > 1 or abs(page.rect.height - 841.89) > 1:
                    raise ValueError(f"{path.name}: not A4")
                for block in page.get_text("blocks"):
                    if block[0] < 12 or block[1] < 8 or block[2] > page.rect.width - 12 or block[3] > page.rect.height - 8:
                        raise ValueError(f"{path.name} page {page.number + 1}: content overflows printable page")
            pages += len(doc)
            print(f"{path.name}: {len(doc)} A4 pages")
    print(f"Checked {len(files)} PDFs, {pages} pages.")


if __name__ == "__main__":
    main()
