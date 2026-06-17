from __future__ import annotations

import importlib.metadata

import click

from app.cli.commands.start import start_command


def _get_version() -> str:
    try:
        return importlib.metadata.version("easypost-mcp")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


@click.group()
@click.version_option(version=_get_version(), prog_name="easypost-mcp")
def cli() -> None:
    """EasyPost Model Context Protocol (MCP) server."""


cli.add_command(start_command)


def run_cli() -> None:
    cli()
