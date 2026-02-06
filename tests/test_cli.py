# ruff: noqa
import sys
import os
from pathlib import Path
import subprocess
import pytest


TEST_CASES_DIR = Path(__file__).parent / "payloads"


def load_test_cases():
    include_dunders = os.environ.get("CSV4J_INCLUDE_DUNDERS", "") != ""
    return [
        case_dir
        for case_dir in TEST_CASES_DIR.iterdir()
        if case_dir.is_dir() and (include_dunders or not case_dir.name.startswith("__"))
    ]


def files_are_equal(file1: Path, file2: Path) -> bool:
    return file1.read_bytes() == file2.read_bytes()


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,
)
def test_cli_basic(case_dir):
    """Invoke csv4j as a CLI and compare output to expected CSV."""
    out_path = Path("dump") / f"{case_dir.name}.csv"
    # ensure previous output removed
    try:
        out_path.unlink()
    except Exception:
        pass

    cmd = [sys.executable, "src/csv4j.py", "-i", str(case_dir / "in.json"), "-t", str(case_dir / "template.yaml"), "-o", str(out_path)]
    subprocess.run(cmd, check=True)

    assert out_path.exists()
    assert files_are_equal(out_path, case_dir / "out.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,
)
def test_cli_multiline(case_dir):
    out_path = Path("dump") / f"{case_dir.name}_multiline.csv"
    try:
        out_path.unlink()
    except Exception:
        pass

    cmd = [
        sys.executable,
        "src/csv4j.py",
        "-i",
        str(case_dir / "in.json"),
        "-t",
        str(case_dir / "template.yaml"),
        "-o",
        str(out_path),
        "-ml",
    ]
    subprocess.run(cmd, check=True)

    assert out_path.exists()
    assert files_are_equal(out_path, case_dir / "out_multiline.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,
)
def test_cli_custom_sep(case_dir):
    seps = [",", ";", "|"]
    for idx, sep in enumerate(seps):
        out_path = Path("dump") / f"{case_dir.name}_sep.csv"
        try:
            out_path.unlink()
        except Exception:
            pass

        cmd = [
            sys.executable,
            "src/csv4j.py",
            "-i",
            str(case_dir / "in.json"),
            "-t",
            str(case_dir / "template.yaml"),
            "-o",
            str(out_path),
            "-s",
            sep,
        ]
        subprocess.run(cmd, check=True)

        assert out_path.exists()
        assert files_are_equal(out_path, case_dir / f"out_sep_{idx}.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,
)
def test_cli_verbose_flag(case_dir):
    """Ensure verbose flag doesn't break CLI execution."""
    out_path = Path("dump") / f"{case_dir.name}_v.csv"
    try:
        out_path.unlink()
    except Exception:
        pass

    cmd = [
        sys.executable,
        "src/csv4j.py",
        "-i",
        str(case_dir / "in.json"),
        "-t",
        str(case_dir / "template.yaml"),
        "-o",
        str(out_path),
        "-v",
    ]
    subprocess.run(cmd, check=True)

    assert out_path.exists()
    assert files_are_equal(out_path, case_dir / "out.csv")


@pytest.mark.parametrize(
    "case_dir",
    load_test_cases(),
    ids=lambda p: p.name,
)
def test_cli_carry_flag(case_dir):
    """Ensure `-c/--carry` copies the input JSON into the output directory."""
    out_path = Path("dump") / f"{case_dir.name}_carry.csv"
    carry_target = Path("dump") / (case_dir / "in.json").name

    cmd = [
        sys.executable,
        "src/csv4j.py",
        "-i",
        str(case_dir / "in.json"),
        "-t",
        str(case_dir / "template.yaml"),
        "-o",
        str(out_path),
        "-c",
    ]
    subprocess.run(cmd, check=True)

    assert out_path.exists()
    # carry should copy the input file into the output parent dir (dump/)
    assert carry_target.exists()
    assert files_are_equal(carry_target, case_dir / "in.json")
