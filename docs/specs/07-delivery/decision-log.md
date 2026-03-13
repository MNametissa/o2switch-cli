# Decision log

Date de gel initial: `2026-03-12`

## Decisions figees

1. Le nom du projet, du binaire et du repository est `o2switch-cli`.
2. Le nom du package Python est `o2switch_cli`.
3. Le cas principal de V1 est `DNS-first`, pas la gestion hosted.
4. Le framework CLI retenu est `Typer`.
5. Le client HTTP retenu est `httpx`.
6. La validation applicative retenue est `pydantic`.
7. Le prefixe d'environnement retenu est `O2SWITCH_CLI_`.
8. Le TTL par defaut pour les `A` records est `300`.
9. Les labels reserves sont refuses par politique, pas contournables par `--force`.
10. Toute mutation doit produire un audit structure et une correlation id.
11. Toute ambiguite sur plusieurs `A` records produit un refus par defaut.
12. La verification DNS reste informative et distincte de l'acceptation par cPanel.
13. UAPI est la voie prioritaire; API 2 n'est qu'un fallback encapsule.
14. La suppression hosted doit retourner `not_supported` si aucun endpoint exploitable n'est detecte.

## Decisions de packaging

- le code applicatif vivra sous `o2switch_cli/`
- les specs vivent sous `docs/specs/`
- le README racine pointe vers ce pack comme source de verite

## Decisions de securite

- le token n'est jamais affiche, meme en `--verbose`
- les actions destructives exigent confirmation ou `--yes`
- le domaine doit appartenir au compte avant toute mutation

## Decisions de rollout

- commencer par la visibilite compte et DNS
- ajouter l'UX interactive apres stabilisation du coeur DNS
- n'ajouter hosted delete qu'apres verification de compatibilite cible
