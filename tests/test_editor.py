import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def sample(tmp_path_factory):
    subprocess.run([sys.executable, str(ROOT / "samples" / "make_sample.py")], check=True)
    return ROOT / "samples" / "sample.pdf"


def run(*args):
    return subprocess.run([sys.executable, "-m", "pdf_toolkit", *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True)


def text_of(path):
    with pymupdf.open(path) as doc:
        return "\n".join(p.get_text() for p in doc)


def test_replace(sample, tmp_path):
    r = run("replace", sample, "-o", tmp_path, "--find", "ACME Corp", "--replace", "Example Inc")
    assert r.returncode == 0, r.stderr
    out = text_of(tmp_path / "sample.pdf")
    assert "Example Inc" in out and "ACME Corp" not in out


def test_insert_after(sample, tmp_path):
    assert run("insert-after", sample, "-o", tmp_path, "--anchor", "Contact:", "--text", "+1-555-0100").returncode == 0
    assert "+1-555-0100" in text_of(tmp_path / "sample.pdf")


def test_headings_suffix(sample, tmp_path):
    assert run("headings", sample, "-o", tmp_path, "--min-size", "16", "--suffix", "- Final", "--seed", "1").returncode == 0
    out = text_of(tmp_path / "sample.pdf")
    assert "Quarterly Report - Final" in out and "Highlights - Final" in out


def test_folder_and_missing_input(sample, tmp_path):
    assert run("replace", sample.parent, "-o", tmp_path, "--find", "ACME", "--replace", "X").returncode == 0
    assert run("replace", "nope.pdf", "-o", tmp_path, "--find", "a", "--replace", "b").returncode == 2
