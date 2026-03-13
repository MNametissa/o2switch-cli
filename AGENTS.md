# Repository Guidelines

## Project Structure & Module Organization

This repository is documentation-first. The active source of truth lives in `docs/specs/`, indexed by `docs/specs/README.md`. Read the spec pack before changing implementation details.

When code is scaffolded, keep the Python package under `o2switch_cli/` and follow the planned split:

- `o2switch_cli/cli/` for Typer command entrypoints
- `o2switch_cli/core/` for auth, cPanel adapters, validation, and services
- `o2switch_cli/config/` for settings loading
- `tests/` for unit, integration, and CLI tests

Keep repo-level docs in `README.md` and `docs/specs/`.

## Build, Test, and Development Commands

The package is not scaffolded yet, so there is no runnable app today. Target commands, once the Python project exists, are:

- `ruff check .` to run linting
- `ruff format .` to format code
- `pytest` to run the test suite
- `mypy o2switch_cli` for optional type checking

Use `rg` for fast search, for example `rg "dns upsert" docs/specs`.

## Coding Style & Naming Conventions

Use Python 3.11+ with 4-space indentation and explicit type hints on public functions. Prefer small service modules over large command files.

- Package and module names: `snake_case`
- Classes: `PascalCase`
- Functions, variables, test names: `snake_case`
- CLI binary: `o2switch-cli`
- Environment variables: `O2SWITCH_CLI_*`

Follow the spec decision log before introducing new naming or API patterns.

## Testing Guidelines

Use `pytest`. Name test files `test_*.py` and mirror the package structure where practical. Prioritize coverage for validators, DNS upsert planning, error mapping, and Typer CLI outputs. Add integration tests for cPanel client behavior using mocks or recorded fixtures, not live secrets.

## Documentation Sources

Do not rely on a single source. Use:

- local source-of-truth docs in `docs/specs/`
- official vendor docs for o2switch and cPanel APIs
- Context7 MCP for framework and library documentation, including Typer patterns

When docs disagree, prefer repository specs for project decisions and official vendor/framework docs for API or syntax details.

## Branching, Commits, and PRs

Use a trunk-based workflow. Create branches from `main` with one of these patterns:

- `feature/<scope>-<short-name>`
- `fix/<scope>-<short-name>`
- `chore/<scope>-<short-name>`
- `release/<version>`

Use Conventional Commits, for example `docs: add contributor rules` or `feat: scaffold dns service`.

Versioning is SemVer. The current package version source of truth is `o2switch_cli/__init__.py`, build metadata reads it from `pyproject.toml`, release notes live in `CHANGELOG.md`, and release tags must use `vMAJOR.MINOR.PATCH`.

After every update batch, create a commit before handing work off. Do not leave intended repository changes uncommitted.

PRs should include:

- a short summary of behavior changes
- linked issue or spec reference
- links to the relevant spec files in `docs/specs/`
- test evidence or a note explaining why tests were not run
- sample CLI output when changing prompts or JSON responses

## Security & Configuration Tips

Never commit cPanel tokens or `.env` files. Use `O2SWITCH_CLI_CPANEL_HOST`, `O2SWITCH_CLI_CPANEL_USER`, and `O2SWITCH_CLI_CPANEL_TOKEN` locally. Do not log secrets, and prefer `--dry-run` before destructive DNS or subdomain actions.
