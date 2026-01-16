# ruff: noqa
import os
from pathlib import Path
import pytest
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
    c = Csv4J(1)
    assert type(c) is Csv4J
    c.load_input(Path(case_dir / "in.json"))
    c.load_template(Path(case_dir / "template.yaml"))
    c.writecsv(Path(f"dump/{case_dir.name}.csv"))

    assert os.path.exists(f"dump/{case_dir.name}.csv") is True
    assert files_are_equal(Path(f"dump/{case_dir.name}.csv"), case_dir / "out.csv")
