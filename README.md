# o2switch-cli

CLI interactif pour gerer domaines, sous-domaines cPanel et enregistrements DNS sur un hebergement o2switch/cPanel.

Version actuelle: `0.1.0`

## Installation

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Standalone bootstrap:

```bash
./install.sh
```

Development bootstrap:

```bash
./install.sh --dev
```

Reusing an existing local install:

```bash
./install.sh
./install.sh --dev
./install.sh --reinstall
```

`install.sh` now reuses the existing `.venv` and skips `pip install -e` when `pyproject.toml` and the selected install profile are unchanged. This matches pip's editable-install behavior: reinstall is mainly needed when project metadata changes.

The installer also publishes launchers into `~/.local/bin` by default:

```bash
o2switch-cli --version
o2switch-cli --help
```

`o2switch-cli` est l'unique commande shell publique. `o2switch_cli` reste seulement le nom du package Python et l'ancien alias shell est nettoye automatiquement lors d'une reinstallation.

It also installs managed bash completion for `o2switch-cli` into
`~/.local/share/bash-completion/completions/` and adds a managed sourcing block in `~/.bashrc`.

Quand l'installateur detecte que `~/.local/bin` n'est pas deja gere dans `~/.bashrc`, il ajoute un bloc balise pour ce PATH. Apres installation ou desinstallation, rechargez votre shell courant:

```bash
source ~/.bashrc && hash -r
```

Standalone uninstall:

```bash
./uninstall.sh
./uninstall.sh --purge-venv
./uninstall.sh --purge-config --purge-state
```

`./uninstall.sh` now removes launchers, completion, and managed shell wiring by default, but preserves `.venv` for faster reinstall. Use `--purge-venv` if you want a full local removal.

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

Setup guidee:

```bash
.venv/bin/o2switch-cli config init
.venv/bin/o2switch-cli config init --path .env --test-api
```

Par defaut, l'audit est ecrit dans le repertoire d'etat utilisateur de la plateforme.
Sous Linux, cela devient typiquement `~/.local/state/o2switch-cli/audit.jsonl`.

Setup non interactive:

```bash
.venv/bin/o2switch-cli config init \
  --path .env \
  --cpanel-host saule.o2switch.net \
  --cpanel-user mon_user \
  --cpanel-token mon_token \
  --non-interactive
```

## Usage

```bash
.venv/bin/o2switch-cli --version
.venv/bin/o2switch-cli --help
.venv/bin/o2switch-cli completion show
.venv/bin/o2switch-cli completion install
.venv/bin/o2switch-cli config init --help
.venv/bin/o2switch-cli domains list
.venv/bin/o2switch-cli domains list --page 2 --page-size 10
.venv/bin/o2switch-cli dns upsert --host odoo-staging.ginutech.com --ip 203.0.113.25
.venv/bin/o2switch-cli dns upsert --zone ginutech.com --host odoo-staging --ip 203.0.113.25
.venv/bin/o2switch-cli dns search ginutech --page-size 15
.venv/bin/o2switch-cli dns delete --zone ginutech.com --host odoo-staging --dry-run
.venv/bin/o2switch-cli subdomains create --root ginutech.com --label odoo-staging --ip 203.0.113.25
.venv/bin/o2switch-cli config show --json
```

Sans sous-commande, le binaire ouvre le mode interactif si le terminal est TTY.
Le mode interactif inclut maintenant des spinners de chargement, une recherche temps reel avec suggestions pendant la frappe, et une navigation paginee pour les grands jeux de resultats.
En mode commande, les sous-commandes, options, et valeurs principales (`--root`, `--host`, `--fqdn`, termes de recherche) sont autocompletables en bash.
Les commandes DNS acceptent `--zone` pour forcer explicitement la zone DNS cible. Quand `--zone` est fournie, `--host` peut etre un label simple (`odoo-staging`) ou un FQDN deja inclus dans cette zone.

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
