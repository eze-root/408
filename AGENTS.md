# 课程项目协作约定

## 项目定位

本仓库是 **计算机考研 408 资料站（408）** 的课程网站与教学资料。站点使用 Sphinx + MyST Markdown，不在文档目录中混入应用服务代码。

内容应面向学生、可直接操作，并优先记录长期稳定的课程知识。具体学期才有效的通知应明确写出学期与日期。

## 内容组织

- `source/lectures/`：四科复习提纲与章节梳理；
- `source/labs/`：选择题、计算题与算法题专项训练；
- `source/assignments/`：历年真题索引、套卷方法与复盘模板；
- `source/resources/`：笔记、试卷、解析和速查资料；
- `source/_static/imgs/`：页面图片；
- `source/_static/files/`：可下载附件；
- `docs/plans/`：课程建设或大型改版计划。

每篇 `source/**/*.md` 页面按以下顺序组织：frontmatter、同名一级标题、`article-info`、正文。frontmatter 至少包含 `title`、`date`、`author` 和 `tags`；展示的作者与日期必须一致。

新增或移动页面时：

- 同步更新所属目录 `index.md` 的 toctree；
- 用 docname 建立站内链接，不写 `.html`；
- 图片统一引用 `/_static/imgs/<文件名>`；
- 全局搜索并更新旧链接；
- 不再使用但仍有教学价值的材料先移至归档目录，不直接删除。

## 工具链

- Python 环境与依赖统一由 uv 管理；用 `uv add` / `uv remove` 修改依赖，不手改 `uv.lock`；
- 用 `npm install` 安装前端依赖，修改后提交 `package-lock.json`；
- HTML 构建：`uv run make clean && uv run make dirhtml`；
- 本地预览：`bash scripts/dev.sh`；
- 不提交 `build/`、`.venv/`、`node_modules/` 和生成的 CSS/PDF。

## 样式与资源

- Tailwind 源文件位于 `source/_static/css/src/site.css`，编译产物 `source/_static/css/site.css` 不提交；
- 改动样式后执行 `uv run make clean && uv run make dirhtml`，确认明暗主题、导航和代码块没有退化；
- 品牌图使用 `source/_static/logo.svg` 与 `favicon.svg`，替换时同步检查 `source/conf.py`；
- 不直接修改 Sphinx 或 Shibuya 安装目录中的文件，定制统一放在仓库内。

## 文档工作流

把课程资料改动当作代码改动，保持术语、命令、日期、导航和评分说明内部一致。

完成任务前：

- 涉及渲染、导航或交叉引用时执行 `uv run make clean && uv run make dirhtml SPHINXOPTS="-W --keep-going"`；
- 执行 `uv run python -m unittest discover -s tests -v`；
- 修复新引入的 warning，不用 suppress 规则掩盖真实问题；
- 纯文本小修改且不影响渲染、导航、链接时可以跳过完整构建。

## Git 与变更范围

- 一个任务对应一个逻辑变更，避免混入无关格式化或课程内容；
- 不覆盖学生提交、教师草稿或工作区中已有的未提交修改；
- 重命名、移动页面前全局搜索引用，改动后再次确认没有旧路径；
- 不提交密钥、token、账号、内部地址、受版权限制的教材全文或学生隐私数据。

## 完成标准

- 内容、导航、交叉引用和附件路径一致；
- 影响渲染或导航的修改通过严格构建，无新增 warning；
- 示例命令经过检查，不包含个人凭据、内网地址或机器专属绝对路径；
- 学期、截止时间、评分规则等高影响信息有明确来源，并保持相关页面同步。
- `AGENTS.md` 与实际目录、命令和部署方式一致。

## 真题排版与部署

- `typst/papers/` 为可编辑题目来源，`typst/answers/` 为配套答案来源，`typst/assets/` 为随仓库保存的题目插图；版本与缺项记录在 `typst/papers/manifest.json`。
- `bash scripts/build-papers.sh` 通过 uv 调用 Typst 0.15.1，生成试题册、答题纸和已收录的答案册；`make dirhtml` 会先执行此步骤。
- 2009—2024 年答案使用 `typst/answers/YYYY.json` 与 `typst/answers/choices/YYYY.md`，公式、代码、表格和 SVG 图均可编辑；2025、2026 年答案使用 Markdown。题面与图像校验值随答案保存，修改后先复核配套关系再更新。`typst/archive/` 保存旧版记录，不参与构建。网站生成按年份整理的 54 份 PDF 压缩包。
- Linux 构建需要 `fonts-noto-cjk` 和 `fonts-dejavu-core`。PDF 生成到 `source/_static/files/papers/`，不提交。
- 涉及试卷内容或版式时，额外执行 `uv run python scripts/check_papers.py`，检查题号、A4 尺寸、页边界和原始标记泄漏，并抽查实际页面。
- OCR 服务只能显式调用；原始资料与任务回执保留在忽略的 `resources/`，不由 CI 上传。`convert_materials.py` 导入到待校对目录，不覆盖人工编辑的试卷。
- `.github/workflows/site.yml` 负责测试、PDF、网站构建与 GitHub Pages 部署；PR 不部署，主分支成功后部署。Pages 的 Source 使用 GitHub Actions。
- Actions 组件固定到具体提交并注明版本；更新时核对官方 release。PR 可取消旧检查，主分支不能中断正在进行的发布。
- 手动运行可取消 `deploy`，只构建检查。失败日志保留 7 天，PDF 下载包保留 14 天；运行摘要中查看各项检查结果。
