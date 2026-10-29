# 计算机考研 408 资料站

数据结构、计算机组成原理、操作系统与计算机网络的复习提纲、练习方法和历年试卷。

- 内容范围：数据结构、计算机组成原理、操作系统、计算机网络
- 资料类型：复习提纲、练题方法、历年真题索引与订正记录
- 维护方式：长期更新

## 开始使用

需要 Python 3.13+、[uv](https://docs.astral.sh/uv/)、Node.js 22 和 Typst 0.15.1。Linux 安装 `fonts-noto-cjk` 与 `fonts-dejavu-core`；macOS 需有宋体、黑体和 DejaVu Sans Mono。

```bash
uv sync --locked
npm ci
uv run make dirhtml
```

生成结果位于 `build/dirhtml/`。本地实时预览：

```bash
bash scripts/dev.sh
```

默认访问 <http://localhost:8000>。修改依赖时同步提交 `uv.lock` 或 `package-lock.json`。

## 编写课程内容

课程页面都放在 `source/` 下：

- `lectures/`：四科复习提纲；
- `labs/`：选择题、计算题与算法题专项训练；
- `assignments/`：历年真题索引、审查记录与订正表；
- `resources/`：笔记、试卷、解析和速查资料；
- `_static/imgs/`：图片；
- `_static/files/`：学生可下载的附件。

每个 Markdown 页面保留以下结构：

````md
---
title: 页面标题
date: 2026-09-01
author: eze-root
tags: [讲义]
---

# 页面标题

```{article-info}
:avatar-outline: muted
:author: eze-root updated on
:date: 2026-09-01
:class-container: sd-p-2 sd-outline-muted sd-rounded-1
```
````

新增页面后，把它加入相应目录 `index.md` 的 `{toctree}`。站内链接使用 docname，例如 `` {doc}`lectures/data-structures` ``，不要写死 `.html`。

## 常用命令

```bash
# 严格构建；CI 也执行这一条
uv run make clean
uv run make dirhtml SPHINXOPTS="-W --keep-going"

# 只构建 CSS
npm run build:css

# 实时预览 Markdown 和 CSS
bash scripts/dev.sh
```

## 提交前检查

```bash
uv run make clean
uv run make dirhtml SPHINXOPTS="-W --keep-going"
uv run python -m unittest discover -s tests -v
```

## 试卷排版与下载

网站构建会先生成 2009—2026 年的试题册、配套答题纸和答案与解析，共 54 个 PDF。需要安装 **Typst 0.15.1**；Linux 另需 `fonts-noto-cjk`、`fonts-dejavu-core`。macOS 使用已有宋体、黑体和 DejaVu Sans Mono。

```bash
bash scripts/build-papers.sh --years 2022
uv run python scripts/check_papers.py
```

排版源文件、答案校订与 OCR 工作流见 [typst/README.md](typst/README.md)。历次修订对照扫描试题、解析和题库核实题面，补全各年份配套答案；2012 年第47题补齐解析，2023 年第41题修正入度／出度算法。2009—2024 年的 640 道选择题、112 道综合题解析全部采用原生文字、公式、代码、表格和 SVG 排版。详细结果见 [试卷审查记录](source/assignments/paper-review.md)。构建不依赖本机的原始 `resources/`，也不会请求 OCR 服务。

## 外部题库采集

可显式运行 `uv run python scripts/collect_beokayy.py`，将四〇八档案室的公开试卷、答案、配图及知识点索引保存到忽略的 `resources/beokayy/`。支持缓存续跑与离线导出，结果先用于校对，不覆盖现有试卷。运行方式与字段说明见 [题库采集说明](scripts/README-beokayy.md)。

## GitHub Actions 与发布

`.github/workflows/site.yml` 使用以下流程：

1. 按锁文件安装依赖，先检查题目源文件和网站配置；
2. 生成 54 份 PDF 和网站，Sphinx warning 会使构建失败；
3. 检查 PDF 的题号、纸张尺寸和页边界；
4. 保存试卷下载包和网站，主分支检查通过后发布到 GitHub Pages。

PR 只检查，不发布；新提交会取消该 PR 的旧检查。主分支的新运行会等待当前发布完成。手动运行时可取消勾选 `deploy`，只检查和保存产物。

Actions 页面显示各项检查结果。`408-printable-papers` 保存 14 天，`github-pages` 保存 7 天；失败时额外保存 `408-build-logs`，保留 7 天。构建限时 15 分钟，部署限时 10 分钟。

Action 固定到具体提交，行末注明版本。升级时核对官方 release 和输入参数，再运行完整构建。Python、Node.js、uv 和 Typst 的版本在工作流中统一配置。

仓库的 **Settings → Pages → Source** 需要选择 **GitHub Actions**。默认网址为 <https://eze-root.github.io/408/>。使用其他地址时，在仓库的 **Settings → Secrets and variables → Actions → Variables** 设置 `SITE_URL`（保留末尾 `/`）；本地构建使用同名环境变量。生成的 PDF、CSS 和网页不提交到 Git。
