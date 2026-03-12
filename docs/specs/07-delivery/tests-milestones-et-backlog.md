# Tests, milestones et backlog

## 1. Milestones

### Milestone 1 - Socle

Scope:

- config auth
- client HTTP cPanel
- test `list_domains`
- validation hostname/IP

Acceptance criteria:

- le CLI charge la config depuis env ou fichier
- un `config doctor` valide la connectivite et les champs requis
- `domains list` retourne un resultat structure

### Milestone 2 - DNS-first

Scope:

- lecture de zone DNS
- recherche hostname
- upsert `A`
- delete `A`
- verification DNS

Acceptance criteria:

- `dns upsert` couvre `create`, `update`, `no-op`, `refuse`
- `dns delete` supprime uniquement les records univoques
- `dns verify` retourne des statuts normalises

### Milestone 3 - UX CLI

Scope:

- mode interactif
- confirmations
- sortie JSON
- dry-run

Acceptance criteria:

- lancer `o2switch-cli` sans sous-commande ouvre le mode interactif
- les commandes de mutation ont le meme resultat en mode texte et JSON
- `--dry-run` n'ecrit jamais cote cPanel

### Milestone 4 - Hosted subdomains

Scope:

- create hosted subdomain
- search hosted subdomains
- delete hosted subdomain selon capacite detectee

Acceptance criteria:

- `subdomains create` verifie le parent et le label
- `subdomains search` remonte les objets hosted existants
- `subdomains delete` retourne `not_supported` proprement si aucun endpoint de suppression n'est exploitable

## 2. Couverture de tests

| Niveau | Couvre |
| --- | --- |
| unit | validators, normalisation, planification upsert/delete, mapping erreurs |
| integration | client cPanel mocke, parsing reponses API, workflow DNS-first |
| CLI | commandes Typer, options globales, JSON/text outputs, exit codes |
| end-to-end controle | environnement de test o2switch ou fixtures HTTP enregistrees |

## 3. Matrice de tests minimum

| Sujet | Type |
| --- | --- |
| validation FQDN | unit |
| validation IPv4 | unit |
| denylist labels reserves | unit |
| choix create/update/no-op/refuse | unit |
| conflit multiple `A` records | unit |
| mapping `401/403/404` vers erreurs metier | integration |
| `domains list` sur reponse cPanel reelle ou fixture | integration |
| `dns upsert --dry-run` | CLI |
| `dns delete --force` | CLI |
| callback Typer sans sous-commande | CLI |
| verification DNS positive / mismatch / timeout | integration |

## 4. Validation commands cibles

Ces commandes sont la cible de l'outillage du repo une fois le scaffold code en place:

```bash
ruff check .
ruff format --check .
pytest
```

Commande optionnelle si typing strict active:

```bash
mypy o2switch_cli
```

## 5. Sequencement backlog

| Version | Livrables |
| --- | --- |
| `V1` | domaines, DNS-first, verify, dry-run, JSON, audit |
| `V1.1` | create/search hosted subdomains |
| `V2` | delete hosted enrichi, `AAAA`, `CNAME`, wildcard, templates |

## 6. Definition of done

Une iteration est finie si:

- la spec cible est couverte sans placeholder
- les tests du niveau adequat existent
- les erreurs sont actionnables
- les sorties texte et JSON sont coherentes
- l'audit ne fuit aucun secret
