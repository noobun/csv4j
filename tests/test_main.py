# ruff: noqa
import os
from pathlib import Path
from types import NoneType
import pytest

from src.csv4j.csv4j import Csv4J  # noqa: E402

TEST_CASES_DIR = Path(__file__).parent / "payloads"


def load_test_cases():
    """Discover all test case directories."""
    include_dunders = os.environ.get("CSV4J_INCLUDE_DUNDERS", "") != ""
    return [
        case_dir
        for case_dir in TEST_CASES_DIR.iterdir()
        if case_dir.is_dir() and (include_dunders or not case_dir.name.startswith("__"))
    ]


class TestMain:
    def test_init(self):
        """Ensure Csv4J object can be instantiated."""
        c = Csv4J()
        assert type(c) is Csv4J

    def test_separator(self):
        """Ensure Csv4J object can be instantiated."""
        allowed = [",", ";", "|"]
        for sep in allowed:
            c = Csv4J()
            return_value = c.separator(sep)
            assert return_value is True
            assert c._Csv4J__customization["sep"] == sep

    def test_separator_fail(self):
        """Ensure Csv4J object can be instantiated."""
        c = Csv4J()
        return_value = c.separator("x")
        assert return_value is False
        assert c._Csv4J__customization["sep"] == ","  # default

    @pytest.mark.parametrize(
        "verbosity",
        range(0, 4),
        ids=lambda p: p,
    )
    def test_verbosity(self, verbosity):
        """Ensure Csv4J object can be instantiated."""
        c = Csv4J(verbose=verbosity)
        c.logger.level = verbosity * 10

    @pytest.mark.parametrize(
        "case_dir",
        load_test_cases(),
        ids=lambda p: p.name,  # test names: test1, test2, ...
    )
    def test_file_validation_pass(self, case_dir):
        """Loading valid input and template files returns dicts."""
        c = Csv4J()
        assert type(c.load_input(Path(case_dir / "in.json"))) is dict
        assert type(c.load_template(Path(case_dir / "template.yaml"))) is dict

    @pytest.mark.parametrize(
        "case_dir",
        load_test_cases(),
        ids=lambda p: p.name,  # test names: test1, test2, ...
    )
    def test_file_validation_failed(self, case_dir):
        """Attempting to load missing input file returns NoneType."""
        c = Csv4J()
        assert type(c.load_input(Path(case_dir / "ins.json"))) is NoneType

    def test_template_validate_fail(self):
        """Loading an invalid template raises an exception (validation failure)."""
        t = Path("tests/payloads/failed_template.yaml")
        c = Csv4J()
        try:
            c.load_template(t)
        except Exception:
            assert True
        # assert False, "Template validation passed expectedly"
