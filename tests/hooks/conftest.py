"""Mark the upstream-pending tests listed in pending_upstream.txt as strict xfails."""

from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent

_REASONS = {
    "amendment-7-8": (
        "ADR-0018 amendment 7 or 8: specified and tested upstream, implementation "
        "(brief C8 or C9) not yet landed -- see pending_upstream.txt"
    ),
    "literal-mode-soh-del": (
        "literal mode does not yet refuse SOH (0x01) or DEL (0x7f), which ADR-0018's "
        "second amendment requires -- see pending_upstream.txt"
    ),
}


def _load_pending() -> dict[str, str]:
    """Map each listed test ID to the reason of the [section] it sits under."""
    pending: dict[str, str] = {}
    section = None
    for raw in (_HERE / "pending_upstream.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            if section not in _REASONS:
                raise pytest.UsageError(f"pending_upstream.txt: unknown section [{section}]")
            continue
        if section is None:
            raise pytest.UsageError(f"pending_upstream.txt: {line!r} is not under a [section]")
        pending[line] = _REASONS[section]
    return pending


_PENDING = _load_pending()


def _test_id(item: pytest.Item) -> str:
    return item.nodeid.split("tests/hooks/", 1)[-1]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    seen = set()
    for item in items:
        test_id = _test_id(item)
        if test_id in _PENDING:
            seen.add(test_id)
            item.add_marker(pytest.mark.xfail(reason=_PENDING[test_id], strict=True))

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
