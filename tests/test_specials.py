# ruff: noqa
import sys
import os
from pathlib import Path
from types import NoneType

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from csv4j import Csv4J  # noqa: E402

# tests/test_module_a.py
SPECIALS_DIR = Path(__file__).parent / "specials"
REGEX_TC = SPECIALS_DIR / "regex"
MULTIINPUT_TC = SPECIALS_DIR / "multiinput"


def files_are_equal(file1: Path, file2: Path) -> bool:
    return file1.read_bytes() == file2.read_bytes()


def test_payload_wildcard_positive():
    c = Csv4J(1)
    assert type(c) is Csv4J
    c.load_input(Path(REGEX_TC / "*.json"), wildcard=True)
    c.load_template(Path(REGEX_TC / "*.yaml"), wildcard=True)
    c.writecsv("dump/regex.csv")

    assert os.path.exists("dump/regex.csv") is True
    assert files_are_equal(Path("dump/regex.csv"), Path(REGEX_TC / "out.csv"))


def test_payload_wildcard_negative():
    c = Csv4J(1)
    assert type(c) is Csv4J
    assert type(c.load_input(Path(REGEX_TC / "*.json"))) is NoneType
    assert type(c.load_template(Path(REGEX_TC / "*.yaml"))) is NoneType


def test_payload_multiinput_positive():
    c = Csv4J(1)
    assert type(c) is Csv4J
    c.load_input(Path(MULTIINPUT_TC / "in1.json"))
    c.load_input(Path(MULTIINPUT_TC / "in2.json"))

    c.load_template(Path(MULTIINPUT_TC / "template.yaml"))
    c.writecsv("dump/multiinput.csv")

    assert os.path.exists("dump/multiinput.csv") is True
    assert files_are_equal(Path("dump/multiinput.csv"), Path(MULTIINPUT_TC / "out.csv"))
