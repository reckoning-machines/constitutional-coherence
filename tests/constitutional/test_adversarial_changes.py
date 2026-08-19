from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from constitutional.validate import validate_repository


CASES = sorted((Path(__file__).parent / "adversarial").glob("*.yaml"))


@pytest.mark.parametrize("case_path", CASES, ids=lambda path: path.stem)
def test_adversarial_change_fails_closed(
    plain_repository: Path,
    apply_mutation,
    case_path: Path,
) -> None:
    """A locally plausible patch that introduces a second authority is refused."""

    case = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    apply_mutation(plain_repository, case["mutation"])

    errors = validate_repository(plain_repository)

    assert any(case["expected_error"] in error for error in errors), errors
