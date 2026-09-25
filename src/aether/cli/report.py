"""Report primitives for ``aether doctor`` — adapted from
``hermes_cli/hermes_cli_doctor_report.py`` (glyph rows, sections, findings).

Kept dependency-free (stdlib only) so the CLI stays light and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ANSI colors (auto-disabled when stdout is not a TTY or NO_COLOR is set).
_RESET = "\033[0m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_DIM = "\033[2m"
_BOLD = "\033[1m"

_GLYPH = {"ok": "✓", "warn": "⚠", "fail": "✗"}
_COLOR = {"ok": _GREEN, "warn": _YELLOW, "fail": _RED}


def _colorize(enabled: bool) -> None:
    global _USE_COLOR
    _USE_COLOR = enabled


_USE_COLOR = True


def _c(text: str, color: str, bold: bool = False) -> str:
    if not _USE_COLOR:
        return text
    return f"{_BOLD if bold else ''}{color}{text}{_RESET}"


def check_ok(text: str, detail: str = "") -> None:
    _mark("ok", text, detail)


def check_warn(text: str, detail: str = "") -> None:
    _mark("warn", text, detail)


def check_fail(text: str, detail: str = "") -> None:
    _mark("fail", text, detail)


def _mark(status: str, text: str, detail: str) -> None:
    glyph = _c(_GLYPH[status], _COLOR[status], bold=True)
    line = f"  {glyph} {text}"
    if detail:
        line += f" {_c(detail, _DIM)}"
    print(line)


def check_info(text: str) -> None:
    print(f"    {_c('→', _CYAN)} {text}")


def check_bool(cond: bool, ok, bad, *, fail: bool = False) -> bool:
    """``check_ok(*ok)`` when *cond* else ``check_warn(*bad)`` (``check_fail``
    with fail=True). *ok* / *bad* are a text or ``(text, detail)`` tuple."""
    args = ok if cond else bad
    fn = check_ok if cond else (check_fail if fail else check_warn)
    # Typer/CLI context: pass strings straight through, tuples get split.
    if isinstance(args, str):
        fn(args)
    elif isinstance(args, tuple):
        fn(*args)
    else:  # pragma: no cover - defensive
        fn(str(args))
    return bool(cond)


def section(title: str) -> None:
    """Print a doctor section banner: blank line + bold cyan ◆ title."""
    print()
    print(_c(f"◆ {title}", _CYAN, bold=True))


@dataclass
class Finding:
    """What one doctor check contributed: issues + fixes."""
    issues: List[str] = field(default_factory=list)
    fixed: int = 0

    def merge(self, other: "Finding") -> None:
        self.issues.extend(other.issues)
        self.fixed += other.fixed

    @property
    def ok(self) -> bool:
        return not self.issues


def fail_and_issue(text: str, detail: str, fix: str, findings: Finding, *, fail: bool = True) -> None:
    """Emit a check row and append the corresponding fix instruction."""
    (check_fail if fail else check_warn)(text, detail)
    findings.issues.append(fix)


def emit(findings: Finding) -> int:
    """Print the collected fix list; return an exit code (0 = healthy)."""
    if not findings.issues:
        return 0
    print()
    print(_c("◆ Suggestions", _CYAN, bold=True))
    for i, fix in enumerate(findings.issues, start=1):
        print(f"   {i}. {_c(fix, _DIM)}")
    return 1