#!/usr/bin/env python3
"""OptiMATE v1-light CLI."""

import asyncio
from pathlib import Path

import click


@click.group()
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging verbosity.")
@click.pass_context
def cli(ctx, log_level):
    """OptiMATE v1-light — Autonomous Optimization Consulting Agent.

    Transforms a business problem description + raw data into a solved
    optimization model and a consultant-grade report.
    """
    from optimatecore.config import setup_logging
    setup_logging(log_level.upper())


@cli.command()
@click.option(
    "--input", "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to problem description file (.txt)",
)
@click.option(
    "--data", "-d",
    multiple=True,
    type=click.Path(exists=True),
    help="Path to data file(s) (.csv or .json). Can be repeated.",
)
@click.option(
    "--run-id",
    default=None,
    help="Custom run ID (auto-generated from timestamp if omitted).",
)
@click.option(
    "--output-dir",
    default="artifacts",
    show_default=True,
    help="Base directory for run artifacts.",
)
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["anthropic", "openai", "groq"], case_sensitive=False),
    help="LLM provider to use. Overrides LLM_PROVIDER env var.",
)
@click.option(
    "--api-key",
    default=None,
    help="API key for the chosen provider. Overrides env var.",
)
def run(input, data, run_id, output_dir, provider, api_key):
    """Run the full OptiMATE optimization pipeline."""
    from optimatecore import config as cfg
    from optimatecore.config import validate_config
    from optimatecore.exceptions import ConfigurationError, OptiMATEError
    from optimatecore.llm_client import build_client
    from optimatecore.orchestrator import Orchestrator

    # Validate config before doing anything
    try:
        validate_config(provider)
    except ConfigurationError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise SystemExit(1)

    problem_text = Path(input).read_text(encoding="utf-8")
    data_files = list(data)

    if not data_files:
        click.echo(
            "Warning: No data files provided. Data Profiler will have nothing to analyze.",
            err=True,
        )

    # Build client — CLI flags override env vars
    client = None
    if provider:
        resolved_key = api_key or {
            "anthropic": cfg.ANTHROPIC_API_KEY,
            "openai": cfg.OPENAI_API_KEY,
            "groq": cfg.GROQ_API_KEY,
        }.get(provider, "")
        if not resolved_key:
            click.echo(
                f"Error: No API key found for provider '{provider}'. "
                f"Set the matching env var or pass --api-key.",
                err=True,
            )
            raise SystemExit(1)
        client = build_client(provider, api_key=resolved_key)

    orchestrator = Orchestrator(base_dir=output_dir, client=client)

    try:
        report_path = asyncio.run(
            orchestrator.run(
                problem_description=problem_text,
                data_file_paths=data_files,
                run_id=run_id,
            )
        )
        click.echo(f"\nDone! Report: {report_path}")
    except OptiMATEError as e:
        click.echo(f"\nPipeline error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("run_id")
@click.option(
    "--output-dir",
    default="artifacts",
    show_default=True,
    help="Base directory for run artifacts.",
)
def status(run_id, output_dir):
    """Show what artifacts exist for a given run ID."""
    run_dir = Path(output_dir) / run_id
    if not run_dir.exists():
        click.echo(f"Run '{run_id}' not found in {output_dir}/")
        raise SystemExit(1)

    click.echo(f"\nRun: {run_id}")
    click.echo(f"Directory: {run_dir.resolve()}\n")

    stages = [
        ("problem_brief.json",        "Layer 1 — Business Analysis"),
        ("data_inventory.json",        "Layer 1 — Data Profiling"),
        ("opportunities/",            "Layer 2 — Opportunity Scouting"),
        ("ranked_opportunities.json", "Layer 3 — Opportunity Ranking"),
        ("models/",                   "Layer 4 — Formulation/Solving"),
        ("report.md",                 "Layer 5 — Report"),
    ]

    for artifact, label in stages:
        path = run_dir / artifact
        exists = path.exists()
        symbol = "✓" if exists else "○"
        click.echo(f"  {symbol}  {label}")
        if exists and path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    click.echo(f"       {child.relative_to(run_dir)}")


if __name__ == "__main__":
    cli()
