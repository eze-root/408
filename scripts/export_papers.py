#!/usr/bin/env python3
"""Package the reviewed PDFs and portable Typst sources after build-papers.sh."""
import json
from pathlib import Path
import shutil
import zipfile
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'


def merge(inputs, target):
    with pymupdf.open() as doc:
        toc = []
        for label, path in inputs:
            toc.append([1, label, len(doc) + 1])
            with pymupdf.open(path) as part:
                offset = len(doc)
                toc.extend([level + 1, title, page + offset]
                           for level, title, page in part.get_toc())
                doc.insert_pdf(part)
        doc.set_toc(toc)
        doc.save(target, garbage=4, deflate=True)
    with pymupdf.open(target) as check:
        if len(check.get_toc()) != len(toc):
            raise ValueError(f'Bookmarks missing in {target}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'typst/papers/manifest.json').read_text())
    # Preserve the earlier web-snapshot exports before producing reviewed files.
    archive = OUT / 'archive/collected-2026-10-29'
    if not archive.exists():
        archive.mkdir(parents=True)
        for path in list(OUT.iterdir()):
            if path.name not in ('archive', 'qa'):
                shutil.move(str(path), archive / path.name)
    annual = OUT / 'by-year'
    annual.mkdir(exist_ok=True)
    source = OUT / 'typst-source'
    if source.exists():
        shutil.rmtree(source)  # Regenerate this exported directory; keep originals in typst/.
    source.mkdir()
    for name in ('assets', 'papers', 'answers'):
        shutil.copytree(ROOT / 'typst' / name, source / name, dirs_exist_ok=True)
    shutil.copytree(ROOT / 'docs/reviews', source / 'docs/reviews', dirs_exist_ok=True)
    for name in ('exam-template.typ', 'answer-content.typ'):
        shutil.copy2(ROOT / 'typst' / name, source / name)
    shutil.copytree(ROOT / 'build/papers', source / 'data', dirs_exist_ok=True)
    for year, meta in manifest.items():
        entry = '#import "exam-template.typ": exam\n'
        entry += '#let paper = json("data/' + year + '.json")\n'
        entry += '#exam(paper)\n'
        (source / f'{year}.typ').write_text(entry)
        for kind in ['paper', 'answer-sheet'] + (['answers'] if meta.get('answers') else []):
            path = ROOT / f'source/_static/files/papers/{year}-408-{kind}.pdf'
            shutil.copy2(path, annual / path.name)
    (source / 'README.md').write_text('''# 可编辑 Typst 排版来源

使用 Typst 0.15.1。`data/` 保存编译用题目与答案数据，`assets/` 保存插图，`exam-template.typ` 是共享模板。`papers/`、`answers/` 同时保留 Markdown 原稿与校订记录。

在本目录编译：

```bash
typst compile --root . --input mode=paper --input serif-font="Songti SC" --input sans-font="Heiti SC" 2026.typ 2026-paper.pdf
typst compile --root . --input mode=answers --input serif-font="Songti SC" --input sans-font="Heiti SC" 2026.typ 2026-answers.pdf
```

Linux 将字体替换为 Noto Serif CJK SC、Noto Sans CJK SC。`mode=answer-sheet` 生成答题纸。修改编译数据可直接重新排版；课程仓库内通过 `scripts/build_papers.py` 将 Markdown 更新为编译数据。
''')
    combined = []
    for year in ('2025', '2026'):
        target = OUT / f'{year}-408-试题与答案.pdf'
        merge([('试题', annual / f'{year}-408-paper.pdf'),
               ('答案与解析', annual / f'{year}-408-answers.pdf')], target)
        combined.append(target)
    merge([(f'{y} 年试题', annual / f'{y}-408-paper.pdf') for y in sorted(manifest)],
          OUT / '408-2009-2026-questions.pdf')
    merge([(f'{y} 年答案', annual / f'{y}-408-answers.pdf') for y in sorted(manifest)],
          OUT / '408-2009-2026-answers.pdf')
    target = OUT / '408-papers-answers-and-typst.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for folder in (annual, source):
            for path in sorted(folder.rglob('*')):
                if path.is_file(): z.write(path, path.relative_to(OUT))
        for path in combined: z.write(path, path.name)
    print(f'{len(list(annual.glob("*.pdf")))} annual PDFs, {len(combined)} combined PDFs: {target}')


if __name__ == '__main__':
    main()
