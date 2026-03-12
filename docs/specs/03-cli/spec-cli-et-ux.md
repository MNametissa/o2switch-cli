# Spec CLI et UX

## 1. Entree principale

```text
o2switch-cli
├── DNS
│   ├── Rechercher un hostname
│   ├── Creer / mettre a jour un A record
│   ├── Supprimer un A record
│   └── Verifier la resolution DNS
├── Sous-domaines
│   ├── Rechercher
│   ├── Creer un sous-domaine cPanel
│   └── Supprimer
├── Domaines
│   ├── Lister les domaines du compte
│   └── Rechercher
└── Configuration
    ├── Tester l'acces API
    └── Afficher la config active
```

## 2. Arborescence de commandes

### Domaines

| Commande | Role |
| --- | --- |
| `o2switch-cli domains list` | liste les domaines du compte |
| `o2switch-cli domains search <term>` | recherche par substring |

### DNS

| Commande | Role |
| --- | --- |
| `o2switch-cli dns search <term>` | recherche hostname/record |
| `o2switch-cli dns upsert --host <fqdn> --ip <ipv4> [--ttl <n>]` | create/update `A` |
| `o2switch-cli dns delete --host <fqdn>` | supprime le `A` |
| `o2switch-cli dns verify --host <fqdn>` | verifie la resolution |

### Sous-domaines

| Commande | Role |
| --- | --- |
| `o2switch-cli subdomains search <term>` | recherche cote hosted |
| `o2switch-cli subdomains create --root <domain> --label <label> [--docroot <path>] [--ip <ipv4>]` | cree le sous-domaine + DNS optionnel |
| `o2switch-cli subdomains delete --fqdn <fqdn>` | suppression hosted |

### Mode interactif

```bash
o2switch-cli
o2switch-cli interactive
```

## 3. Options globales

Les commandes doivent partager un socle commun:

- `--json`
- `--dry-run`
- `--force`
- `--yes`
- `--verbose`
- `--no-verify`
- `--config <path>`

## 4. Principe UX

Le CLI ne mute jamais a l'aveugle.

Avant toute mutation, il affiche:

| Element | But |
| --- | --- |
| domaine racine selectionne | eviter le mauvais scope |
| hostname final normalise | eviter les erreurs de saisie |
| etat actuel detecte | savoir si create/update/no-op |
| action prevue | rendre le changement lisible |
| confirmation | eviter l'erreur operateur |

## 5. Recherche et selection

### Recherche de domaines

Source primaire: `DomainInfo/list_domains`

Resultat attendu:

| Champ | Description |
| --- | --- |
| `domain` | ex. `ginutech.com` |
| `type` | main / addon / parked |
| `eligible_for_subdomain_creation` | bool |
| `has_dns_zone` | bool |

### Recherche de hostnames

Le CLI doit chercher dans deux espaces:

| Espace | Signification |
| --- | --- |
| `hosted_subdomains` | objets cPanel existants |
| `dns_records` | hostnames definis dans la zone |

Resultat possible:

| Categorie | Exemple |
| --- | --- |
| `hosted_subdomains` | `app.ginutech.com` |
| `dns_records` | `odoo-staging.ginutech.com -> A 203.0.113.25` |
| `available` | hostname non trouve |

## 6. UX du dry-run

`--dry-run` doit:

- executer toutes les validations
- charger l'etat courant du domaine et de la zone
- produire un plan de mutation sans ecrire
- afficher la meme sortie de recapitulatif avec `result=dry_run`

## 7. Sortie machine JSON

La sortie JSON doit etre stable et versionnable.

Format minimal:

```json
{
  "operation": "dns_upsert",
  "mode": "dns-only",
  "target": "odoo-staging.ginutech.com",
  "zone": "ginutech.com",
  "planned_action": "update",
  "applied": true,
  "verification": "accepted_pending_visibility",
  "correlation_id": "..."
}
```

## 8. Codes de sortie

| Code | Signification |
| --- | --- |
| `0` | succes ou no-op |
| `2` | erreur de validation |
| `3` | erreur d'authentification |
| `4` | ressource non trouvee |
| `5` | conflit ou ambiguite |
| `6` | erreur transport/API |
| `7` | verification en warning |

## 9. Accessibilite et lisibilite terminal

- aucun tableau requis pour comprendre une erreur critique
- couleur optionnelle, jamais indispensable
- formats texte et JSON equivalemment complets
- confirmations explicites sur les actions destructives
