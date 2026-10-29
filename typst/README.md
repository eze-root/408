# 408 真题与答案排版

Typst 0.15.1 生成 2009—2026 年试题册、答题纸和答案与解析，共 54 个 PDF。A4 黑白排版，正文 12 磅；题干后标分数，选项独立排列，选择题整题同页，综合题按题分页。答题纸共 8 页。

## 构建

```bash
uv sync --locked
bash scripts/build-papers.sh
bash scripts/build-papers.sh --years 2025 2026
uv run python scripts/check_papers.py
```

Linux 安装 `fonts-noto-cjk`、`fonts-dejavu-core`。macOS 使用宋体、黑体与 DejaVu Sans Mono。下载件输出至 `source/_static/files/papers/`；`make dirhtml` 自动先生成 PDF。PDF、CSS 与 `build/` 中间文件不提交。

## 内容来源

- `papers/YYYY.md`：试题，题号使用 `## 1.` 至 `## 47.`。
- `answers/YYYY.json`：2009—2024 年结构化答案，包含公式、表格、代码及配图；绑定试题与图像校验值。
- `answers/choices/YYYY.md`：对应年份的 40 道选择题解析。
- `answers/corrections/`：综合题补全与订正，构建时读取，保持单一来源。
- `assets/answers/YYYY/`：重绘 SVG 图；`answer-content.typ` 排版原生内容节点。
- `answers/typesetting-review.json`：本轮重排与内容订正记录。
- `answers/YYYY.md`：2025、2026 年答案，同样使用 1—47 题号；前 40 题标题后填写 A—D，正文可写解析。
- `papers/YYYY.typ`、`exam-template.typ`：年度入口与共享版式。
- `assets/YYYY/`：题目与答案插图，Markdown 路径以 `assets/` 开头。
- `papers/manifest.json`：综合题分值、答案可用性及图像尺寸设置。
- `papers/sources.json`：来源链接、文件摘要和扫描页说明。
- `papers/corrections-2026-10-29.json`：本轮冲突判断、依据与具体人工复核项。
- `../docs/reviews/archive/`：历史审查记录。

选择题选项使用 `A.`、`B.`、`C.`、`D.`；代码使用带语言的围栏，公式使用 `$...$` 或 `$$...$$`。图像默认保持题干中的位置；旧稿中落在选项后的整题配图会移回题干。

## 校对与验证

改题时记录年份、题号、来源页码及采用结果，修改后执行单元测试、PDF 检查并抽查渲染页面。检查包括题号、分值、选项、答案表、A4 尺寸、字体下限、页边界和原始标记。

原始资料保留在忽略的 `resources/` 中，CI 构建仅使用仓库内的 Markdown、Typst 和插图。OCR 只在明确调用时运行：

```bash
uv run python scripts/ocr_papers.py --endpoint "$OCR_ENDPOINT" --years 2022
```

`convert_materials.py` 将 OCR 导入 `resources/真题/待校对/`；人工维护的试题来源独立保存。

## 答案维护

日常修改编辑 `answers/YYYY.json`、`answers/choices/YYYY.md`，或被引用的 `answers/corrections/`。代码块可以包含空行；导入器保留段落、分数式、上下标、矩阵、表格与代码缩进。所有 47 题必须有解析，答案表须与已核对的 40 个答案字母一致。修改题面后先重新核对答案及选项，再更新配套校验值。

`import_typed_answers.py` 是显式的离线初次导入工具，读取缓存题库，拒绝覆盖已维护的年度 JSON。日常构建不调用导入器、OCR 或远程资料服务。旧扫描排版记录归档在 `archive/scan-edition-2026-10-29/`，原 PDF 与页图仅留在忽略的 `resources/`。

`build_papers.py` 同时生成按年份分目录的 54 份 PDF 下载包。`export_papers.py` 另导出答案合订本、试题合订本与可独立编译的 Typst 来源包。网站全部下载链接指向本站文件。
