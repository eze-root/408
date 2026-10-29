# 本地题库对照工具

正式试题和答案统一使用 `bash scripts/build-papers.sh` 构建，来源为 `typst/papers/` 和 `typst/answers/`。2026-10-29 已合并 2025、2026 年资料并修订冲突题。

以下采集工具用于保留与比较网页快照，历史导出包保存在本地 `output/pdf/archive/`。

## 比较范围与方法

按年份、题号对应本地 Markdown 与采集 JSON，比较题干、选项和可提取的分值。NFKC、空白和中文标点归一化只用来消除显示差异，不删除数字、运算符或词语。文字相同不意味着图片相同；配图提供两版目视对照。字符三元组相似度用于发现疑似错位，不自动改题号或决定哪个版本正确。

报告写入 `resources/beokayy/comparison/`，包含逐题 JSON 和可浏览 HTML，可从采集预览服务访问 `/comparison/`。2026-10-29 的一次对比中，本地 752 个题号均有采集对应，新增 2025、2026 年 94 题。归一化后 99 题文字相同，653 题存在文字差异；后者包含 OCR、公式表达、简写、补充条件等差别，不是错误题数。

明确需处理的版本差异包括：2012-43、2012-44、2014-45、2014-47 的单题分值，以及 2024-04 的图和选项。不得只用总分或答案字母自动解决这些冲突。已有扫描和人工勘误继续保留，此流程不是独立原卷逐题审定。

## 输出版本

PDF 采用**采集版题面及其配套答案**，封面写明来源、未审定状态与关键冲突。不会把采集答案字母接到选项不一致的本地稿后面。原站选择题只有答案字母，答案册不声称提供这些题的完整解析；综合题保留参考解答。

原站的 HTML 被转换为结构化节点，由仓库内 `typst/collected-exam.typ` 原生排版。保留段落、上下标、取反上划线、分式、矩阵、跨行跨列表格、代码缩进与图片。未知 HTML 元素会报错，不能静默丢弃。`2026-46` 答案的 `≤ft⌊` 显示残片修正为 `⌊`，带有精确匹配前提和日志，原始采集数据不改写。

默认写入忽略的 `output/pdf/`：

- `408-2009-2026-questions.pdf`：带年份书签的试题合集；
- `408-2009-2026-answers.pdf`：带年份书签的参考答案合集；
- `by-year/`：各年试题册与答案册，共 36 份；
- `typst-source/`：可独立编译的 `.typ`、结构化 JSON、图片与显示订正日志；
- `408-papers-answers-and-typst.zip`：按年 PDF、可编辑来源、构建报告和逐题对比数据；
- `build-report.json`、`logs/`：页数、摘要、转换数量与每份 Typst 编译日志。

单独编译导出的源文件：

```bash
cd output/pdf/typst-source
typst compile --input mode=questions 2026.typ 2026-questions.pdf
typst compile --input mode=answers 2026.typ 2026-answers.pdf
```

Linux 可额外传入 `--input serif-font="Noto Serif CJK SC" --input sans-font="Noto Sans CJK SC"`。不要把人工改稿放在生成目录；重建会替换同名文件。只构建部分年份时，合集与报告仅包括所选年份，旧的其他年份文件仍保留。

## 检查

构建器检查 47 题、150 分、A4、题号、答案区、页边界、原始标记泄漏，核对 PDF 中选择题答案表是否与 JSON 一致，并拒绝 Typst warning。试题册不会包含答案内容。完成后仍需抽查实际渲染页面，尤其是含矩阵、公式、长代码和表格的题。

```bash
uv run python -m unittest discover -s tests -v
uv run make clean
uv run make dirhtml SPHINXOPTS="-W --keep-going"
uv run python scripts/check_papers.py
```

最后一条继续检查正式的 38 份试题册、答题纸与答案册。所有采集内容与生成 PDF 保持本地，不自动提交或发布。
