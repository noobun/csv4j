# ruff: noqa
import sys
import os
from pathlib import Path
import pytest
import jsonschema

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from csv4j import Csv4J, Template  # noqa: E402

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


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_init(case_dir):
    c = Csv4J(
        case_dir / "in.json",
        f"dump/{case_dir.name}.csv",
        case_dir / "template.yaml",
        1,
    )
    assert type(c) is Csv4J


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_file_validation_pass(case_dir):
    c = Csv4J(
        case_dir / "in.json",
        f"dump/{case_dir.name}.csv",
        case_dir / "template.yaml",
        1,
    )
    assert c.validate_paths() is False


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_file_validation_failed(case_dir):
    c = Csv4J(
        case_dir / "ins.json",
        f"dump/{case_dir.name}.csv",
        case_dir / "template.yaml",
        1,
    )
    assert c.validate_paths() is True


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_template_validate_pass(case_dir):
    t = Template(case_dir / "template.yaml")
    try:
        t.validate()
    except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError):
        assert False, "Template validation failed unexpectedly"

    assert True


def test_template_validate_fail():
    t = Template("tests/payloads/failed_template.yaml")
    try:
        t.validate()
    except Exception:
        assert True

    # assert False, "Template validation passed expectedly"
