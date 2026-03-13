# Securite, audit et erreurs

## 1. Exigences de securite

| Exigence | Statut |
| --- | --- |
| token jamais logge | obligatoire |
| separation staging/prod recommandee | recommandee |
| actions destructives confirmees | obligatoire |
| domaine hors scope refuse | obligatoire |
| `force` explicite pour cas ambigus | obligatoire |

## 2. Regles d'exploitation

- aucune mutation sans verification du domaine racine
- aucun secret en sortie console, JSON ou logs
- aucune suppression DNS si l'outil ne peut pas identifier un record univoque
- la verification DNS externe ne doit jamais masquer l'etat d'acceptation par cPanel

## 3. Journalisation structuree

Chaque mutation produit un log structure.

| Champ | Description |
| --- | --- |
| `timestamp` | date/heure UTC |
| `actor` | utilisateur ou systeme |
| `mode` | `dns-only` / `hosted+dns` |
| `operation` | `create` / `update` / `delete` |
| `hostname` | cible |
| `zone` | zone concernee |
| `before` | etat precedent |
| `after` | etat final |
| `ttl` | TTL final |
| `force_used` | bool |
| `result` | `success` / `warning` / `failure` |
| `correlation_id` | trace pipeline |

## 4. Erreurs applicatives

| Classe | Exemple |
| --- | --- |
| `validation` | hostname invalide |
| `auth` | token absent ou invalide |
| `permission` | acces refuse par cPanel |
| `not_found` | domaine ou zone absente |
| `conflict` | plusieurs `A` records |
| `transport` | endpoint inaccessible |
| `verification` | mutation acceptee mais non visible |
| `not_supported` | endpoint hosted indisponible |

## 5. Format d'erreur standard

```json
{
  "error_class": "conflict",
  "operation": "dns_delete",
  "target": "odoo-staging.ginutech.com",
  "message": "Multiple A records found for hostname.",
  "safe_next_step": "Review the conflicting records and rerun with --force only if the target is confirmed."
}
```

## 6. Idempotence

Le CLI doit etre strictement idempotent.

Exemple:

- si `odoo-staging.ginutech.com` pointe deja vers `203.0.113.25`
- et que le TTL voulu est deja conforme
- l'outil retourne `no-op`
- aucune mutation n'est envoyee a cPanel

## 7. Verification post-mutation

La verification suit deux niveaux:

1. verification de l'acceptation par l'API cPanel
2. verification DNS externe via resolver si active

Le resultat doit exposer ces deux realites sans les confondre.

## 8. Politique MFA / OTP

L'architecture d'authentification doit rester compatible avec un environnement cPanel protege par MFA au niveau console. Le CLI repose sur les API tokens et n'essaie pas de reproduire un login interactif MFA.

## 9. Registre de risques operationnels

| Risque | Impact | Reponse |
| --- | --- | --- |
| rotation du token oubliee | indisponibilite CLI | test `config doctor` et message d'action |
| zone DNS non hebergee chez cPanel | echec mutation | detection early et erreur `not_found` ou `not_supported` |
| suppression humaine erronee | outage | confirmations et `dry-run` |
| verification externe faussement negative | confusion | statuts distincts API/DNS |
