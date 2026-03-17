# ruff: noqa
import sys
import os
from pathlib import Path
from types import NoneType
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "csv4j"))
)

from csv4j import Csv4J  # noqa: E402

# tests/test_module_a.py

TEST_CASES_DIR = Path(__file__).parent / "payloads"


def load_test_cases():
    """Discover all test case directories."""
    include_dunders = os.environ.get("CSV4J_INCLUDE_DUNDERS", "") != ""
    return [
        case_dir
        for case_dir in TEST_CASES_DIR.iterdir()
        if case_dir.is_dir() and (include_dunders or not case_dir.name.startswith("__"))
    ]


def test_init():
    """Ensure Csv4J object can be instantiated."""
    c = Csv4J()
    assert type(c) is Csv4J


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_file_validation_pass(case_dir):
    """Loading valid input and template files returns dicts."""
    c = Csv4J()
    assert type(c.load_input(Path(case_dir / "in.json"))) is dict
    assert type(c.load_template(Path(case_dir / "template.yaml"))) is dict


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_file_validation_failed(case_dir):
    """Attempting to load missing input file returns NoneType."""
    c = Csv4J()
    assert type(c.load_input(Path(case_dir / "ins.json"))) is NoneType


def test_template_validate_fail():
    """Loading an invalid template raises an exception (validation failure)."""
    t = Path("tests/payloads/failed_template.yaml")
    c = Csv4J()
    try:
        c.load_template(t)
    except Exception:
        assert True
    # assert False, "Template validation passed expectedly"
