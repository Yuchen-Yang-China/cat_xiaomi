#!/usr/bin/env python3
"""Run lightweight, dependency-free checks for the public cat archive."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.dont_write_bytecode = True
import build_dashboard


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
PUBLIC_TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".csv", ".py", ".html"}
PRIVATE_PATH_PATTERNS = ("/" + "Users/", "file" + "://")


def repository_files(suffixes: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if suffixes is None or path.suffix.lower() in suffixes:
            files.append(path)
    return sorted(files)


def check_markdown_links() -> tuple[list[str], int]:
    errors: list[str] = []
    files = repository_files({".md"})
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            href = match.group(1).strip().strip("<>")
            href = href.split("#", 1)[0]
            if not href or href.startswith(("http://", "https://", "mailto:")):
                continue
            target = (path.parent / unquote(href)).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"{path.relative_to(ROOT)} links outside repository: {href}"
                )
                continue
            if not target.exists():
                errors.append(f"{path.relative_to(ROOT)} has broken link: {href}")
    return errors, len(files)


def check_csv_files() -> tuple[list[str], int]:
    errors: list[str] = []
    files = repository_files({".csv"})
    for path in files:
        try:
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    errors.append(f"{path.relative_to(ROOT)} has no CSV header")
                    continue
                for row_number, row in enumerate(reader, start=2):
                    if None in row:
                        errors.append(
                            f"{path.relative_to(ROOT)} row {row_number} has extra columns"
                        )
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)} is not valid UTF-8 CSV: {exc}")
    return errors, len(files)


def check_public_paths() -> tuple[list[str], int]:
    errors: list[str] = []
    files = repository_files(PUBLIC_TEXT_SUFFIXES)
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in PRIVATE_PATH_PATTERNS:
            if pattern in text:
                errors.append(
                    f"{path.relative_to(ROOT)} contains public-hostile path pattern {pattern}"
                )
    return errors, len(files)


def check_dashboard() -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(build_dashboard.DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Unable to read dashboard data: {exc}"]

    errors.extend(build_dashboard.validate(data))
    expected = build_dashboard.render(data)
    if not build_dashboard.OUTPUT_PATH.exists():
        errors.append("dashboard.html is missing")
    elif build_dashboard.OUTPUT_PATH.read_text(encoding="utf-8") != expected:
        errors.append("dashboard.html is out of date; run python3 scripts/build_dashboard.py")

    lowered = expected.lower()
    forbidden_network_features = ("<script src=", "fetch(", "xmlhttprequest", "websocket(")
    for feature in forbidden_network_features:
        if feature in lowered:
            errors.append(f"dashboard.html contains offline-incompatible feature: {feature}")
    return errors


def main() -> int:
    results: list[tuple[str, list[str], int | None]] = []
    link_errors, markdown_count = check_markdown_links()
    results.append(("Markdown links", link_errors, markdown_count))
    csv_errors, csv_count = check_csv_files()
    results.append(("CSV files", csv_errors, csv_count))
    path_errors, text_count = check_public_paths()
    results.append(("Public path scan", path_errors, text_count))
    results.append(("Dashboard data/build", check_dashboard(), None))

    errors: list[str] = []
    for label, group_errors, count in results:
        if group_errors:
            print(f"FAIL {label}")
            for error in group_errors:
                print(f"  - {error}")
            errors.extend(group_errors)
        else:
            suffix = f" ({count} files)" if count is not None else ""
            print(f"PASS {label}{suffix}")

    if errors:
        print(f"\n{len(errors)} check(s) failed.", file=sys.stderr)
        return 1
    print("\nRepository checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
