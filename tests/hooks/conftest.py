"""Mark the tests listed in pending_upstream.txt as expected failures.

Each [section] in that file carries a reason, a strictness and a platform
condition. A section whose condition does not hold on this machine leaves its
tests alone: they run as ordinary tests and must pass.
"""

import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest

_HERE = Path(__file__).resolve().parent


def _bash_major() -> int:
    """The major version of the bash the hooks will actually run under.

    Both hooks start with `#!/usr/bin/env bash`, so that is the first `bash`
    on PATH -- on macOS usually /bin/bash, which is 3.2.
    """
    bash = shutil.which("bash")
    if bash is None:
        return 0
    result = subprocess.run(
        [bash, "-c", "echo ${BASH_VERSINFO[0]}"], capture_output=True, text=True, check=False
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


_BASH_MAJOR = _bash_major()


class _Section(NamedTuple):
    reason: str
    strict: bool
    applies: bool


_SECTIONS = {
    "amendment-7-8": _Section(
        reason=(
            "ADR-0018 amendment 7 or 8: specified and tested upstream, implementation "
            "(brief C8 or C9) not yet landed -- see pending_upstream.txt"
        ),
        strict=True,
        applies=True,
    ),
    "bash-3-control-chars": _Section(
        reason=(
            f"on bash {_BASH_MAJOR}, literal mode lets SOH (0x01) and DEL (0x7f) through; "
            "bash 5 refuses them -- see pending_upstream.txt"
        ),
        strict=True,
        applies=_BASH_MAJOR < 4,
    ),
    "bash-3-slow": _Section(
        reason=(
            f"on bash {_BASH_MAJOR}, too slow to decide a long path within the test's "
            "time budget; bash 5 is not -- see pending_upstream.txt"
        ),
        strict=False,
        applies=_BASH_MAJOR < 4,
    ),
}


def _load_pending() -> dict[str, str]:
    """Map each listed test ID to the name of the [section] it sits under."""
    pending: dict[str, str] = {}
    section = None
    for raw in (_HERE / "pending_upstream.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            if section not in _SECTIONS:
                raise pytest.UsageError(f"pending_upstream.txt: unknown section [{section}]")
            continue
        if section is None:
            raise pytest.UsageError(f"pending_upstream.txt: {line!r} is not under a [section]")
        pending[line] = section
    return pending


_PENDING = _load_pending()


def _test_id(item: pytest.Item) -> str:
    return item.nodeid.split("tests/hooks/", 1)[-1]


def pytest_report_header(config: pytest.Config) -> str:
    return f"hooks run under bash {_BASH_MAJOR} ({shutil.which('bash')})"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    seen = set()
    for item in items:
        test_id = _test_id(item)
        name = _PENDING.get(test_id)
        if name is None:
            continue
        seen.add(test_id)
        section = _SECTIONS[name]
        if section.applies:
            item.add_marker(pytest.mark.xfail(reason=section.reason, strict=section.strict))

    # A listed ID that no longer names a test is stale -- a test renamed or
    # deleted upstream. Only judge that on an unfiltered run, and only for
    # modules that were actually collected, so running one file or one test
    # does not trip it.
    filtered = config.option.keyword or config.option.markexpr or any("::" in a for a in config.args)
    if filtered:
        return
    collected_modules = {_test_id(item).split("::", 1)[0] for item in items}
    stale = sorted(p for p in set(_PENDING) - seen if p.split("::", 1)[0] in collected_modules)
    if stale:
        listing = "\n  ".join(stale[:20])
        raise pytest.UsageError(
            f"pending_upstream.txt lists {len(stale)} test ID(s) that were not collected; "
            f"remove or correct them:\n  {listing}"
        )
