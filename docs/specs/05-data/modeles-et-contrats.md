# Modeles et contrats

## 1. Normalisation de nommage

- tous les hostnames sont compares en lowercase
- les espaces sont trims
- le trailing dot est retire pour les comparaisons
- les sorties affichent la forme canonique sans trailing dot

## 2. Modeles principaux

### `AppConfig`

| Champ | Type | Regle |
| --- | --- | --- |
| `cpanel_host` | `str` | requis |
| `cpanel_user` | `str` | requis |
| `cpanel_token` | `SecretStr` | requis |
| `default_ttl` | `int` | defaut `300` |
| `reserved_labels` | `list[str]` | surchargeable |
| `verify_dns_after_mutation` | `bool` | defaut `true` |
| `output_format` | `text|json` | defaut `text` |

### `DomainDescriptor`

| Champ | Type | Description |
| --- | --- | --- |
| `domain` | `str` | domaine racine |
| `type` | `main|addon|parked|subdomain` | type cPanel |
| `eligible_for_subdomain_creation` | `bool` | creation hosted possible |
| `has_dns_zone` | `bool` | zone DNS disponible |

### `DNSRecord`

| Champ | Type | Description |
| --- | --- | --- |
| `name` | `str` | FQDN normalise |
| `type` | `str` | `A` en V1 |
| `value` | `str` | IPv4 |
| `ttl` | `int` | TTL effectif |
| `zone` | `str` | domaine racine |
| `record_id` | `str|None` | identifiant/index cPanel |

### `SubdomainDescriptor`

| Champ | Type | Description |
| --- | --- | --- |
| `fqdn` | `str` | sous-domaine complet |
| `label` | `str` | label local |
| `root_domain` | `str` | domaine parent |
| `docroot` | `str` | repertoire cible |
| `managed_by_cpanel` | `bool` | toujours `true` pour hosted |

### `MutationPlan`

| Champ | Type | Description |
| --- | --- | --- |
| `operation` | `str` | `dns_upsert`, `dns_delete`, `subdomain_create` |
| `planned_action` | `create|update|delete|no-op|refuse` | decision metier |
| `before` | `object|None` | etat precedent |
| `after` | `object|None` | etat cible |
| `requires_force` | `bool` | ambiguite ou action destructive |
| `requires_confirmation` | `bool` | defaut `true` hors batch assume |

### `OperationResult`

| Champ | Type | Description |
| --- | --- | --- |
| `operation` | `str` | nom stable |
| `mode` | `dns-only|hosted+dns|hosted-only` | mode execute |
| `target` | `str` | hostname ou domaine |
| `zone` | `str|None` | zone concernee |
| `action` | `str` | action finale |
| `applied` | `bool` | mutation appliquee ou non |
| `verification` | `str` | statut de verification |
| `message` | `str` | resume humain |
| `correlation_id` | `str` | trace audit |

### `ErrorEnvelope`

| Champ | Type | Description |
| --- | --- | --- |
| `error_class` | `str` | categorie |
| `operation` | `str` | ex. `dns_upsert` |
| `target` | `str` | hostname ou zone |
| `message` | `str` | message lisible |
| `safe_next_step` | `str` | action recommande |

## 3. Validation hostname

Le systeme accepte:

- un FQDN complet, ex. `odoo-staging.ginutech.com`
- ou `label + root domain`

Regles:

| Regle | Obligatoire |
| --- | --- |
| trim espaces | oui |
| lowercase interne | oui |
| suppression trailing dot | oui |
| label non vide | oui |
| pas de segment vide | oui |
| pas de `-` en debut/fin de label | oui |
| domaine racine connu pour mutations | oui |

## 4. Validation IP et TTL

### IPv4

- un `A` record n'accepte qu'une IPv4 valide
- toute IPv6 est refusee en V1 avec message orientant vers le futur support `AAAA`

### TTL

| Valeur | Usage |
| --- | --- |
| `60-120` | tests agressifs |
| `300` | staging / deploiement rapide |
| `900` | transition moderee |
| `3600` | production plus stable |

Decision:

- TTL par defaut `300`
- TTL minimal accepte `60`
- TTL maximal accepte `86400`

## 5. Denylist de labels reserves

Liste par defaut:

- `www`
- `mail`
- `ftp`
- `cpanel`
- `webmail`
- `autodiscover`

Politique:

- refuse en mode normal
- contournable uniquement par configuration explicite, pas par `--force`

## 6. Politique DNS d'upsert

| Etat detecte | Action |
| --- | --- |
| aucun `A` record | `create` |
| un seul `A`, IP differente | `update` |
| un seul `A`, meme IP et meme TTL | `no-op` |
| un seul `A`, meme IP et TTL different | `update` |
| plusieurs `A` records | `refuse` par defaut |

## 7. Politique anti-ambiguite

Si plusieurs `A` records existent:

- afficher les records trouves
- refuser par defaut
- exiger `--force`
- redemander une confirmation explicite hors mode `--yes`

## 8. Contrat de recherche

### `dns search`

Retourne une liste d'objets:

| Champ | Description |
| --- | --- |
| `category` | `dns_records`, `hosted_subdomains`, `available` |
| `hostname` | hostname concerne |
| `record_type` | ex. `A` |
| `value` | valeur DNS si presente |
| `managed_by_cpanel` | vrai si objet hosted |

### `domains search`

Retourne des `DomainDescriptor`.

### `subdomains search`

Retourne des `SubdomainDescriptor`.

## 9. Contrat de verification DNS

Statuts normalises:

- `skipped`
- `accepted_pending_visibility`
- `resolved_matches_target`
- `resolved_mismatch`
- `lookup_failed`
