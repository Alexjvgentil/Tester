from __future__ import annotations

import io
import sys
from pathlib import Path

import click

# Ensure stdout/stderr use UTF-8 on Windows to avoid charmap encoding errors
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from web_tester.config import load_config, Config
from web_tester.exceptions import ConfigError


@click.command()
@click.argument("url")
@click.option("-i", "--instructions", required=True, help="What the agent should do on the page.")
@click.option("-n", "--name", default=None, help="Test name (used in folder name). Defaults to first 50 chars of instructions.")
@click.option("--provider", default=None, type=click.Choice(["openai", "anthropic"]), help="Override MODEL_PROVIDER from .env")
@click.option("--model", default=None, help="Override MODEL_NAME from .env")
@click.option("--headless/--no-headless", default=None, help="Run browser headless (default: true)")
@click.option("--max-steps", default=None, type=int, help="Override MAX_STEPS from .env")
@click.option("--output-dir", default=None, help="Override TEST_RUNS_DIR from .env")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Stream step-by-step progress to stdout.")
def main(
    url: str,
    instructions: str,
    name: str | None,
    provider: str | None,
    model: str | None,
    headless: bool | None,
    max_steps: int | None,
    output_dir: str | None,
    verbose: bool,
) -> None:
    """Run an AI web test against URL.

    \b
    Example:
        web-tester https://example.com \\
          -i "Click the 'More information' link and verify it loads" \\
          -n smoke_test --no-headless -v
    """
    try:
        config = load_config()

        if provider:
            config.model_provider = provider
        if model:
            config.model_name = model
        if headless is not None:
            config.browser_headless = headless
        if max_steps is not None:
            config.max_steps = max_steps
        if output_dir is not None:
            config.test_runs_dir = output_dir

        config.validate()
    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo("Copy .env.example to .env and fill in your API key.", err=True)
        sys.exit(1)

    from web_tester.agent import WebTestAgent

    click.echo(f"Starting test: {name or instructions[:50]}")
    click.echo(f"URL: {url}")
    click.echo(f"Model: {config.model_provider}/{config.model_name}")
    click.echo("")

    agent = WebTestAgent(config=config)
    result = agent.run(url=url, instructions=instructions, test_name=name, verbose=verbose)

    click.echo("")
    status_color = "green" if result.status == "pass" else "red"
    click.echo(click.style(f"Status: {result.status.upper()}", fg=status_color, bold=True))
    click.echo(f"Steps:  {result.steps_taken}")
    click.echo(f"Time:   {result.duration_seconds:.1f}s")
    click.echo(f"Folder: {result.session_dir}")
    click.echo(f"Report: {result.report_md}")
    click.echo("")
    click.echo(result.final_message)

    sys.exit(0 if result.status == "pass" else 1)


if __name__ == "__main__":
    main()
