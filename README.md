# 计算机考研 408 资料站

数据结构、计算机组成原理、操作系统与计算机网络的一站式复习资料、历年真题和备考路线。

- 内容范围：数据结构、计算机组成原理、操作系统、计算机网络
- 资料类型：知识地图、专项训练、历年真题索引与复盘模板
- 维护方式：长期更新

## 开始使用

需要 Python 3.13+、[uv](https://docs.astral.sh/uv/) 和 Node.js 20+。

```bash
uv sync
npm install
uv run make dirhtml
```

生成结果位于 `build/dirhtml/`。本地实时预览：

```bash
bash scripts/dev.sh
```

默认访问 <http://localhost:8000>。首次安装生成的 `uv.lock` 与 `package-lock.json` 应提交到版本库。

## 编写课程内容

课程页面都放在 `source/` 下：

- `lectures/`：四科知识地图；
- `labs/`：选择题、计算题与算法题专项训练；
- `assignments/`：历年真题索引与复盘模板；
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

网站构建会先生成 2009—2024 年的试题册和配套答题纸，共 32 个 PDF。需要安装 **Typst 0.15.1**；Linux 另需 `fonts-noto-cjk`、`fonts-dejavu-core`。macOS 使用已有宋体、黑体和 DejaVu Sans Mono。

```bash
bash scripts/build-papers.sh --years 2022
uv run python scripts/check_papers.py
```

排版源文件、OCR 工作流与已知内容缺项见 [typst/README.md](typst/README.md)。2023、2024 年为有缺项的回忆资料，页面明确标注，不作为完整计分模拟卷。构建不依赖本机的原始 `resources/`，也不会请求 OCR 服务。

## GitHub Actions 与发布

`.github/workflows/site.yml` 在主分支推送、PR 和手动触发时安装依赖、生成 PDF、严格构建网页并执行测试与 PDF 检查。主分支成功后发布到 GitHub Pages；PR 只构建与检查。每次运行还会保存 `408-printable-papers` 下载产物。

仓库的 **Settings → Pages → Source** 需要选择 **GitHub Actions**。默认网址为 <https://eze-root.github.io/408/>；其他部署地址可通过 `SITE_URL` 配置。生成的 PDF/CSS/网页留在构建产物中，不提交到 Git。
