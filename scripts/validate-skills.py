#!/usr/bin/env python3
"""Validate every skills/<name>/SKILL.md in this repository.

Checks the things that make a skill silently fail to load, or drift out of
sync with the directory it lives in:

  errors   missing SKILL.md, unparseable or unclosed frontmatter, missing or
           empty name/description, a name that does not match its directory,
           a name that is not a lowercase-hyphen slug, an over-long name or
           description, an empty body, duplicate names
  warnings unrecognised frontmatter keys, a skill the README never mentions,
           stray files directly under skills/

Uses PyYAML when it is importable, and otherwise falls back to a strict
parser for the `key: value` subset that skill frontmatter actually uses, so
the script runs with a bare python3 and no install step.

    python3 scripts/validate-skills.py [root] [--strict]

Exits non-zero when there are errors, or when --strict is given and there
are warnings.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DELIM = "---"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
KNOWN_KEYS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "model",
    "disable-model-invocation",
}

IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


class Problems:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append((where, message))

    def warn(self, where: str, message: str) -> None:
        self.warnings.append((where, message))


def _parse_simple(raw: str) -> tuple[dict | None, str | None]:
    """Parse the `key: value` subset of YAML, rejecting anything ambiguous."""
    data: dict[str, str] = {}
    for lineno, line in enumerate(raw.split("\n"), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            return None, (
                f"line {lineno}: indented or multi-line frontmatter needs a real "
                "YAML parser to validate — install PyYAML (pip install pyyaml)"
            )
        key, sep, value = line.partition(":")
        if not sep:
            return None, f"line {lineno}: expected 'key: value', got {line!r}"
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif ": " in value:
            return None, (
                f"line {lineno}: the unquoted value for '{key}' contains ': ', which "
                "YAML reads as a nested mapping — wrap the value in quotes"
            )
        data[key] = value
    return data, None


def parse_frontmatter(text: str) -> tuple[dict | None, str | None, str | None]:
    """Return (mapping, body, error)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != DELIM:
        return None, None, "file does not open with a '---' frontmatter delimiter"

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == DELIM:
            end = i
            break
    if end is None:
        return None, None, "frontmatter is never closed by a second '---'"

    raw = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :])

    try:
        import yaml
    except ImportError:
        data, err = _parse_simple(raw)
        if err:
            return None, None, err
    else:
        try:
            data = yaml.safe_load(raw)
        except Exception as exc:  # noqa: BLE001 - report whatever YAML says
            return None, None, f"frontmatter is not valid YAML: {exc}"

    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None, None, "frontmatter is not a key/value mapping"
    return data, body, None


def check_skill(skill_md: Path, expected_name: str, rel: str, p: Problems) -> str | None:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        p.error(rel, f"is not valid UTF-8: {exc}")
        return None

    data, body, err = parse_frontmatter(text)
    if err:
        p.error(rel, err)
        return None

    for key in sorted(set(data) - KNOWN_KEYS):
        p.warn(rel, f"unrecognised frontmatter key '{key}'")

    name = data.get("name")
    if name is None:
        p.error(rel, "frontmatter has no 'name'")
    elif not isinstance(name, str) or not name.strip():
        p.error(rel, "'name' is empty")
    else:
        name = name.strip()
        if name != expected_name:
            p.error(rel, f"'name' is {name!r} but the directory is {expected_name!r}")
        if not NAME_RE.match(name):
            p.error(rel, f"'name' {name!r} is not a lowercase-hyphen slug")
        if len(name) > MAX_NAME:
            p.error(rel, f"'name' is {len(name)} characters, over the {MAX_NAME} limit")

    description = data.get("description")
    if description is None:
        p.error(rel, "frontmatter has no 'description' — without one the skill never triggers")
    elif not isinstance(description, str) or not description.strip():
        p.error(rel, "'description' is empty — without one the skill never triggers")
    elif len(description) > MAX_DESCRIPTION:
        p.error(
            rel,
            f"'description' is {len(description)} characters, over the {MAX_DESCRIPTION} limit",
        )

    if body is not None and not body.strip():
        p.error(rel, "has frontmatter but no body")

    return name if isinstance(name, str) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".", help="repository root (default: .)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print(f"error: no skills/ directory under {root}", file=sys.stderr)
        return 1

    p = Problems()

    for stray in sorted(x for x in skills_dir.iterdir() if x.is_file()):
        if stray.name != ".gitkeep":
            p.warn(str(stray.relative_to(root)), "stray file directly under skills/")

    skill_dirs = sorted(x for x in skills_dir.iterdir() if x.is_dir())
    if not skill_dirs:
        p.error("skills/", "contains no skill directories")

    readme = root / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""

    seen: dict[str, str] = {}
    checked = 0
    for d in skill_dirs:
        rel_dir = str(d.relative_to(root))
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            p.error(rel_dir, "has no SKILL.md")
            continue
        checked += 1
        rel = str(skill_md.relative_to(root))
        name = check_skill(skill_md, d.name, rel, p)
        if name:
            if name in seen:
                p.error(rel, f"duplicate skill name {name!r}, already used by {seen[name]}")
            else:
                seen[name] = rel
        if readme_text and f"skills/{d.name}/" not in readme_text:
            p.warn(rel_dir, "is not mentioned in README.md")

    for where, message in p.warnings:
        if IN_ACTIONS:
            print(f"::warning file={where}::{message}")
        print(f"warning: {where}: {message}")
    for where, message in p.errors:
        if IN_ACTIONS:
            print(f"::error file={where}::{message}")
        print(f"error: {where}: {message}", file=sys.stderr)

    print(
        f"\nchecked {checked} skill(s): {len(p.errors)} error(s), {len(p.warnings)} warning(s)"
    )

    if p.errors:
        return 1
    if args.strict and p.warnings:
        print("failing because --strict was given and there are warnings", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
