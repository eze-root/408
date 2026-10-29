# 厦门工学院 408 资料采集

从指定的 408 资料页读取公开 PDF 附件，按年份保存试题与答案。下载范围由页面中的附件链接决定，默认目录为忽略的 `resources/xit/`。

```bash
uv run python scripts/collect_xit.py
uv run python scripts/collect_xit.py --offline
uv run python -m http.server 8002 --bind 127.0.0.1 --directory resources/xit
```

在浏览器打开 `http://127.0.0.1:8002/catalog.html`。

- `source-index.html`：来源页面快照。
- `manifest.json`：年份、类型、来源 URL、SHA-256、字节数、页数与下载状态。
- `YYYY/*.pdf`：原文件。
- `YYYY/*.txt`：PDF 原有文本层的提取结果；脚本不调用 OCR。
- `catalog.html`：本地年份目录。

再次运行会校验已下载文件并继续下载缺项。每个附件下载后立即保存清单；同一年同类资料有多个不同链接时停止自动选择。缓存校验不通过时保留现有文件并报告路径。`--offline` 仅校验缓存并重建目录。

正式 Typst 试题、答案与答题纸通过 `bash scripts/build-papers.sh` 构建。运行 `uv run python scripts/export_papers.py` 可导出按年 PDF、试题答案合册和可独立编译的 Typst 源码包。
