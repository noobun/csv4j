# ruff: noqa
from pathlib import Path
import pytest

from src.csv4j.csv4j import parse_args  # noqa: E402

TEST_CASES_DIR = Path(__file__).parent / "payloads"


class TestArgparse:
    def test_argparse_basic(self):
        """Test basic argument parsing."""
        args = parse_args(["-i", "input.json", "-t", "template.yaml", "-o", "output.csv"])
        assert isinstance(args.input, list)
        assert isinstance(args.template, Path)
        assert isinstance(args.output, Path)

        assert args.input == [Path("input.json")]
        assert args.template == Path("template.yaml")
        assert args.output == Path("output.csv")

    def test_argparse_flags(self):
        """Test parsing of optional flags."""
        args = parse_args(["-i", "input.json", "-t", "template.yaml", "-o", "output.csv", "-v", "-c", "-m"])
        assert args.multiline is True
        assert args.verbose == 1
        assert args.carry is True

    @pytest.mark.parametrize(
        "sep",
        [",", ";", "|"],
        ids=lambda p: p,  # test names: test1, test2, ...
    )
    def test_argparse_sep(self, sep):
        """Test custom separator argument."""
        args = parse_args(["-i", "input.json", "-t", "template.yaml", "-o", "output.csv", "-s", sep])
        assert args.sep == sep

    def test_argparse_defaults(self):
        """Test that optional arguments have correct defaults."""
        args = parse_args(["-i", "input.json", "-t", "template.yaml", "-o", "output.csv"])
        assert args.multiline is False
        assert args.verbose == 0
        assert args.carry is False
        assert args.sep == ","
        assert args.none == ""
