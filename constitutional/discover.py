from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml


TOPOLOGY_PATH = Path("docs/constitution/authority-topology.yaml")


@dataclass(frozen=True, slots=True)
class ObservedCarrier:
    locator: str
    kind: str
    source: str


@dataclass(frozen=True, slots=True)
class ObservedWriter:
    carrier: str
    symbol: str
    source: str


@dataclass(frozen=True, slots=True)
class ObservedRepository:
    durable_carriers: tuple[ObservedCarrier, ...]
    writers: tuple[ObservedWriter, ...]
    python_symbols: tuple[str, ...]
    imports: Mapping[str, tuple[str, ...]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "durable_carriers": [asdict(item) for item in self.durable_carriers],
            "writers": [asdict(item) for item in self.writers],
            "python_symbols": list(self.python_symbols),
            "imports": {key: list(value) for key, value in self.imports.items()},
        }


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return value


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _schema_columns(path: Path) -> Iterable[ObservedCarrier]:
    text = path.read_text(encoding="utf-8")
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<table>[A-Za-z_]\w*)\s*"
        r"\((?P<body>.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    for match in table_pattern.finditer(text):
        table = match.group("table")
        body = match.group("body")
        body_start = match.start("body")
        for column_match in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s+([^,\n]+)", body):
            column = column_match.group(1)
            if column.upper() in {
                "PRIMARY",
                "FOREIGN",
                "UNIQUE",
                "CHECK",
                "CONSTRAINT",
            }:
                continue
            yield ObservedCarrier(
                locator=f"sqlite.{table}.{column}",
                kind="sqlite_column",
                source=f"{path.as_posix()}:{_line_number(text, body_start + column_match.start())}",
            )


def _matches_any(value: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch(value, pattern) for pattern in patterns)


def _module_for(root: Path, source: Path) -> str:
    relative = source.relative_to(root / "src")
    return ".".join(relative.with_suffix("").parts)


class _PythonInventory(ast.NodeVisitor):
    def __init__(self, module: str, source_path: Path, source_text: str) -> None:
        self.module = module
        self.source_path = source_path
        self.source_text = source_text
        self.scope: list[str] = []
        self.symbols: list[str] = []
        self.functions: list[tuple[str, ast.AST]] = []
        self.imports: set[str] = set()

    def _symbol(self, name: str) -> str:
        return ".".join([self.module, *self.scope, name])

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(self._symbol(node.name))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        symbol = self._symbol(node.name)
        self.symbols.append(symbol)
        self.functions.append((symbol, node))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.add(f"{module}.{alias.name}".strip("."))


def _string_constants(node: ast.AST) -> tuple[str, ...]:
    return tuple(
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    )


def _is_sql_write(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(token in normalized for token in ("insert into ", "update ", "delete from "))


def _sql_mentions_carrier(text: str, locator: str) -> bool:
    _dialect, table, column = locator.split(".", 2)
    normalized = " ".join(text.lower().split())
    return table.lower() in normalized and column.lower() in normalized


def _json_file_name(constants: Iterable[str]) -> str | None:
    for value in constants:
        match = re.search(r"([A-Za-z0-9_.-]+\.json)", value)
        if match:
            return match.group(1)
    return None


def _source_inventory(
    root: Path,
    source_roots: Iterable[str],
    durable_patterns: Iterable[str],
) -> tuple[list[_PythonInventory], list[ObservedCarrier], list[ObservedWriter]]:
    inventories: list[_PythonInventory] = []
    json_carriers: list[ObservedCarrier] = []
    json_writers: list[ObservedWriter] = []
    for source_root in source_roots:
        for path in sorted((root / source_root).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            inventory = _PythonInventory(_module_for(root, path), path, text)
            inventory.visit(ast.parse(text, filename=str(path)))
            inventories.append(inventory)
            for symbol, function in inventory.functions:
                constants = _string_constants(function)
                joined = "\n".join(constants)
                if ".json" not in joined or not (
                    "write_text" in ast.unparse(function) or "json.dump" in ast.unparse(function)
                ):
                    continue
                file_name = _json_file_name(constants)
                if file_name is None:
                    continue
                for value in constants:
                    if _matches_any(value, durable_patterns):
                        locator = f"json_file.{file_name}.{value}"
                        json_carriers.append(
                            ObservedCarrier(locator, "json_field", path.relative_to(root).as_posix())
                        )
                        json_writers.append(
                            ObservedWriter(locator, symbol, path.relative_to(root).as_posix())
                        )
    return inventories, json_carriers, json_writers


def discover_repository(root: Path, topology: Mapping[str, Any]) -> ObservedRepository:
    root = root.resolve()
    discovery = topology.get("discovery") or {}
    patterns = tuple(str(item) for item in discovery.get("durable_column_patterns", ()))
    all_schema_columns: list[ObservedCarrier] = []
    for relative in discovery.get("schema_files", ()):
        all_schema_columns.extend(_schema_columns(root / str(relative)))
    candidates = [
        item
        for item in all_schema_columns
        if _matches_any(item.locator.rsplit(".", 1)[-1], patterns)
    ]

    inventories, json_carriers, json_writers = _source_inventory(
        root,
        tuple(str(item) for item in discovery.get("source_roots", ("src",))),
        patterns,
    )
    candidates.extend(json_carriers)

    writers: list[ObservedWriter] = list(json_writers)
    for carrier in candidates:
        if not carrier.locator.startswith("sqlite."):
            continue
        for inventory in inventories:
            for symbol, function in inventory.functions:
                for value in _string_constants(function):
                    if _is_sql_write(value) and _sql_mentions_carrier(value, carrier.locator):
                        writers.append(
                            ObservedWriter(
                                carrier.locator,
                                symbol,
                                inventory.source_path.relative_to(root).as_posix(),
                            )
                        )
                        break

    imports = {
        inventory.source_path.relative_to(root).as_posix(): tuple(sorted(inventory.imports))
        for inventory in inventories
    }
    symbols = tuple(sorted({symbol for item in inventories for symbol in item.symbols}))
    return ObservedRepository(
        tuple(sorted(set(candidates), key=lambda item: item.locator)),
        tuple(sorted(set(writers), key=lambda item: (item.carrier, item.symbol))),
        symbols,
        imports,
    )


def write_observed(root: Path, observed: ObservedRepository) -> Path:
    target = root / "build/constitutional/observed-authority.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(observed.to_dict(), indent=2, sort_keys=True) + "\n")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe authority-bearing repository shapes")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    topology = load_yaml(root / TOPOLOGY_PATH)
    observed = discover_repository(root, topology)
    target = args.output or write_observed(root, observed)
    if args.output:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(observed.to_dict(), indent=2, sort_keys=True) + "\n")
    print(f"Observed {len(observed.durable_carriers)} candidate durable carriers")
    print(f"Observed {len(observed.writers)} candidate writers")
    print(target)


if __name__ == "__main__":
    main()
