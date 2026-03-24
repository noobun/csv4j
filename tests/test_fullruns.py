# ruff: noqa
import os
from pathlib import Path
import pytest
import json
import yaml
from types import NoneType

from src.csv4j.csv4j import Csv4J  # noqa: E402

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


class TestPayloadDefault:
    """Test default payloads with standard CSV output."""

    @pytest.mark.parametrize(
        "case_dir",
        load_test_cases(),
        ids=lambda p: p.name,  # test names: test1, test2, ...
    )
    def test_payload_positive(self, case_dir):
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
    def test_payload_positive_manualfeed(self, case_dir):
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
    def test_payload_positive_multiline(self, case_dir):
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
    def test_payload_positive_custom_sep(self, case_dir):
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


SPECIALS_DIR = Path(__file__).parent / "specials"
REGEX_TC = SPECIALS_DIR / "regex"
MULTIINPUT_TC = SPECIALS_DIR / "multiinput"
NULLKEY_TC = SPECIALS_DIR / "nonevar"


class TestPayloadSpecials:
    def test_payload_wildcard_positive(self):
        """Test wildcard loading of inputs/templates and compare output."""
        c = Csv4J()
        assert type(c) is Csv4J
        c.load_input(Path(REGEX_TC / "*.json"), wildcard=True)
        c.load_template(Path(REGEX_TC / "*.yaml"), wildcard=True)
        c.writecsv("dump/regex.csv")

        assert os.path.exists("dump/regex.csv") is True
        assert files_are_equal(Path("dump/regex.csv"), Path(REGEX_TC / "out.csv"))

    def test_payload_wildcard_negative(self):
        """Ensure wildcard without match returns NoneType (error path)."""
        c = Csv4J()
        assert type(c) is Csv4J
        assert type(c.load_input(Path(REGEX_TC / "*.json"))) is NoneType
        assert type(c.load_template(Path(REGEX_TC / "*.yaml"))) is NoneType

    def test_payload_multiinput_positive(self):
        """Load multiple inputs and ensure merged output matches expected."""
        c = Csv4J()
        assert type(c) is Csv4J
        c.load_input(Path(MULTIINPUT_TC / "in1.json"))
        c.load_input(Path(MULTIINPUT_TC / "in2.json"))

        c.load_template(Path(MULTIINPUT_TC / "template.yaml"))
        c.writecsv("dump/multiinput.csv")

        assert os.path.exists("dump/multiinput.csv") is True
        assert files_are_equal(Path("dump/multiinput.csv"), Path(MULTIINPUT_TC / "out.csv"))

    def test_payload_nullkey_positive(self):
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

    def test_payload_carry_api(self):
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
