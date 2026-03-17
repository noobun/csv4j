# ruff: noqa
import sys
import os
from pathlib import Path
from types import NoneType

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "csv4j"))
)

from csv4j import Csv4J  # noqa: E402

# tests/test_module_a.py
SPECIALS_DIR = Path(__file__).parent / "specials"
REGEX_TC = SPECIALS_DIR / "regex"
MULTIINPUT_TC = SPECIALS_DIR / "multiinput"
NULLKEY_TC = SPECIALS_DIR / "nonevar"


def files_are_equal(file1: Path, file2: Path) -> bool:
    """Return True when two files have identical bytes."""
    return file1.read_bytes() == file2.read_bytes()


def test_payload_wildcard_positive():
    """Test wildcard loading of inputs/templates and compare output."""
    c = Csv4J()
    assert type(c) is Csv4J
    c.load_input(Path(REGEX_TC / "*.json"), wildcard=True)
    c.load_template(Path(REGEX_TC / "*.yaml"), wildcard=True)
    c.writecsv("dump/regex.csv")

    assert os.path.exists("dump/regex.csv") is True
    assert files_are_equal(Path("dump/regex.csv"), Path(REGEX_TC / "out.csv"))


def test_payload_wildcard_negative():
    """Ensure wildcard without match returns NoneType (error path)."""
    c = Csv4J()
    assert type(c) is Csv4J
    assert type(c.load_input(Path(REGEX_TC / "*.json"))) is NoneType
    assert type(c.load_template(Path(REGEX_TC / "*.yaml"))) is NoneType


def test_payload_multiinput_positive():
    """Load multiple inputs and ensure merged output matches expected."""
    c = Csv4J()
    assert type(c) is Csv4J
    c.load_input(Path(MULTIINPUT_TC / "in1.json"))
    c.load_input(Path(MULTIINPUT_TC / "in2.json"))

    c.load_template(Path(MULTIINPUT_TC / "template.yaml"))
    c.writecsv("dump/multiinput.csv")

    assert os.path.exists("dump/multiinput.csv") is True
    assert files_are_equal(Path("dump/multiinput.csv"), Path(MULTIINPUT_TC / "out.csv"))


def test_payload_nullkey_positive():
    """Load multiple inputs and ensure merged output matches expected."""
    c = Csv4J()
    assert type(c) is Csv4J
    c.load_input(Path(NULLKEY_TC / "in.json"))
    c.load_template(Path(NULLKEY_TC / "template.yaml"))

    for null_val in ["NA", "NULL"]:
        c.customize(sep=",", multiline=False, none=null_val)
        c.writecsv(f"dump/nullvalue_{null_val}.csv")

        assert os.path.exists(f"dump/nullvalue_{null_val}.csv") is True
        assert files_are_equal(Path(f"dump/nullvalue_{null_val}.csv"), Path(NULLKEY_TC / f"out_{null_val}.csv"))


def test_payload_carry_api():
    """API mode: verify that providing `carry` copies the input file to the target location."""
    c = Csv4J()
    assert type(c) is Csv4J
    src = MULTIINPUT_TC / "in1.json"
    target = Path("dump") / src.name

    # call load_input with carry pointing at the dump directory
    res = c.load_input(src, wildcard=False, carry=Path("dump"))
    assert res is not None
    assert target.exists()
    assert files_are_equal(target, src)
