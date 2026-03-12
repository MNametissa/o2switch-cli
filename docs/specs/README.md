# Pack de specs o2switch-cli

Ce dossier transforme le brief initial en pack de specifications executable pour `o2switch-cli`.

Les conventions retenues sont:

- nom produit et binaire CLI: `o2switch-cli`
- nom du package Python: `o2switch_cli`
- prefixe des variables d'environnement: `O2SWITCH_CLI_`

## Source of truth

Les documents ci-dessous sont la reference de travail pour l'implementation.

| Domaine | Fichier | Role |
| --- | --- | --- |
| cadrage | `00-overview/intake-et-perimetre.md` | objectif, scope, hypothese, non-goals |
| produit | `01-product/spec-produit.md` | usages, priorites, workflows metier |
| architecture | `02-architecture/architecture-technique.md` | modules, stack, organisation de code |
| CLI | `03-cli/spec-cli-et-ux.md` | arborescence de commandes, UX interactive, JSON |
| API | `04-api/integration-cpanel-o2switch.md` | auth, endpoints, contrats d'integration |
| references | `04-api/references.md` | sources o2switch et cPanel a conserver |
| donnees | `05-data/modeles-et-contrats.md` | modeles, validations, matrices de champs |
| operations | `06-operations/securite-audit-erreurs.md` | securite, audit, erreurs, idempotence |
| delivery | `07-delivery/tests-milestones-et-backlog.md` | backlog, acceptance criteria, couverture de tests |
| decisions | `07-delivery/decision-log.md` | decisions de cadrage figees |

## Couverture du brief initial

Le brief fourni est entierement remappe dans ce pack:

- objectif produit et philosophie DNS-first
- positionnement CLI interactif et mode commande
- architecture fonctionnelle interne
- modes metier DNS-only et hosted+DNS
- perimetre API cPanel UAPI / API 2
- authentification et stockage des credentials
- UX, recherche, selection, confirmation
- validations hostname, IPv4, TTL et denylist
- politiques DNS d'upsert, delete et anti-ambiguite
- workflows detailles et contrats de resultat
- gestion d'erreurs, audit, securite et idempotence
- stack Python recommandee, backlog V1/V1.1/V2

## Ordre de lecture recommande

1. `00-overview/intake-et-perimetre.md`
2. `01-product/spec-produit.md`
3. `02-architecture/architecture-technique.md`
4. `04-api/integration-cpanel-o2switch.md`
5. `05-data/modeles-et-contrats.md`
6. `03-cli/spec-cli-et-ux.md`
7. `06-operations/securite-audit-erreurs.md`
8. `07-delivery/tests-milestones-et-backlog.md`
