# Versioning Policy

`o2switch-cli` suit **Semantic Versioning** avec le format `MAJOR.MINOR.PATCH`.

Version actuelle: `0.1.0`

## Source Of Truth

La source de verite de la version package est [`o2switch_cli/__init__.py`](o2switch_cli/__init__.py).
[`pyproject.toml`](pyproject.toml) lit cette valeur dynamiquement via setuptools.

## Bump Rules

- `MAJOR`: changement non retro-compatible sur la CLI publique, les commandes, les options, les variables d'environnement, les formats JSON stables, ou les comportements de mutation attendus
- `MINOR`: ajout retro-compatible de fonctionnalites, commandes, options, integrations, modes interactifs, ou champs JSON optionnels
- `PATCH`: correctifs retro-compatibles, docs, tests, securite, performance, robustesse interne

## Pre-1.0 Rule

Tant que le projet est en `0.x`, un bump `MINOR` peut contenir une rupture de compatibilite. Les versions `PATCH` doivent rester retro-compatibles.

## Release Mechanics

- tag Git: `vMAJOR.MINOR.PATCH`
- changelog: [`CHANGELOG.md`](CHANGELOG.md)
- verifications minimales:
  - `o2switch-cli --version`
  - `PYTHONPATH=. .venv/bin/python -m ruff check .`
  - `PYTHONPATH=. .venv/bin/python -m pytest`

## Release Checklist

1. Choisir le bon bump SemVer.
2. Mettre a jour [`o2switch_cli/__init__.py`](o2switch_cli/__init__.py) si la version change.
3. Verifier que [`pyproject.toml`](pyproject.toml) pointe toujours vers cette source dynamique.
4. Mettre a jour [`CHANGELOG.md`](CHANGELOG.md).
5. Verifier l'affichage de `o2switch-cli --version`.
6. Tagger le commit avec `vX.Y.Z`.
