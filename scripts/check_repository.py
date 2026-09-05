#!/usr/bin/env python3
"""Run lightweight, dependency-free checks for the public cat archive."""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

sys.dont_write_bytecode = True
import build_dashboard


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
PUBLIC_TEXT_SUFFIXES = {
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".csv",
    ".py",
    ".html",
    ".svg",
}
PRIVATE_PATH_PATTERNS = ("/" + "Users/", "file" + "://")
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
CN_MOBILE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
WECHAT_ID_PATTERN = re.compile(r"\bwx" + r"id_[A-Za-z0-9_-]+\b", re.IGNORECASE)
DATE_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})(?:\s|$)", re.MULTILINE)
ACTION_ID = re.compile(r"^\|\s*(A-\d{4}-\d{2}-\d{2})\s*\|", re.MULTILINE)


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
        for label, pattern in (
            ("email address", EMAIL_PATTERN),
            ("possible Chinese mobile number", CN_MOBILE_PATTERN),
            ("WeChat id", WECHAT_ID_PATTERN),
        ):
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)} contains {label}")
    return errors, len(files)


def check_manifest() -> list[str]:
    """Check the manifest fields used by repository tooling without YAML deps."""
    errors: list[str] = []
    path = ROOT / "project_manifest.yml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Unable to read project_manifest.yml: {exc}"]

    schema_match = re.search(r"^schema_version:\s*(\d+)\s*$", text, re.MULTILINE)
    if not schema_match or int(schema_match.group(1)) != 2:
        errors.append("project_manifest.yml schema_version must be 2")

    reviewed_match = re.search(
        r"^\s*last_reviewed:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE
    )
    if not reviewed_match:
        errors.append("project_manifest.yml needs an ISO last_reviewed date")
    else:
        try:
            reviewed = date.fromisoformat(reviewed_match.group(1))
            if reviewed > date.today():
                errors.append("project_manifest.yml last_reviewed cannot be in the future")
        except ValueError:
            errors.append("project_manifest.yml last_reviewed is not a valid date")

    required_paths = (
        "AGENTS.md",
        "INDEX.md",
        "01_profile/cat_profile.md",
        "01_profile/baseline.md",
        "08_questions_decisions/action_queue.md",
        "11_insights/data/current_snapshot.json",
        "dashboard.html",
    )
    for required in required_paths:
        if not (ROOT / required).exists():
            errors.append(f"Manifest-required path is missing: {required}")
    return errors


def check_action_queue() -> list[str]:
    errors: list[str] = []
    path = ROOT / "08_questions_decisions/action_queue.md"
    text = path.read_text(encoding="utf-8")
    ids = ACTION_ID.findall(text)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    for item in duplicates:
        errors.append(f"Duplicate action id in action_queue.md: {item}")
    if not ids:
        errors.append("action_queue.md has no valid action ids")
    return errors


def latest_daily_record_date() -> date | None:
    dates: list[date] = []
    for path in sorted((ROOT / "02_daily/logs").glob("*.md")):
        for raw in DATE_HEADING.findall(path.read_text(encoding="utf-8")):
            try:
                dates.append(date.fromisoformat(raw))
            except ValueError:
                continue
    return max(dates) if dates else None


def check_dashboard() -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(build_dashboard.DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Unable to read dashboard data: {exc}"]

    errors.extend(build_dashboard.validate(data))
    latest_daily = latest_daily_record_date()
    if latest_daily is not None:
        try:
            snapshot_date = date.fromisoformat(data["meta"]["as_of"])
            if snapshot_date < latest_daily:
                errors.append(
                    "Dashboard snapshot is older than the latest daily record: "
                    f"{snapshot_date} < {latest_daily}"
                )
        except (KeyError, ValueError):
            pass
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
    results.append(("Project manifest", check_manifest(), None))
    results.append(("Action queue ids", check_action_queue(), None))
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
