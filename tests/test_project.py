import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectScaffoldTests(unittest.TestCase):
    def test_sphinx_configuration_is_valid_python(self) -> None:
        conf_path = REPO_ROOT / "source/conf.py"
        ast.parse(conf_path.read_text(encoding="utf-8"))

    def test_navigation_targets_exist(self) -> None:
        for relative_path in [
            "source/lectures/index.md",
            "source/labs/index.md",
            "source/assignments/index.md",
            "source/resources/index.md",
        ]:
            self.assertTrue((REPO_ROOT / relative_path).is_file(), relative_path)

    def test_brand_assets_exist(self) -> None:
        for relative_path in [
            "source/_static/logo.svg",
            "source/_static/favicon.svg",
        ]:
            self.assertTrue((REPO_ROOT / relative_path).is_file(), relative_path)


if __name__ == "__main__":
    unittest.main()
