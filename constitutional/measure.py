"""Measure the actual Constitutional Delta between a git baseline and the tree.

The Plan records what change was authorized. This module records what change
actually happened, by observing two repository states and subtracting them. It
never reads the Plan, and it never reads a hand-written Verify record. That
separation is the whole point: a forecast that is compared only against itself
measures nothing.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from typing import Any, Iterator, Mapping

import yaml

from constitutional.discover import (
    TOPOLOGY_PATH,
    ObservedRepository,
    allowed_writers,
    canonical_carriers,
    discover_repository,
    load_yaml,
    path_matches,
    representation_index,
)


GATE_RULES_PATH = Path("constitutional/gate_rules.yaml")
MEASURED_OUTPUT = Path("build/constitutional/measured-delta.yaml")

BASE_REF_ENV = "CONSTITUTIONAL_BASE_REF"
BASE_CANDIDATES = ("origin/main", "origin/master", "main", "master")

COMPARED_FLAGS = (
    "duplicate_independent_writers",
    "legacy_successor_writes",
    "browser_owned_truth",
    "mutable_present_historical_dependency",
)


# ---------------------------------------------------------------- git plumbing


def run_git(root: Path, *args: str) -> str | None:
    """Run a read-only git command, returning stripped stdout or None on failure."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def is_git_repository(root: Path) -> bool:
    return run_git(root, "rev-parse", "--git-dir") is not None


def resolve_base_ref(root: Path, explicit: str | None = None) -> str | None:
    """Resolve the commit the working tree is measured against.

    Order: explicit argument, environment override, merge-base with a known
    trunk, then HEAD (which gates uncommitted work). Returns None outside a git
    repository or in a repository with no commits.
    """

    if not is_git_repository(root):
        return None
    for candidate in (explicit, os.environ.get(BASE_REF_ENV)):
        if candidate:
            resolved = run_git(root, "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}")
            return resolved or None
    head = run_git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if head is None:
        return None
    for candidate in BASE_CANDIDATES:
        if run_git(root, "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}") is None:
            continue
        merge_base = run_git(root, "merge-base", "HEAD", candidate)
        if merge_base:
            return merge_base
    return head


def changed_paths(root: Path, base: str) -> tuple[str, ...]:
    """Repository-relative paths that differ between the baseline and the tree."""

    tracked = run_git(root, "diff", "--name-only", base, "--") or ""
    untracked = run_git(root, "ls-files", "--others", "--exclude-standard") or ""
    paths = {line.strip() for line in f"{tracked}\n{untracked}".splitlines() if line.strip()}
    return tuple(sorted(paths))


def active_change_ids(changed: tuple[str, ...], changes_root: str) -> list[str]:
    """Change identifiers whose record directory the diff touches."""

    prefix = f"{changes_root.rstrip('/')}/"
    identifiers: set[str] = set()
    for path in changed:
        if not path.startswith(prefix):
            continue
        head = path[len(prefix):].split("/", 1)[0]
        if head:
            identifiers.add(head)
    return sorted(identifiers)


def path_exists_at(root: Path, base: str, path: str) -> bool:
    return run_git(root, "cat-file", "-e", f"{base}:{path}") is not None


@contextlib.contextmanager
def base_snapshot(root: Path, base: str) -> Iterator[Path | None]:
    """Materialise the baseline tree in a temporary directory."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "archive", "--format=tar", base],
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        yield None
        return
    if completed.returncode != 0:
        yield None
        return
    with tempfile.TemporaryDirectory() as temporary:
        with tarfile.open(fileobj=io.BytesIO(completed.stdout)) as archive:
            try:
                archive.extractall(temporary, filter="data")
            except TypeError:  # pragma: no cover - Python without extraction filters
                archive.extractall(temporary)
        yield Path(temporary)


# ------------------------------------------------------------- shape reduction


def _safe_discover(root: Path, topology: Mapping[str, Any]) -> ObservedRepository | None:
    try:
        return discover_repository(root, topology)
    except (FileNotFoundError, NotADirectoryError, ValueError, SyntaxError):
        return None


def _ontology_shape(topology: Mapping[str, Any]) -> dict[str, Any]:
    facts = topology.get("governed_facts") or {}
    return {
        str(fact_id): {
            "subject": str(fact.get("subject") or ""),
            "relevant_lifecycle": str(fact.get("relevant_lifecycle") or ""),
        }
        for fact_id, fact in facts.items()
    }


def _semantics_shape(root: Path | None, topology: Mapping[str, Any]) -> dict[str, Any]:
    facts = topology.get("governed_facts") or {}
    shape: dict[str, Any] = {}
    for fact_id, fact in facts.items():
        owner = str(fact.get("semantic_owner") or "")
        document = owner.partition("#")[0]
        digest = "ABSENT"
        if root is not None and document:
            candidate = root / document
            if candidate.is_file():
                digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        shape[str(fact_id)] = {"owner": owner, "document_digest": digest}
    return shape


def _authority_shape(topology: Mapping[str, Any]) -> dict[str, Any]:
    facts = topology.get("governed_facts") or {}
    shape: dict[str, Any] = {}
    for fact_id, fact in facts.items():
        canonical = fact.get("canonical_authority") or {}
        historical = fact.get("historical_carrier")
        shape[str(fact_id)] = {
            "canonical": {
                "owner": str(canonical.get("owner") or ""),
                "classification": str(canonical.get("classification") or ""),
                "immutable": bool(canonical.get("immutable", False)),
                "carriers": sorted(str(item) for item in canonical.get("carriers", ())),
                "allowed_writers": sorted(
                    str(item) for item in canonical.get("allowed_writers", ())
                ),
            },
            "commit_boundary": str(canonical.get("commit_boundary") or ""),
            "historical_carrier": _historical_shape(historical),
        }
    return shape


def _historical_shape(historical: Any) -> Any:
    if not isinstance(historical, Mapping):
        return str(historical or "")
    return {
        "owner": str(historical.get("owner") or ""),
        "classification": str(historical.get("classification") or ""),
        "immutable": bool(historical.get("immutable", False)),
        "carriers": sorted(str(item) for item in historical.get("carriers", ())),
        "allowed_writers": sorted(str(item) for item in historical.get("allowed_writers", ())),
        "denied_decision_rights": sorted(
            str(item) for item in historical.get("denied_decision_rights", ())
        ),
    }


def _observed_writers(observed: ObservedRepository | None) -> set[str]:
    if observed is None:
        return set()
    return {f"{writer.symbol} -> {writer.carrier}" for writer in observed.writers}


def _client_surface(
    root: Path | None,
    observed: ObservedRepository | None,
    client_glob: str,
) -> set[str]:
    """Public symbols living behind the client boundary."""

    if observed is None or root is None or not client_glob:
        return set()
    surface: set[str] = set()
    for symbol in observed.python_symbols:
        module = ".".join(symbol.split(".")[:-1])
        relative = (Path("src") / Path(*module.split("."))).with_suffix(".py").as_posix()
        if path_matches(relative, client_glob):
            surface.add(symbol)
    return surface


# ------------------------------------------------------------- pathology flags


def dependency_findings(
    root: Path,
    rules: Mapping[str, Any],
    observed: ObservedRepository,
) -> dict[str, list[str]]:
    """Import and naming boundary violations, grouped by the flag they raise."""

    findings: dict[str, list[str]] = {
        "browser_owned_truth": [],
        "mutable_present_historical_dependency": [],
    }
    for rule in rules.get("forbidden_imports", ()):
        for path, imports in observed.imports.items():
            if not path_matches(path, str(rule["from_glob"])):
                continue
            for imported in imports:
                for forbidden in rule.get("modules", ()):
                    if imported == forbidden or imported.startswith(f"{forbidden}."):
                        findings["browser_owned_truth"].append(
                            f"forbidden authority import: {path} imports {imported}"
                        )

    client_rule = rules.get("forbidden_client_decision_names") or {}
    client_glob = str(client_rule.get("from_glob") or "")
    for symbol in _client_surface(root, observed, client_glob):
        name = symbol.rsplit(".", 1)[-1]
        if any(token in name for token in client_rule.get("contains", ())):
            findings["browser_owned_truth"].append(
                f"client-owned currentness decision surface: {symbol}"
            )

    for rule in rules.get("historical_read_boundaries", ()):
        for path, imports in observed.imports.items():
            if not path_matches(path, str(rule["from_glob"])):
                continue
            for forbidden in rule.get("forbidden_modules", ()):
                if forbidden in imports:
                    findings["mutable_present_historical_dependency"].append(
                        f"mutable-present historical dependency: {path} imports {forbidden}"
                    )
            required = {str(item) for item in rule.get("required_modules", ())}
            if required and not required.intersection(imports):
                findings["mutable_present_historical_dependency"].append(
                    f"historical owner missing: {path} must import one of {sorted(required)}"
                )
    for value in findings.values():
        value.sort()
    return findings


def measure_flags(
    root: Path,
    topology: Mapping[str, Any],
    rules: Mapping[str, Any],
    observed: ObservedRepository,
) -> dict[str, bool]:
    """Observe the four fail-closed pathologies directly, rather than asking."""

    canonical = canonical_carriers(topology)
    duplicate = any(len(facts) > 1 for facts in canonical.values())
    permitted = allowed_writers(topology)
    for writer in observed.writers:
        if writer.symbol not in permitted.get(writer.carrier, set()):
            duplicate = True

    legacy_locators = {
        entry["locator"]
        for entry in representation_index(topology).values()
        if entry["classification"] == "LEGACY_ONLY" and entry["locator"]
    }
    legacy_writes = any(writer.carrier in legacy_locators for writer in observed.writers)

    findings = dependency_findings(root, rules, observed)
    return {
        "duplicate_independent_writers": bool(duplicate),
        "legacy_successor_writes": bool(legacy_writes),
        "browser_owned_truth": bool(findings["browser_owned_truth"]),
        "mutable_present_historical_dependency": bool(
            findings["mutable_present_historical_dependency"]
        ),
    }


# ------------------------------------------------------------------- the delta


def measure_delta(
    root: Path,
    base: str,
    *,
    topology: Mapping[str, Any],
    rules: Mapping[str, Any],
    observed: ObservedRepository,
    change_id: str | None = None,
) -> dict[str, Any]:
    """Subtract the baseline repository from the working tree."""

    root = root.resolve()
    with base_snapshot(root, base) as snapshot:
        base_topology_path = None if snapshot is None else snapshot / TOPOLOGY_PATH
        if base_topology_path is not None and base_topology_path.is_file():
            base_topology: Mapping[str, Any] = load_yaml(base_topology_path)
            base_observed = _safe_discover(snapshot, base_topology)
        else:
            base_topology = {}
            base_observed = None
        client_glob = str(
            (rules.get("forbidden_client_decision_names") or {}).get("from_glob") or ""
        )
        base_shape = {
            "ontology": _ontology_shape(base_topology),
            "semantics": _semantics_shape(snapshot, base_topology),
            "authority": _authority_shape(base_topology),
            "representations": representation_index(base_topology),
            "writers": _observed_writers(base_observed),
            "client_surface": _client_surface(snapshot, base_observed, client_glob),
        }

    head_shape = {
        "ontology": _ontology_shape(topology),
        "semantics": _semantics_shape(root, topology),
        "authority": _authority_shape(topology),
        "representations": representation_index(topology),
        "writers": _observed_writers(observed),
        "client_surface": _client_surface(
            root,
            observed,
            str((rules.get("forbidden_client_decision_names") or {}).get("from_glob") or ""),
        ),
    }

    ontology_changed = base_shape["ontology"] != head_shape["ontology"]
    semantics_changed = base_shape["semantics"] != head_shape["semantics"]

    base_authority = base_shape["authority"]
    head_authority = head_shape["authority"]
    canonical_changed = False
    boundary_changed = False
    historical_changed = False
    touched: set[str] = set()
    for fact_id in set(base_authority) | set(head_authority):
        before = base_authority.get(fact_id, {})
        after = head_authority.get(fact_id, {})
        if before == after:
            continue
        touched.add(fact_id)
        if before.get("canonical") != after.get("canonical"):
            canonical_changed = True
        if before.get("commit_boundary") != after.get("commit_boundary"):
            boundary_changed = True
        if before.get("historical_carrier") != after.get("historical_carrier"):
            historical_changed = True

    base_reps = base_shape["representations"]
    head_reps = head_shape["representations"]
    added = [
        {
            "id": representation_id,
            "governed_fact": entry["governed_fact"],
            "classification": entry["classification"],
        }
        for representation_id, entry in sorted(head_reps.items())
        if representation_id not in base_reps
    ]
    removed = [
        {
            "id": representation_id,
            "governed_fact": entry["governed_fact"],
            "classification": entry["classification"],
        }
        for representation_id, entry in sorted(base_reps.items())
        if representation_id not in head_reps
    ]
    touched.update(entry["governed_fact"] for entry in added)
    touched.update(entry["governed_fact"] for entry in removed)

    rights_added: list[str] = []
    for representation_id, after in sorted(head_reps.items()):
        before = base_reps.get(representation_id)
        if before is None:
            continue
        if before["classification"] != after["classification"]:
            rights_added.append(
                f"{representation_id}: classification "
                f"{before['classification']} -> {after['classification']}"
            )
            touched.add(after["governed_fact"])
        regained = set(before["denied_decision_rights"]) - set(after["denied_decision_rights"])
        for right in sorted(regained):
            rights_added.append(f"{representation_id}: no longer denied {right}")
            touched.add(after["governed_fact"])
        gained_writers = set(after["writers"]) - set(before["writers"])
        for writer in sorted(gained_writers):
            rights_added.append(f"{representation_id}: declared writer {writer}")
            touched.add(after["governed_fact"])

    writers_added = sorted(head_shape["writers"] - base_shape["writers"])
    client_changed = base_shape["client_surface"] != head_shape["client_surface"]

    authority_changed = any(
        (
            canonical_changed,
            boundary_changed,
            historical_changed,
            client_changed,
            bool(writers_added),
            bool(rights_added),
        )
    )
    if authority_changed:
        status = "AUTHORITY_CHANGE"
    elif added or removed:
        status = "REPRESENTATION_CHANGE"
    else:
        status = "NO_CHANGE"

    measured = {
        "change_id": change_id,
        "measured_from": "repository-observation",
        "measured_between": {"base": base, "head": "working-tree"},
        "touched_facts": sorted(touched),
        "ontology": {"status": "CHANGE" if ontology_changed else "NO_CHANGE"},
        "semantics": {"status": "CHANGE" if semantics_changed else "NO_CHANGE"},
        "authority": {
            "status": status,
            "canonical_authority_changed": canonical_changed,
            "commit_boundary_changed": boundary_changed,
            "writers_added": writers_added,
            "decision_rights_added": rights_added,
            "historical_sources_changed": historical_changed,
            "client_responsibility_changed": client_changed,
            "representations_added": added,
            "representations_removed": removed,
        },
    }
    measured.update(measure_flags(root, topology, rules, observed))
    return measured


# --------------------------------------------------------------- comparison


def _normalise_authority(section: Mapping[str, Any]) -> dict[str, Any]:
    def _reps(key: str) -> list[dict[str, str]]:
        return sorted(
            (
                {
                    "id": str(item.get("id") or ""),
                    "governed_fact": str(item.get("governed_fact") or ""),
                    "classification": str(item.get("classification") or ""),
                }
                for item in section.get(key, ()) or ()
            ),
            key=lambda item: item["id"],
        )

    return {
        "status": str(section.get("status") or ""),
        "canonical_authority_changed": bool(section.get("canonical_authority_changed", False)),
        "commit_boundary_changed": bool(section.get("commit_boundary_changed", False)),
        "writers_added": sorted(str(item) for item in section.get("writers_added", ()) or ()),
        "decision_rights_added": sorted(
            str(item) for item in section.get("decision_rights_added", ()) or ()
        ),
        "historical_sources_changed": bool(section.get("historical_sources_changed", False)),
        "client_responsibility_changed": bool(
            section.get("client_responsibility_changed", False)
        ),
        "representations_added": _reps("representations_added"),
        "representations_removed": _reps("representations_removed"),
    }


def compare_measured(
    expected: Mapping[str, Any],
    measured: Mapping[str, Any],
    *,
    label: str = "the authorization",
) -> list[str]:
    """Compare a declared delta against the observed repository."""

    authorized = expected
    errors: list[str] = []
    for section in ("ontology", "semantics"):
        declared = str((authorized.get(section) or {}).get("status") or "")
        actual = str((measured.get(section) or {}).get("status") or "")
        if declared != actual:
            errors.append(
                f"measured {section} does not match {label}: "
                f"declared {declared or 'MISSING'}, measured {actual}"
            )

    expected_authority = _normalise_authority(authorized.get("authority") or {})
    actual_authority = _normalise_authority(measured.get("authority") or {})
    for key, actual_value in actual_authority.items():
        expected_value = expected_authority.get(key)
        if expected_value != actual_value:
            errors.append(
                f"measured authority.{key} does not match {label}: "
                f"declared {expected_value!r}, measured {actual_value!r}"
            )

    authorized_facts = {str(item) for item in authorized.get("touched_facts", ()) or ()}
    for fact_id in measured.get("touched_facts", ()) or ():
        if str(fact_id) not in authorized_facts:
            errors.append(
                f"measured change to a governed fact not declared in {label}: {fact_id}"
            )

    for flag in COMPARED_FLAGS:
        if bool(measured.get(flag)) is not bool(authorized.get(flag)):
            errors.append(
                f"measured {flag} does not match {label}: "
                f"declared {authorized.get(flag)!r}, measured {measured.get(flag)!r}"
            )
    return errors


def write_measured(root: Path, measured: Mapping[str, Any]) -> Path:
    target = root / MEASURED_OUTPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump(dict(measured), sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return target


def load_gate_rules(root: Path) -> dict[str, Any]:
    return load_yaml(root / GATE_RULES_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure the actual Constitutional Delta from repository observation"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base", type=str, default=None)
    parser.add_argument("--change-id", type=str, default=None)
    parser.add_argument(
        "--record",
        action="store_true",
        help="write the measurement into the active change record as the Verify output",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    base = resolve_base_ref(root, args.base)
    if base is None:
        print("NO BASELINE: measurement requires a git baseline")
        raise SystemExit(2)

    topology = load_yaml(root / TOPOLOGY_PATH)
    rules = load_yaml(root / "constitutional/dependency_rules.yaml")
    gate_rules = load_gate_rules(root)
    changes_root = str(gate_rules.get("changes_root") or "docs/work/changes")

    change_id = args.change_id
    if change_id is None:
        candidates = active_change_ids(changed_paths(root, base), changes_root)
        change_id = candidates[0] if len(candidates) == 1 else None

    observed = discover_repository(root, topology)
    measured = measure_delta(
        root,
        base,
        topology=topology,
        rules=rules,
        observed=observed,
        change_id=change_id,
    )
    target = write_measured(root, measured)
    print(f"Measured against {base[:12]}")
    print(target)

    if args.record:
        if change_id is None:
            print("NO ACTIVE CHANGE: pass --change-id to record a Verify result")
            raise SystemExit(2)
        record = root / changes_root / change_id / "actual-constitutional-delta.yaml"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            yaml.safe_dump(dict(measured), sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        print(record)


if __name__ == "__main__":
    main()
