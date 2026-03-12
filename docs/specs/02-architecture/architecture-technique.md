# Architecture technique

## 1. Vue d'ensemble

L'architecture est organisee en couches pour separer:

- l'entree CLI
- la logique metier
- l'integration cPanel
- la validation
- la journalisation et la verification DNS

## 2. Modules internes

| Module | Responsabilite |
| --- | --- |
| `auth` | chargement et validation des credentials cPanel |
| `cpanel_client` | appels HTTP vers UAPI / API 2 |
| `domain_catalog` | listing et recherche des domaines disponibles |
| `dns_catalog` | inspection des zones et des enregistrements |
| `dns_mutator` | creation, modification, suppression de records |
| `subdomain_manager` | creation/suppression des sous-domaines cPanel |
| `interactive_ui` | prompts, choix, confirmations |
| `validator` | validation stricte des inputs |
| `audit` | logs structures |
| `resolver` | lookup DNS de verification |

## 3. Organisation du code recommandee

```text
o2switch_cli/
├── cli/
│   ├── main.py
│   ├── dns.py
│   ├── subdomains.py
│   ├── domains.py
│   └── interactive.py
├── core/
│   ├── auth.py
│   ├── cpanel_client.py
│   ├── validators.py
│   ├── domain_service.py
│   ├── dns_service.py
│   ├── subdomain_service.py
│   ├── audit.py
│   └── models.py
├── config/
│   └── settings.py
├── infra/
│   ├── http.py
│   └── resolver.py
└── tests/
```

## 4. Stack recommandee

| Couche | Recommandation |
| --- | --- |
| langage | Python 3.11+ |
| framework CLI | `Typer` |
| prompts interactifs | `questionary` ou `InquirerPy` |
| client HTTP | `httpx` |
| config | `.env` + fichier local |
| validation | `pydantic` |
| logs | JSON lines ou `structlog` |
| sortie machine | JSON optionnel |

## 5. Strategie CLI

Le CLI doit suivre une composition `Typer` avec:

- une app racine
- des sous-apps `domains`, `dns`, `subdomains`
- un callback racine pour les options globales et le mode interactif par defaut

Ce choix est aligne avec les patterns documentes officiellement par Typer via `app.add_typer(...)`, `@app.callback()` et `invoke_without_command=True`.

## 6. Services applicatifs

| Service | Responsabilite |
| --- | --- |
| `DomainService` | lister et rechercher les domaines |
| `DNSService` | inspecter la zone, rechercher les records, upsert/delete |
| `SubdomainService` | creer/rechercher/supprimer des sous-domaines cPanel |
| `ValidationService` | politiques hostname, IPv4, TTL, docroot |
| `AuditService` | emission du journal structure |
| `ResolverService` | verification DNS post-mutation |

## 7. Topologie des dependances

```text
CLI -> Services -> Validators / Models -> cPanel client / Resolver -> Audit
```

Regles:

- le code CLI ne parle jamais directement HTTP
- la logique de decision `create/update/no-op/refuse` vit dans les services
- le client cPanel ne contient pas de logique metier de mutation
- la verification DNS est un composant separe pour eviter de melanger acceptation API et propagation externe

## 8. Flux internes

### Flux DNS-only

```text
CLI -> Validation -> DomainService -> DNSService.read_zone -> DNSService.plan_upsert -> cPanel client -> Audit -> Resolver
```

### Flux Hosted + DNS

```text
CLI -> Validation -> DomainService -> SubdomainService.create -> DNSService.plan_upsert -> cPanel client -> Audit -> Resolver
```

## 9. Strategie de dependances

- limiter les dependances au strict necessaire
- centraliser tous les appels reseau dans `cpanel_client`
- isoler les details cPanel UAPI et API 2 derriere des methodes stables
- garder les modeles de donnees serialisables pour JSON et logs

## 10. Contraintes de conception

- idempotence obligatoire sur les commandes de mutation
- `dry-run` disponible sans acces destructif
- aucun secret dans les logs
- toute action destructive passe par une confirmation ou un `--yes`
- l'architecture doit permettre l'ajout futur de `AAAA` et `CNAME`
