# o2switch-cli

CLI interactif pour gerer domaines, sous-domaines cPanel et enregistrements DNS sur un hebergement o2switch/cPanel.

Version actuelle: `0.1.0`

## Installation

```bash
./install.sh
```

The installer:
- Creates a local virtual environment
- Installs the CLI and dependencies
- Prompts for cPanel credentials (stored in `~/.config/o2switch-cli/.env`)
- Publishes `o2switch-cli` to `~/.local/bin`
- Installs bash completion

After install, reload your shell:

```bash
source ~/.bashrc && hash -r
```

### Non-interactive install

```bash
./install.sh --cpanel-host saule.o2switch.net --cpanel-user myuser --cpanel-token mytoken
```

### Development install

```bash
./install.sh --dev
```

### Skip setup wizard

```bash
./install.sh --skip-setup
o2switch-cli config init  # configure later
```

### Uninstall

```bash
./uninstall.sh
./uninstall.sh --purge-venv --purge-config --purge-state
```

## Configuration

Credentials are stored globally in `~/.config/o2switch-cli/.env` and loaded automatically.

```bash
# Show current config and where it's loaded from
o2switch-cli config show

# Show config file paths (active, global, local)
o2switch-cli config path

# Re-run setup wizard
o2switch-cli config init

# Test API access
o2switch-cli config test
```

### Config file locations

1. **Local** `.env` in current directory (takes precedence)
2. **Global** `~/.config/o2switch-cli/.env` (default)

### Environment variables

You can also set credentials via environment variables:

```bash
export O2SWITCH_CLI_CPANEL_HOST=saule.o2switch.net
export O2SWITCH_CLI_CPANEL_USER=myuser
export O2SWITCH_CLI_CPANEL_TOKEN=mytoken
```

### Getting a cPanel API token

1. Log into cPanel
2. Go to Security > Manage API Tokens
3. Create a new token with appropriate permissions
4. Copy the token (it's only shown once)

## Usage

```bash
o2switch-cli              # Interactive mode (if TTY)
o2switch-cli --help       # Show all commands
```

### DNS Records

```bash
# Point a hostname to an IP (create or update A record)
o2switch-cli dns upsert --host staging.example.com --ip 203.0.113.25

# With explicit zone and custom TTL
o2switch-cli dns upsert --zone example.com --host staging --ip 203.0.113.25 --ttl 600

# Search DNS records
o2switch-cli dns search example

# Delete an A record
o2switch-cli dns delete --host staging.example.com

# Verify DNS resolution
o2switch-cli dns verify --host staging.example.com --ip 203.0.113.25

# Dry run (show what would change without applying)
o2switch-cli dns upsert --host staging.example.com --ip 203.0.113.25 --dry-run
```

### Domains

```bash
o2switch-cli domains list
o2switch-cli domains list --page 2 --page-size 10
```

### Subdomains

```bash
o2switch-cli subdomains create --root example.com --label staging --ip 203.0.113.25
o2switch-cli subdomains list
o2switch-cli subdomains delete --fqdn staging.example.com
```

### Output formats

```bash
o2switch-cli domains list --json
o2switch-cli config show --json
```

Interactive mode includes loading spinners, real-time search suggestions, and paginated navigation.

## Versioning

`o2switch-cli` suit **Semantic Versioning**.

- format: `MAJOR.MINOR.PATCH`
- version actuelle: `0.1.0`
- tags de release: `vMAJOR.MINOR.PATCH`
- changelog: [`CHANGELOG.md`](CHANGELOG.md)
- politique detaillee: [`VERSIONING.md`](VERSIONING.md)

Regles de bump:

- `MAJOR`: rupture de compatibilite sur la CLI, la sortie JSON stable, les comportements de mutation, ou les variables/configs publiques
- `MINOR`: nouvelles commandes, nouvelles options retro-compatibles, nouveaux workflows ou nouveaux champs JSON optionnels
- `PATCH`: corrections retro-compatibles, docs, tests, durcissement interne sans rupture contractuelle

Tant que le projet reste en `0.x`, un bump `MINOR` peut encore embarquer des changements cassants. Les correctifs `PATCH` doivent rester retro-compatibles.

Source de verite:

- version package: [`o2switch_cli/__init__.py`](o2switch_cli/__init__.py)
- metadata build: [`pyproject.toml`](pyproject.toml) lit cette version dynamiquement

Avant une release, mettre a jour le changelog, verifier `o2switch-cli --version`, puis tagger le commit avec `vX.Y.Z`.

## Development

```bash
.venv/bin/ruff check .
.venv/bin/ruff format .
.venv/bin/pytest
```

## Specs

Le pack de specifications projet est dans [`docs/specs/README.md`](docs/specs/README.md).
