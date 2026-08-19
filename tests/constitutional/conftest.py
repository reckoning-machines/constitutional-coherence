"""Shared machinery for constitutional witnesses.

Every constitutional test works the same way: take this repository, put it
somewhere disposable, change it the way a plausible patch would, and ask the
harness what it thinks. Only the verdict differs.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Mapping

import pytest

from constitutional.measure import BASE_REF_ENV


ROOT = Path(__file__).resolve().parents[2]
IGNORED = shutil.ignore_patterns(
    ".git", "build", ".pytest_cache", "__pycache__", "*.egg-info", "*.sqlite3"
)


def _copy(destination: Path) -> Path:
    shutil.copytree(ROOT, destination, ignore=IGNORED)
    return destination


def _apply(repository: Path, mutation: Mapping[str, Any]) -> None:
    target = repository / mutation["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    operation = mutation["operation"]
    if operation == "append":
        target.write_text(
            target.read_text(encoding="utf-8") + mutation["content"], encoding="utf-8"
        )
    elif operation == "write":
        target.write_text(mutation["content"], encoding="utf-8")
    elif operation == "replace":
        text = target.read_text(encoding="utf-8")
        find = mutation["find"]
        assert find in text, f"fixture anchor not found in {mutation['path']}"
        target.write_text(text.replace(find, mutation["content"], 1), encoding="utf-8")
    elif operation == "copy":
        shutil.copyfile(repository / mutation["source"], target)
    else:
        raise AssertionError(f"Unknown fixture operation: {operation}")


@pytest.fixture
def apply_mutation() -> Callable[[Path, Mapping[str, Any]], None]:
    return _apply


@pytest.fixture(autouse=True)
def _no_ambient_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never inherit a baseline from the surrounding environment.

    CI exports CONSTITUTIONAL_BASE_REF so the workflow gates itself against the
    trunk. That ref does not exist inside a test's temporary repository, and a
    baseline that cannot be resolved fails closed, so every gate case would
    report the gate as unavailable instead of exercising it. Each test supplies
    its own baseline or deliberately has none.
    """

    monkeypatch.delenv(BASE_REF_ENV, raising=False)


@pytest.fixture
def plain_repository(tmp_path: Path) -> Path:
    """A disposable copy with no git history, so the gate has no baseline."""

    return _copy(tmp_path / "repository")


@pytest.fixture
def baselined_repository(tmp_path: Path) -> Path:
    """A disposable copy whose current state is committed as the baseline."""

    if shutil.which("git") is None:
        pytest.skip("git is required to exercise the constitutional gate")
    repository = _copy(tmp_path / "repository")
    run = lambda *args: subprocess.run(
        ["git", "-C", str(repository), *args], check=True, capture_output=True
    )
    run("init", "-q")
    run("add", "-A")
    run(
        "-c",
        "user.email=witness@example.invalid",
        "-c",
        "user.name=Constitutional Witness",
        "commit",
        "-qm",
        "baseline",
    )
    return repository
