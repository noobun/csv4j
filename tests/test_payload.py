# ruff: noqa
import sys
import os
from pathlib import Path
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from csv4j import Csv4J  # noqa: E402

# tests/test_module_a.py
TEST_CASES_DIR = Path(__file__).parent / "payloads"


def load_test_cases():
    """Discover all test case directories."""
    return [
        case_dir
        for case_dir in TEST_CASES_DIR.iterdir()
        if case_dir.is_dir() and not case_dir.name.startswith("__")
    ]


def files_are_equal(file1: Path, file2: Path) -> bool:
    return file1.read_bytes() == file2.read_bytes()


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive(case_dir):
    c = Csv4J(
        case_dir / "in.json",
        f"dump/{case_dir.name}.csv",
        case_dir / "template.yaml",
        1,
    )
    assert type(c) is Csv4J
    c.process()
    assert os.path.exists(f"dump/{case_dir.name}.csv") is True
    assert files_are_equal(Path(f"dump/{case_dir.name}.csv"), case_dir / "out.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive_multiline(case_dir):
    c = Csv4J(
        case_dir / "in.json",
        f"dump/{case_dir.name}_multiline.csv",
        case_dir / "template.yaml",
        1,
    )
    assert type(c) is Csv4J
    c.process(multiline=True)
    assert os.path.exists(f"dump/{case_dir.name}_multiline.csv") is True
    assert files_are_equal(Path(f"dump/{case_dir.name}_multiline.csv"), case_dir / "out_multiline.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive_custom_sep(case_dir):
    sep = [",", ";", "|"]
    c = Csv4J(
        case_dir / "in.json",
        f"dump/{case_dir.name}_sep.csv",
        case_dir / "template.yaml",
        1,
    )
    assert type(c) is Csv4J
    for index in range(len(sep)):
        c.process(sep=sep[index])
        assert os.path.exists(f"dump/{case_dir.name}_sep.csv") is True
        assert files_are_equal(Path(f"dump/{case_dir.name}_sep.csv"), Path(f"{case_dir}/out_sep_{index}.csv"))
