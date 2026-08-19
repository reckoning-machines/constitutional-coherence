from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any, Mapping

from constitutional.discover import (
    TOPOLOGY_PATH,
    ObservedRepository,
    SchemaDiscoveryError,
    allowed_writers,
    declared_carriers,
    discover_repository,
    load_yaml,
    path_matches,
    write_observed,
)
from constitutional.measure import (
    active_change_ids,
    changed_paths,
    compare_measured,
    dependency_findings,
    load_gate_rules,
    measure_delta,
    path_exists_at,
    resolve_base_ref,
    write_measured,
)


CLASSIFICATIONS = (
    "AUTHORITATIVE",
    "DERIVED",
    "CACHE",
    "RECEIPT",
    "LEGACY_ONLY",
    "EPHEMERAL",
)
DEFAULT_DELTA = Path(
    "docs/work/changes/CHANGE-042/constitutional-delta.yaml"
)
DEFAULT_ACTUAL_DELTA = Path(
    "docs/work/changes/CHANGE-042/actual-constitutional-delta.yaml"
)


class ConstitutionalViolation(RuntimeError):
    pass


def _markdown_anchor_exists(path: Path, anchor: str) -> bool:
    headings = re.findall(r"(?m)^#+\s+(.+?)\s*$", path.read_text(encoding="utf-8"))
    anchors = {
        re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
        for heading in headings
    }
    return anchor in anchors


def _source_for_module(root: Path, module: str) -> Path:
    return root / "src" / Path(*module.split(".")).with_suffix(".py")


def _symbol_exists(root: Path, symbol: str, observed: ObservedRepository) -> bool:
    return symbol in observed.python_symbols


def _schema_texts(root: Path, topology: Mapping[str, Any]) -> str:
    return "\n".join(
        (root / str(path)).read_text(encoding="utf-8")
        for path in (topology.get("discovery") or {}).get("schema_files", ())
    ).lower()


def validate_topology(
    root: Path,
    topology: Mapping[str, Any],
    observed: ObservedRepository,
) -> list[str]:
    errors: list[str] = []
    if topology.get("schema_version") != 1:
        errors.append("authority topology schema_version must be 1")
    if tuple(topology.get("classifications") or ()) != CLASSIFICATIONS:
        errors.append("authority topology must define exactly the six constitutional classes")

    facts = topology.get("governed_facts") or {}
    if not isinstance(facts, Mapping) or not facts:
        errors.append("authority topology has no governed facts")
        return errors

    declared = declared_carriers(topology)
    allowed = allowed_writers(topology)
    for carrier in observed.durable_carriers:
        if carrier.locator not in declared:
            errors.append(
                f"unclassified durable carrier: {carrier.locator} ({carrier.source})"
            )
    for writer in observed.writers:
        permitted = allowed.get(writer.carrier, set())
        if writer.symbol not in permitted:
            errors.append(
                "unauthorized writer: "
                f"{writer.symbol} -> {writer.carrier} ({writer.source})"
            )

    schema_text = _schema_texts(root, topology)
    representation_ids: set[str] = set()
    for fact_id, fact in facts.items():
        owner = str(fact.get("semantic_owner") or "")
        owner_path, _, anchor = owner.partition("#")
        semantic_path = root / owner_path
        if not semantic_path.is_file():
            errors.append(f"{fact_id}: semantic owner does not exist: {owner_path}")
        elif anchor and not _markdown_anchor_exists(semantic_path, anchor):
            errors.append(f"{fact_id}: semantic owner anchor does not exist: {anchor}")

        canonical = fact.get("canonical_authority") or {}
        if canonical.get("classification") != "AUTHORITATIVE":
            errors.append(f"{fact_id}: canonical authority must be AUTHORITATIVE")
        boundary = str(canonical.get("commit_boundary") or "")
        if not _symbol_exists(root, boundary, observed):
            errors.append(f"{fact_id}: commit boundary symbol is missing: {boundary}")
        for writer in canonical.get("allowed_writers", ()):
            if not _symbol_exists(root, str(writer), observed):
                errors.append(f"{fact_id}: allowed writer symbol is missing: {writer}")

        if canonical.get("immutable"):
            tables = {
                str(locator).split(".")[1]
                for locator in canonical.get("carriers", ())
                if str(locator).startswith("sqlite.")
            }
            for table in tables:
                if f"before update on {table}" not in schema_text:
                    errors.append(f"{fact_id}: immutable carrier permits UPDATE: {table}")
                if f"before delete on {table}" not in schema_text:
                    errors.append(f"{fact_id}: immutable carrier permits DELETE: {table}")

        historical = fact.get("historical_carrier")
        if isinstance(historical, Mapping) and historical.get("immutable"):
            tables = {
                str(locator).split(".")[1]
                for locator in historical.get("carriers", ())
                if str(locator).startswith("sqlite.")
            }
            for table in tables:
                if f"before update on {table}" not in schema_text:
                    errors.append(f"{fact_id}: historical receipt permits UPDATE: {table}")
                if f"before delete on {table}" not in schema_text:
                    errors.append(f"{fact_id}: historical receipt permits DELETE: {table}")

        for representation in fact.get("representations", ()):
            representation_id = str(representation.get("id") or "")
            if not representation_id or representation_id in representation_ids:
                errors.append(f"{fact_id}: representation IDs must be nonempty and unique")
            representation_ids.add(representation_id)
            classification = representation.get("classification")
            if classification not in CLASSIFICATIONS or classification == "AUTHORITATIVE":
                errors.append(
                    f"{fact_id}/{representation_id}: invalid subordinate classification"
                )
            denied = representation.get("denied_decision_rights")
            if not isinstance(denied, list) or not denied:
                errors.append(
                    f"{fact_id}/{representation_id}: denied decision rights are required"
                )
            if classification == "DERIVED" and not representation.get("rebuildable_from"):
                errors.append(f"{fact_id}/{representation_id}: DERIVED must be rebuildable")
            if classification == "RECEIPT" and not representation.get("immutable"):
                errors.append(f"{fact_id}/{representation_id}: RECEIPT must be immutable")
            locator = str(representation.get("locator") or "")
            if locator and not locator.startswith(("sqlite.", "json_file.")):
                if not _symbol_exists(root, locator, observed):
                    errors.append(
                        f"{fact_id}/{representation_id}: locator symbol is missing: {locator}"
                    )
    return errors


def validate_dependencies(
    root: Path,
    rules: Mapping[str, Any],
    observed: ObservedRepository,
) -> list[str]:
    """Import and naming boundaries, reported as flat constitutional errors."""

    findings = dependency_findings(root, rules, observed)
    return [error for group in findings.values() for error in group]


def validate_delta(
    root: Path,
    topology: Mapping[str, Any],
    delta: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    authority_file = root / str(delta.get("authorized_by") or "")
    if not authority_file.is_file():
        errors.append("Constitutional Delta lacks an existing legitimate authority record")
    facts = topology.get("governed_facts") or {}
    for fact_id in delta.get("touched_facts", ()):
        if fact_id not in facts:
            errors.append(f"Constitutional Delta touches unknown fact: {fact_id}")
    if (delta.get("ontology") or {}).get("status") not in {"NO_CHANGE", "CHANGE"}:
        errors.append("Constitutional Delta must declare ontology status")
    if (delta.get("semantics") or {}).get("status") not in {"NO_CHANGE", "CHANGE"}:
        errors.append("Constitutional Delta must declare semantics status")

    authority = delta.get("authority") or {}
    declared_representations = {
        (str(fact_id), str(rep.get("id"))): str(rep.get("classification"))
        for fact_id, fact in facts.items()
        for rep in fact.get("representations", ())
    }
    for representation in authority.get("representations_added", ()):
        key = (
            str(representation.get("governed_fact") or ""),
            str(representation.get("id") or ""),
        )
        expected = declared_representations.get(key)
        if expected is None:
            errors.append(f"Delta representation is absent from topology: {key[1]}")
        elif expected != representation.get("classification"):
            errors.append(f"Delta representation classification disagrees: {key[1]}")
    for field in (
        "duplicate_independent_writers",
        "legacy_successor_writes",
        "browser_owned_truth",
        "mutable_present_historical_dependency",
    ):
        if delta.get(field) is not False:
            errors.append(f"Constitutional Delta fails closed: {field} must be false")
    return errors


def validate_actual_delta(
    authorized: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if actual.get("change_id") != authorized.get("change_id"):
        errors.append("Actual Constitutional Delta belongs to a different change")
    for section in ("ontology", "semantics", "authority"):
        if actual.get(section) != authorized.get(section):
            errors.append(
                f"Actual Constitutional Delta does not match authorization: {section}"
            )
    for field in (
        "duplicate_independent_writers",
        "legacy_successor_writes",
        "browser_owned_truth",
        "mutable_present_historical_dependency",
    ):
        if actual.get(field) != authorized.get(field):
            errors.append(
                f"Actual Constitutional Delta does not match authorization: {field}"
            )
    return errors


def validate_gate(
    root: Path,
    topology: Mapping[str, Any],
    observed: ObservedRepository,
    rules: Mapping[str, Any],
    *,
    base: str | None = None,
    require_gate: bool = False,
) -> list[str]:
    """Gate the working tree against the change record that authorizes it.

    The gate selects the Constitutional Delta from the diff rather than from a
    constant, refuses a delta legitimised by a decision record that the same
    change created or edited, and compares the authorized forecast against a
    delta measured from the repository itself.
    """

    root = root.resolve()
    base_ref = resolve_base_ref(root, base)
    if base_ref is None:
        if require_gate:
            return [
                "constitutional gate unavailable: no git baseline to measure against"
            ]
        return []

    gate_rules_path = root / "constitutional/gate_rules.yaml"
    if not gate_rules_path.is_file():
        return ["constitutional gate rules are missing: constitutional/gate_rules.yaml"]
    gate_rules = load_gate_rules(root)

    changed = changed_paths(root, base_ref)
    governed_globs = [str(item) for item in gate_rules.get("governed_paths", ())]
    governed = [
        path
        for path in changed
        if any(path_matches(path, glob) for glob in governed_globs)
    ]
    if not governed:
        return []

    errors: list[str] = []
    changes_root = str(gate_rules.get("changes_root") or "docs/work/changes")
    change_ids = active_change_ids(changed, changes_root)
    if not change_ids:
        return [
            "governed change without a Constitutional Delta: "
            + ", ".join(governed)
        ]
    if len(change_ids) > 1:
        return [
            "ambiguous active change: governed work touches "
            + ", ".join(change_ids)
        ]

    change_id = change_ids[0]
    change_dir = Path(changes_root) / change_id
    delta_path = root / change_dir / "constitutional-delta.yaml"
    if not delta_path.is_file():
        return [
            f"{change_id}: governed change has no "
            f"{(change_dir / 'constitutional-delta.yaml').as_posix()}"
        ]
    delta = load_yaml(delta_path)
    record_status = str(delta.get("status") or "OPEN").upper()
    if record_status == "COMPLETED":
        return [
            f"governed work attributed to a completed change record: {change_id}. "
            "A merged change cannot be re-authorized; open a new change."
        ]
    if record_status != "OPEN":
        return [f"{change_id}: change record status must be OPEN or COMPLETED"]
    errors.extend(f"{change_id}: {error}" for error in validate_delta(root, topology, delta))

    authorized_by = str(delta.get("authorized_by") or "")
    if authorized_by:
        if authorized_by in changed:
            errors.append(
                f"{change_id}: the authorizing decision record was written or edited by "
                f"the change it authorizes: {authorized_by}"
            )
        elif not path_exists_at(root, base_ref, authorized_by):
            errors.append(
                f"{change_id}: the authorizing decision record did not exist before the "
                f"change: {authorized_by}"
            )

    for rule in gate_rules.get("declaration_required", ()):
        globs = [str(item) for item in rule.get("paths", ())]
        touched = [
            path for path in changed if any(path_matches(path, glob) for glob in globs)
        ]
        if not touched:
            continue
        section = str(rule.get("section") or "")
        status = str((delta.get(section) or {}).get("status") or "")
        unlawful = status in {"", "NO_CHANGE"} if section == "authority" else status != "CHANGE"
        if unlawful:
            errors.append(
                f"{change_id}: {touched[0]} changed, but the Constitutional Delta "
                f"declares {section} status {status or 'MISSING'}"
            )

    measured = measure_delta(
        root,
        base_ref,
        topology=topology,
        rules=rules,
        observed=observed,
        change_id=change_id,
    )
    write_measured(root, measured)
    errors.extend(
        f"{change_id}: {error}" for error in compare_measured(delta, measured)
    )

    actual_path = root / change_dir / "actual-constitutional-delta.yaml"
    if not actual_path.is_file():
        errors.append(
            f"{change_id}: Verify record is missing: "
            f"{(change_dir / 'actual-constitutional-delta.yaml').as_posix()}"
        )
    else:
        actual = load_yaml(actual_path)
        errors.extend(
            f"{change_id}: {error}"
            for error in compare_measured(
                actual, measured, label="the recorded Verify record"
            )
        )
        errors.extend(
            f"{change_id}: {error}" for error in validate_actual_delta(delta, actual)
        )
    return errors


def validate_repository(
    root: Path,
    *,
    delta_path: Path = DEFAULT_DELTA,
    actual_delta_path: Path = DEFAULT_ACTUAL_DELTA,
    base: str | None = None,
    require_gate: bool = False,
) -> list[str]:
    """Validate standing repository shape, retained change records, and the gate.

    Standing validation answers "is the repository coherent right now". The gate
    answers "was this particular change authorized", which needs a baseline and
    therefore needs git.
    """

    root = root.resolve()
    topology = load_yaml(root / TOPOLOGY_PATH)
    try:
        observed = discover_repository(root, topology)
    except SchemaDiscoveryError as error:
        return [f"schema discovery refused: {error}"]
    write_observed(root, observed)
    rules = load_yaml(root / "constitutional/dependency_rules.yaml")
    errors = [
        *validate_topology(root, topology, observed),
        *validate_dependencies(root, rules, observed),
    ]
    if (root / delta_path).is_file() and (root / actual_delta_path).is_file():
        retained = load_yaml(root / delta_path)
        retained_actual = load_yaml(root / actual_delta_path)
        errors.extend(validate_delta(root, topology, retained))
        errors.extend(validate_actual_delta(retained, retained_actual))
    errors.extend(
        validate_gate(
            root,
            topology,
            observed,
            rules,
            base=base,
            require_gate=require_gate,
        )
    )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Constitutional Coherence")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--delta", type=Path, default=DEFAULT_DELTA)
    parser.add_argument("--actual-delta", type=Path, default=DEFAULT_ACTUAL_DELTA)
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="git ref the working tree is measured against",
    )
    parser.add_argument(
        "--require-gate",
        action="store_true",
        help="fail when no git baseline is available instead of skipping the gate",
    )
    args = parser.parse_args()
    errors = validate_repository(
        args.root,
        delta_path=args.delta,
        actual_delta_path=args.actual_delta,
        base=args.base,
        require_gate=args.require_gate,
    )
    if errors:
        print("CONSTITUTIONAL FAILURE")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("CONSTITUTIONAL COHERENCE VALIDATED")


if __name__ == "__main__":
    main()
