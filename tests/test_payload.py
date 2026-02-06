# ruff: noqa
import sys
import os
from pathlib import Path
import pytest
import json
import yaml

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
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


def files_are_equal(file1: Path, file2: Path) -> bool:
    """Return True when two files have identical bytes."""
    return file1.read_bytes() == file2.read_bytes()


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive(case_dir):
    """Run payload extraction end-to-end and compare produced CSV to expected."""
    c = Csv4J()
    assert type(c) is Csv4J
    c.load_input(Path(case_dir / "in.json"))
    c.load_template(Path(case_dir / "template.yaml"))
    c.writecsv("dump/" + case_dir.name + ".csv")

    assert os.path.exists(f"dump/{case_dir.name}.csv") is True
    assert files_are_equal(Path(f"dump/{case_dir.name}.csv"), case_dir / "out.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive_manualfeed(case_dir):
    """Feed input/template as Python objects, then write and compare output."""
    c = Csv4J()
    assert type(c) is Csv4J

    with open(case_dir / "in.json", "r", encoding="utf-8") as f:
        input = json.load(f)
    c.loads_input(input, id="in")

    with open(case_dir / "template.yaml", "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)
    c.loads_template(template)

    c.writecsv("dump/" + case_dir.name + ".csv")

    assert os.path.exists(f"dump/{case_dir.name}.csv") is True
    assert files_are_equal(Path(f"dump/{case_dir.name}.csv"), case_dir / "out.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive_multiline(case_dir):
    """Validate multiline output mode produces expected CSV."""
    c = Csv4J()
    assert type(c) is Csv4J
    c.load_input(Path(case_dir / "in.json"))
    c.load_template(Path(case_dir / "template.yaml"))
    c.writecsv("dump/" + case_dir.name + ".csv")
    c.customize(sep=",", multiline=True, none="")
    c.writecsv("dump/" + case_dir.name + "_multiline.csv")
    assert os.path.exists(f"dump/{case_dir.name}_multiline.csv") is True
    assert files_are_equal(Path(f"dump/{case_dir.name}_multiline.csv"), case_dir / "out_multiline.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,  # test names: test1, test2, ...
)
def test_payload_positive_custom_sep(case_dir):
    """Validate custom separators produce expected CSV outputs."""
    sep = [",", ";", "|"]
    c = Csv4J()
    assert type(c) is Csv4J
    c.load_input(Path(case_dir / "in.json"))
    c.load_template(Path(case_dir / "template.yaml"))
    for index in range(len(sep)):
        c.customize(sep=sep[index], multiline=False, none="")
        c.writecsv(f"dump/{case_dir.name}_sep.csv")
        assert os.path.exists(f"dump/{case_dir.name}_sep.csv") is True
        assert files_are_equal(Path(f"dump/{case_dir.name}_sep.csv"), Path(f"{case_dir}/out_sep_{index}.csv"))
