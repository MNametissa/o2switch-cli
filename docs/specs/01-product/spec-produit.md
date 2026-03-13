# Spec produit

## 1. Positionnement

`o2switch-cli` est un CLI interactif oriente operations DevOps et hebergement mutualise cPanel.

Deux styles d'usage doivent coexister:

| Style | But |
| --- | --- |
| interactif | usage humain quotidien |
| command mode | automatisation, scripts, CI/CD |

Exemples conceptuels:

```bash
o2switch-cli
o2switch-cli interactive
o2switch-cli dns upsert --host odoo-staging.ginutech.com --ip 203.0.113.25
o2switch-cli subdomains create --root ginutech.com --label odoo-staging
```

## 2. Priorites fonctionnelles

| Usage | Priorite |
| --- | --- |
| rechercher un domaine racine disponible | P1 |
| rechercher un hostname existant | P1 |
| creer ou modifier un `A` record rapidement | P1 |
| supprimer un `A` record proprement | P1 |
| verifier l'etat DNS apres mutation | P1 |
| mode dry-run | P1 |
| creer un vrai sous-domaine cPanel | P2 |
| supprimer un vrai sous-domaine cPanel | P2 |

## 3. Mode metier A - DNS Fast Path

### But

Creer ou modifier uniquement un `A` record.

### Cas cible

```text
odoo-staging.ginutech.com -> 203.0.113.25
```

### Resultat attendu

- le hostname existe en DNS
- il pointe vers l'IPv4 cible
- l'outil retourne un statut final intelligible

### Workflow detaille

| Etape | Description |
| --- | --- |
| 1 | parser le hostname |
| 2 | extraire la zone candidate |
| 3 | verifier que le domaine existe dans le compte |
| 4 | lire l'etat de la zone DNS |
| 5 | rechercher les records du hostname |
| 6 | decider `create`, `update`, `no-op` ou `refuse` |
| 7 | executer la mutation DNS |
| 8 | verifier la reponse API |
| 9 | lancer un lookup DNS si demande |
| 10 | afficher le recapitulatif final |

### Contrat de sortie

| Champ | Exemple |
| --- | --- |
| `mode` | `dns-only` |
| `hostname` | `odoo-staging.ginutech.com` |
| `zone` | `ginutech.com` |
| `action` | `created` |
| `old_value` | `null` |
| `new_value` | `203.0.113.25` |
| `ttl` | `300` |
| `verification` | `accepted_pending_visibility` |

## 4. Mode metier B - Hosted Subdomain + DNS

### But

Creer:

1. le sous-domaine cPanel
2. puis son record DNS

### Resultat attendu

- le domaine parent existe dans le compte
- le sous-domaine cPanel est cree
- le DNS est aligne avec l'IP souhaitee

### Workflow detaille

| Etape | Description |
| --- | --- |
| 1 | verifier que le root domain existe |
| 2 | valider le label |
| 3 | verifier que le sous-domaine n'existe pas deja |
| 4 | appeler `SubDomain/addsubdomain` |
| 5 | relire la zone DNS |
| 6 | upsert le `A` record |
| 7 | retourner le statut combine |

## 5. User stories

### DNS-first

- En tant qu'operateur, je veux pointer vite un hostname vers un VPS pour exposer un service.
- En tant que pipeline, je veux pouvoir relancer un upsert sans casser un record deja conforme.
- En tant que support, je veux verifier la resolution DNS apres une mutation.

### Hosted + DNS

- En tant qu'operateur cPanel, je veux creer un vrai sous-domaine gere par l'hebergement puis l'aligner avec le DNS.
- En tant qu'administrateur, je veux rechercher les sous-domaines connus par cPanel.

## 6. Acceptance criteria produit

### DNS P1

- `o2switch-cli dns upsert` refuse toute mutation si la zone n'appartient pas au compte
- `o2switch-cli dns upsert` retourne `no-op` si l'etat voulu existe deja
- `o2switch-cli dns delete` refuse si plusieurs `A` records existent sans `--force`
- `o2switch-cli dns verify` distingue l'etat API et la visibilite DNS resolue

### Hosted P2

- `o2switch-cli subdomains create` verifie l'existence du domaine parent avant creation
- l'option `--ip` declenche un alignement DNS dans le meme workflow
- toute suppression hosted reste explicite et confirmee

## 7. Resume ultra-operationnel

| Element | Decision |
| --- | --- |
| nom de l'outil | `o2switch-cli` |
| interface | CLI interactif + command mode |
| cas principal | creer vite un `A` record vers un VPS |
| API principale | cPanel UAPI |
| listing domaines | `DomainInfo/list_domains` |
| creation hosted | `SubDomain/addsubdomain` |
| mutation DNS | `DNS/mass_edit_zone` |
| auth | token cPanel via o2switch |
| langage recommande | Python |
| V1 | DNS-first |
| V1.1 | support hosted |
