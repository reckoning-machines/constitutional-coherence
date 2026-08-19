from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from constitutional.validate import validate_repository


ROOT = Path(__file__).resolve().parents[2]
CASES = sorted((Path(__file__).parent / "adversarial").glob("*.yaml"))


def _copy_repository(target: Path) -> Path:
    destination = target / "repository"
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", "build", ".pytest_cache", "__pycache__"),
    )
    return destination


@pytest.mark.parametrize("case_path", CASES, ids=lambda path: path.stem)
def test_adversarial_change_fails_closed(tmp_path: Path, case_path: Path) -> None:
    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    repository = _copy_repository(tmp_path)
    mutation = case["mutation"]
    target = repository / mutation["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if mutation["operation"] == "append":
        target.write_text(
            target.read_text(encoding="utf-8") + "\n" + mutation["content"],
            encoding="utf-8",
        )
    elif mutation["operation"] == "write":
        target.write_text(mutation["content"], encoding="utf-8")
    else:
        raise AssertionError(f"Unknown fixture operation: {mutation['operation']}")

    errors = validate_repository(repository)

    assert any(case["expected_error"] in error for error in errors), errors
