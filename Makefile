# Run targets through uv so Sphinx resolves from the project environment:
#   uv run make dirhtml
SPHINXOPTS    ?=
SPHINXBUILD   ?= python -m sphinx
SOURCEDIR     = source
BUILDDIR      = build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile html dirhtml

html dirhtml:
	@bash scripts/build_css.sh
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
