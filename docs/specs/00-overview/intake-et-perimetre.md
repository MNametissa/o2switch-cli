# Intake et perimetre

## 1. Resume d'intake

`o2switch-cli` est un outil CLI interactif pour gerer a distance, depuis un compte `o2switch/cPanel`, les domaines disponibles, les sous-domaines cPanel et les enregistrements DNS, avec priorite absolue au workflow de creation rapide d'un hostname pointant vers une IPv4 de VPS.

Exemple cible:

```text
odoo-staging.ginutech.com -> 203.0.113.25
```

## 2. Objectif produit

Le produit doit permettre:

- de trouver le bon domaine racine disponible sur le compte
- de verifier l'etat DNS d'un hostname
- de creer ou mettre a jour rapidement un `A` record
- de supprimer proprement un `A` record quand il est univoque
- de supporter ensuite les vrais sous-domaines cPanel
- d'etre utilisable a la fois par un humain et par un pipeline

## 3. Philosophie produit

Le projet distingue explicitement deux intentions metier:

| Intention metier | Strategie |
| --- | --- |
| exposer vite un hostname vers un VPS | `DNS-first` via `A` record uniquement |
| creer un vrai sous-domaine gere par cPanel | `Hosted Subdomain + DNS` |

Cette distinction est obligatoire dans toute l'UX et dans tout le code, car la couche "objet sous-domaine cPanel" et la couche "zone DNS" sont distinctes.

## 4. Scope

### V1

- auth par token cPanel
- listing et recherche des domaines du compte
- recherche de hostname dans les zones DNS
- `dns upsert` pour `A`
- `dns delete` pour `A`
- verification DNS apres mutation
- mode interactif
- `--dry-run`
- sortie JSON optionnelle
- audit structure

### V1.1

- creation de sous-domaine cPanel
- recherche de sous-domaines cPanel
- alignement DNS lors de la creation hosted

### V2

- suppression hosted plus robuste
- `AAAA`
- `CNAME`
- wildcard workflows
- templates de deploiement

## 5. Non-goals

Les points suivants sont hors scope initial:

- gestion complete de certificats TLS
- orchestration de deploiement applicatif sur VPS
- edition generale de tous les types DNS en V1
- support multi-provider DNS
- UI graphique web

## 6. Hypotheses retenues

- le compte o2switch cible expose un token cPanel valide
- le domaine racine existe deja dans le compte pour toute mutation
- la zone DNS est hebergee et modifiable depuis cPanel pour les domaines cibles
- le binaire sera implemente en Python 3.11+
- le package interne s'appellera `o2switch_cli`
- la verification DNS externe peut etre eventual-consistent et ne doit pas invalider une mutation acceptee par cPanel

## 7. Questions ouvertes

Aucune question bloquante n'est laissee ouverte dans ce pack. Les choix suivants figent les points ambigus du brief:

- la suppression hosted est specifiee des maintenant, mais son implementation est deferree tant que l'endpoint disponible sur le compte cible n'est pas verifie
- le prefixe d'environnement est `O2SWITCH_CLI_` et non un alias de l'ancien nom
- le mode par defaut reste securise: aucune mutation sans resume et confirmation, sauf si l'utilisateur force explicitement le mode non interactif

## 8. Personas et usages

| Persona | Attente principale |
| --- | --- |
| DevOps / administrateur | declarer vite un hostname vers un VPS |
| developpeur backend | preparer staging/review apps |
| operateur support | verifier un record ou une configuration DNS |
| pipeline CI/CD | executer des mutations idempotentes en mode commande |

## 9. Criteres de succes

- un operateur peut creer ou mettre a jour un `A` record en une commande
- un pipeline peut relancer la meme commande sans effet de bord
- les erreurs sont classees, actionnables et sans fuite de secret
- les journaux permettent d'auditer chaque mutation
- l'architecture permet d'ajouter `AAAA` et `CNAME` sans refonte majeure

## 10. Registre de risques

| Risque | Impact | Mitigation |
| --- | --- | --- |
| endpoint DNS cPanel varie selon le compte | mutation impossible | isoler l'integration dans `cpanel_client` et journaliser la capacite detectee |
| plusieurs `A` records pour le meme hostname | ambiguite operateur | refuser par defaut et imposer `--force` |
| domaine hors scope du compte | mutation erronnee | verifier via `DomainInfo/list_domains` avant toute action |
| token invalide ou trop permissif | panne ou exposition | validation early, jamais logger le token, documenter la rotation |
| propagation DNS lente | faux negatif en verification | separer `accepted_by_cpanel` et `visible_in_dns` dans le resultat |
