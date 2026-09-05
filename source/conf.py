"""Sphinx configuration for 计算机考研 408 资料站."""

from pathlib import Path


project = "\u8ba1\u7b97\u673a\u8003\u7814 408 \u8d44\u6599\u7ad9"
author = "408 \u5b66\u4e60\u5c0f\u7ec4"
copyright = "2026, 408 \u5b66\u4e60\u5c0f\u7ec4"
release = "\u957f\u671f\u66f4\u65b0"

extensions = [
    "sphinx.ext.autosectionlabel",
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxemoji.sphinxemoji",
]

autosectionlabel_prefix_document = True
source_suffix = {".md": "markdown"}
root_doc = "index"
language = "zh_CN"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3

html_theme = "shibuya"
html_title = "\u8ba1\u7b97\u673a\u8003\u7814 408 \u8d44\u6599\u7ad9"
html_baseurl = "https://kaoyan-408.pastel-spool-7598.chatgpt.site"
html_theme_options = {
    "accent_color": "teal",
    "color_mode": "auto",
    # Two levels work better for chapter/section style course navigation while
    # keeping deeply nested lecture headings collapsed by default.
    "globaltoc_expand_depth": 2,
    "toctree_maxdepth": 3,
    "show_ai_links": False,
}
html_static_path = ["_static"]
html_css_files = [
    "https://cdn.jsdelivr.net/npm/source-sans@3.52.0/source-sans-3VF.css",
    "css/site.css",
]
html_logo = "_static/logo.svg"
html_favicon = "_static/favicon.svg"
html_meta = {
    "description": "计算机考研 408 知识框架、专项训练、历年真题与复盘资料站。",
}

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Fail early if brand assets are accidentally removed.
for asset in ("logo.svg", "favicon.svg"):
    if not (Path(__file__).parent / "_static" / asset).is_file():
        raise FileNotFoundError(f"Missing brand asset: {asset}")
