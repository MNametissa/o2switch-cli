# o2switch-cli

CLI interactif pour gerer domaines, sous-domaines cPanel et enregistrements DNS sur un hebergement o2switch/cPanel.

## Installation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

## Configuration

Convention de nommage:

- binaire CLI: `o2switch-cli`
- package Python: `o2switch_cli`
- variables d'environnement: `O2SWITCH_CLI_*`

Variables attendues:

```bash
export O2SWITCH_CLI_CPANEL_HOST=saule.o2switch.net
export O2SWITCH_CLI_CPANEL_USER=mon_user
export O2SWITCH_CLI_CPANEL_TOKEN=mon_token
```

## Usage

```bash
.venv/bin/o2switch-cli --help
.venv/bin/o2switch-cli domains list
.venv/bin/o2switch-cli dns upsert --host odoo-staging.ginutech.com --ip 203.0.113.25
.venv/bin/o2switch-cli dns delete --host odoo-staging.ginutech.com --dry-run
.venv/bin/o2switch-cli subdomains create --root ginutech.com --label odoo-staging --ip 203.0.113.25
.venv/bin/o2switch-cli config show --json
```

Sans sous-commande, le binaire ouvre le mode interactif si le terminal est TTY.

## Development

```bash
.venv/bin/ruff check .
.venv/bin/ruff format .
.venv/bin/pytest
```

## Specs

Le pack de specifications projet est dans [`docs/specs/README.md`](docs/specs/README.md).
