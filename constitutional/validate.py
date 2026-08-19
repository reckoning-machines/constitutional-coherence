from __future__ import annotations

import argparse
import ast
from fnmatch import fnmatch
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from constitutional.discover import (
    TOPOLOGY_PATH,
    ObservedRepository,
    discover_repository,
    load_yaml,
    write_observed,
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


def _declared_carriers(topology: Mapping[str, Any]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for fact_id, fact in (topology.get("governed_facts") or {}).items():
        canonical = fact.get("canonical_authority") or {}
        for locator in canonical.get("carriers", ()):
            owners.setdefault(str(locator), set()).add(str(fact_id))
        historical = fact.get("historical_carrier")
        if isinstance(historical, Mapping):
            for locator in historical.get("carriers", ()):
                owners.setdefault(str(locator), set()).add(str(fact_id))
        for representation in fact.get("representations", ()):
            locator = str(representation.get("locator") or "")
            if locator.startswith(("sqlite.", "json_file.")):
                owners.setdefault(locator, set()).add(str(fact_id))
    return owners


def _allowed_writers(topology: Mapping[str, Any]) -> dict[str, set[str]]:
    allowed: dict[str, set[str]] = {}
    for fact in (topology.get("governed_facts") or {}).values():
        canonical = fact.get("canonical_authority") or {}
        writers = {str(item) for item in canonical.get("allowed_writers", ())}
        for locator in canonical.get("carriers", ()):
            allowed.setdefault(str(locator), set()).update(writers)
        historical = fact.get("historical_carrier")
        if isinstance(historical, Mapping):
            historical_writers = {
                str(item) for item in historical.get("allowed_writers", writers)
            }
            for locator in historical.get("carriers", ()):
                allowed.setdefault(str(locator), set()).update(historical_writers)
        for representation in fact.get("representations", ()):
            locator = str(representation.get("locator") or "")
            if locator.startswith(("sqlite.", "json_file.")):
                allowed.setdefault(locator, set()).update(
                    str(item) for item in representation.get("writers", ())
                )
    return allowed


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

    declared = _declared_carriers(topology)
    allowed = _allowed_writers(topology)
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


def _matches_path(path: str, pattern: str) -> bool:
    if fnmatch(path, pattern):
        return True
    return fnmatch(path, pattern.replace("**/", ""))


def validate_dependencies(
    root: Path,
    rules: Mapping[str, Any],
    observed: ObservedRepository,
) -> list[str]:
    errors: list[str] = []
    for rule in rules.get("forbidden_imports", ()):
        for path, imports in observed.imports.items():
            if not _matches_path(path, str(rule["from_glob"])):
                continue
            for imported in imports:
                for forbidden in rule.get("modules", ()):
                    if imported == forbidden or imported.startswith(f"{forbidden}."):
                        errors.append(
                            f"forbidden authority import: {path} imports {imported}"
                        )

    client_rule = rules.get("forbidden_client_decision_names") or {}
    client_glob = str(client_rule.get("from_glob") or "")
    for symbol in observed.python_symbols:
        module = ".".join(symbol.split(".")[:-1])
        path = _source_for_module(root, module)
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if client_glob and _matches_path(relative, client_glob):
            name = symbol.rsplit(".", 1)[-1]
            if any(token in name for token in client_rule.get("contains", ())):
                errors.append(f"client-owned currentness decision surface: {symbol}")

    for rule in rules.get("historical_read_boundaries", ()):
        for path, imports in observed.imports.items():
            if not _matches_path(path, str(rule["from_glob"])):
                continue
            for forbidden in rule.get("forbidden_modules", ()):
                if forbidden in imports:
                    errors.append(
                        f"mutable-present historical dependency: {path} imports {forbidden}"
                    )
            required = set(str(item) for item in rule.get("required_modules", ()))
            if required and not required.intersection(imports):
                errors.append(
                    f"historical owner missing: {path} must import one of {sorted(required)}"
                )
    return errors


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


def validate_repository(
    root: Path,
    *,
    delta_path: Path = DEFAULT_DELTA,
    actual_delta_path: Path = DEFAULT_ACTUAL_DELTA,
) -> list[str]:
    root = root.resolve()
    topology = load_yaml(root / TOPOLOGY_PATH)
    observed = discover_repository(root, topology)
    write_observed(root, observed)
    rules = load_yaml(root / "constitutional/dependency_rules.yaml")
    delta = load_yaml(root / delta_path)
    actual_delta = load_yaml(root / actual_delta_path)
    return [
        *validate_topology(root, topology, observed),
        *validate_dependencies(root, rules, observed),
        *validate_delta(root, topology, delta),
        *validate_actual_delta(delta, actual_delta),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Constitutional Coherence")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--delta", type=Path, default=DEFAULT_DELTA)
    parser.add_argument("--actual-delta", type=Path, default=DEFAULT_ACTUAL_DELTA)
    args = parser.parse_args()
    errors = validate_repository(
        args.root,
        delta_path=args.delta,
        actual_delta_path=args.actual_delta,
    )
    if errors:
        print("CONSTITUTIONAL FAILURE")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("CONSTITUTIONAL COHERENCE VALIDATED")


if __name__ == "__main__":
    main()
