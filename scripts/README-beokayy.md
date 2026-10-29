# 四〇八档案室公开题库采集

`collect_beokayy.py` 从 <https://zhenti.beokayy.club/> 首页发现试卷年份，读取每年的公开整卷页面，提取题干、选项、答案、分值、科目、配图、视频链接和知识点对应关系。视频只保存链接。不会访问账号、收藏、错题本、付费课程或调用 OCR。

## 运行

```bash
uv sync --locked
# 首页列出的全部年份；串行采集，请求间隔至少 1 秒
uv run python scripts/collect_beokayy.py

# 指定年份。汇总文件只包含这次选择的年份
uv run python scripts/collect_beokayy.py --years 2025 2026

# 默认复用缓存；中断后直接重跑同一命令
uv run python scripts/collect_beokayy.py

# 完全不联网，从已校验的缓存重新生成导出
uv run python scripts/collect_beokayy.py --offline

# 显式重新下载，更新来源快照
uv run python scripts/collect_beokayy.py --refresh
```

默认输出为 Git 忽略的 `resources/beokayy/`。可用 `--output` 指定另一个独立输出目录；目录由采集器管理，同名导出和 `--refresh` 对应的原始缓存会被替换。不要把人工校订文件放入这个目录。不同采集批次需要长期保留时使用不同的输出目录。

每次联网运行先重新检查 `robots.txt`，遵守禁止路径与请求间隔。404 表示没有该文件；401、403、登录跳转和站外跳转会停止采集。429 和临时服务器错误有限重试，服务器要求长时间等待时停止。遇到题目结构改变、题号缺失或重复、选择题选项不完整、分值合计不符时，以非零状态退出并保留缓存和失败报告。

## 输出与字段

| 文件 | 用途 |
| --- | --- |
| `index.html` | 离线阅读入口，按年进入试卷，答案可展开 |
| `papers/YYYY.html` | 本地配图的试卷阅读页，不执行原站脚本 |
| `papers/YYYY.json` | 该年试卷元数据与完整题目列表 |
| `questions.jsonl` | 每行一道题，适合后续检索、对比与导入 |
| `knowledge-points.json` | 知识点 ID、名称、科目、章节、题号与来源链接 |
| `assets.json` | 图片来源 URL、本地路径、SHA-256 和采集时间 |
| `assets/` | 下载的题目、选项和答案配图；不含二维码或站点 Logo |
| `raw/` | 原始响应字节及 URL、状态、类型、SHA-256、UTC 时间侧录 |
| `report.json` | 本次范围、完整性状态、题量、缺失答案、图片和资源清单 |

逐题记录包含 `id`、`year`、`number`、`subject`、`type`、`score`、`stem`、`options`、`answer`、`answer_choice`、`knowledge_point_ids`、`assets`、`video_urls`、`source` 与 `review_status`。

科目名称统一使用“计算机组成原理”，原站题卡中的“组成原理”另保存在 `source.subject`，以便与知识点索引关联。

`stem`、`answer` 和每个选项同时保留 `html`、便于搜索的 `text`、`image_urls`。HTML 保留表格、上下标、分式和代码；纯文本用于检索，不能替代公式与表格原貌。JSON 中的图片 URL 保留原站地址，本地文件映射见 `assets`，HTML 阅读页使用相对路径。`answer` 是原站答案区域的全部内容，可能只有答案字母，也可能有详细解答；不把只有答案的题目标记成拥有完整解析。`answer_choice` 仅识别明确写出的单选答案，无法确定时为 null。

知识点索引保留四科全部条目；`--years` 只筛选题目，因此知识点中可能有其他年份的题号。只采集部分年份时，之前其他年份的导出文件不会被删除，但本次 `index.html`、`questions.jsonl` 与报告只涵盖所选年份。

`status=complete` 表示通过结构与资源检查；`partial` 表示有图片 404 或缺失答案；`failed` 表示采集中断。后两者均返回非零退出码。中断时可能留有上一次成功导出，使用数据前先检查本次 `report.json` 的状态、时间和年份。

## 阅读与校对

直接打开 `resources/beokayy/index.html`，或启动仅本机可访问的预览：

```bash
uv run python -m http.server 8001 --bind 127.0.0.1 --directory resources/beokayy
```

浏览器访问 <http://127.0.0.1:8001/>。此服务与课程站点的 8000 端口独立。

所有题目初始状态为 `unverified`，结构检查通过不等于题目、答案或知识点归属正确。原始资料保持在忽略的 `resources/` 中，不自动导入 `typst/papers/`、不发布到课程站点，也不由 CI 上传；人工核对并确认可用范围后再单独导入。采集不改变来源内容的权利归属。

## 验证

采集后可继续运行本地真题对比与 Typst 配套试题、答案排版，见 [对比与 PDF 说明](README-paper-comparison.md)。

```bash
uv run python -m unittest discover -s tests -v
uv run python scripts/collect_beokayy.py --offline
```

测试使用自行构造的 HTML，不联网、不提交第三方试题全文，覆盖字段提取、题号与分值校验、代码和公式保留、图片本地化、缓存损坏、robots 限制及拒绝访问。
