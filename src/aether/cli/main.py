"""``aether`` — operator CLI for an Aether install (terminal twin of the web
console at ``[IP]:8456/setup``).

Adapted from ``hermes_cli/main.py`` + command surface (NousResearch/hermes).
Three commands mirror the console's three jobs:

    aether doctor   →  diagnose the install (✓/⚠/✗ + fix list), like the
                       console's ⚡ Diagnose button
    aether setup    →  interactive quick-setup wizard (only prompts for what
                       is *missing*), like the console's Setup form — the
                       terminal version of BotFather + provider key entry
    aether status   →  one-screen runtime snapshot, like the console Status tab

Run ``aether doctor`` first if something isn't working; every ✗ row carries a
next step.  Exit code is 0 when the install is healthy.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer

from aether.envfile import env_file_path, load_env
from aether.config import settings

app = typer.Typer(
    name="aether",
    help="Aether Core operator CLI — console help at [IP]:8456/setup.",
    add_completion=False,
)


@app.command()
def doctor(fix: bool = typer.Option(False, "--fix", "-f", help="attempt safe repairs")) -> None:
    """Diagnose the install — mirror of the console's ⚡ Diagnose."""
    from aether.cli import doctor as _doctor

    code = _doctor.run_doctor(should_fix=fix)
    raise typer.Exit(code)


@app.command()
def setup(quick: bool = typer.Option(False, "--quick", "-q", help="only ask for missing keys")) -> None:
    """Interactive quick-setup wizard (BotFather token, provider key, …).

    Prompt-only-for-**missing** semantics mirror Hermes' ``hermes setup --quick``;
    writes go to the same ``.env`` the console at ``/setup`` manages.
    """
    from aether.cli import setup as _setup

    env = load_env(env_file_path())
    _setup.run(env, quick=quick)


@app.command()
def status() -> None:
    """One-screen snapshot of the running install."""
    from aether.cli.status import print_status

    print_status(load_env(env_file_path()))


@app.command()
def health() -> None:
    """Check the API health endpoint."""
    import httpx

    url = f"http://{settings.API_HOST}:{settings.API_PORT}/health"
    try:
        resp = httpx.get(url, timeout=5.0)
        typer.echo(f"API Health: {resp.json()['status']}")
    except Exception as exc:  # pragma: no cover - operator-facing only
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
