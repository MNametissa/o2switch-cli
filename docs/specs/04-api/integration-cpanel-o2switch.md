# Integration cPanel et o2switch

## 1. Sources d'authentification

Le client utilise:

- hostname cPanel, par exemple `saule.o2switch.net`
- username cPanel
- API token cPanel

## 2. Variables d'environnement

Les variables standardisees pour `o2switch-cli` sont:

```bash
O2SWITCH_CLI_CPANEL_HOST=saule.o2switch.net
O2SWITCH_CLI_CPANEL_USER=mon_user
O2SWITCH_CLI_CPANEL_TOKEN=mon_token
```

## 3. Sources de configuration supportees

| Source | Priorite |
| --- | --- |
| variables d'environnement | P1 |
| fichier local | P1 |
| prompt interactif ponctuel | P2 |

Ordre de resolution recommande:

1. options CLI explicites
2. fichier de config
3. variables d'environnement
4. prompt interactif si autorise

## 4. Strategie d'auth HTTP

Le client HTTP doit utiliser l'entete cPanel token auth et ne jamais logger le token brut.

Contraintes:

- timeout court et configurable
- user-agent explicite `o2switch-cli/<version>`
- TLS obligatoire

## 5. Endpoints principaux

| Besoin | Endpoint | Usage |
| --- | --- | --- |
| lister les domaines du compte | `DomainInfo/list_domains` | recherche domaine racine |
| creer un sous-domaine | `SubDomain/addsubdomain` | hosted mode |
| lire/modifier une zone DNS | `DNS/mass_edit_zone` | add/edit/remove records |
| catalogue DNS | module `DNS` | inspection et lookup interne |

## 6. Strategie UAPI / API 2

- V1 privilegie UAPI partout ou disponible
- les compatibilites historiques du module `SubDomain` en API 2 sont encapsulees derriere `cpanel_client`
- toute detection de fallback est tracee en log de debug, jamais exposee comme detail technique bloquant a l'utilisateur final

## 7. Contrats de service cPanel

### `list_domains()`

Retourne:

- main domain
- addon domains
- parked domains
- sous-domaines si exposes par l'API du compte

### `get_zone_state(root_domain)`

Retourne:

- la liste des records de zone
- les indexes ou identifiants necessaires a une mutation
- les metadonnees de serial/version si exposees

### `find_records(fqdn, record_type="A")`

Retourne:

- la liste des records correspondant exactement au hostname normalise

### `upsert_a_record(fqdn, ip, ttl)`

Planifie puis applique une decision:

- `create`
- `update`
- `no-op`
- `refuse`

### `delete_a_record(fqdn, force=False)`

Decision:

- supprimer si univoque
- refuser si ambigu sans `force`

### `create_subdomain(root_domain, label, docroot=None)`

- verifie que `root_domain` appartient au compte
- cree l'objet sous-domaine cPanel
- retourne le FQDN, le docroot final et le statut API

### `search_subdomains(term)`

- combine `DomainInfo/list_domains` et les sources `SubDomain` si necessaire

### `delete_subdomain(fqdn)`

Strategie figee:

- essayer le chemin UAPI disponible pour le compte
- sinon fallback API 2 si expose
- si aucun endpoint de suppression n'est disponible, retourner `not_supported` sans toucher au DNS

## 8. Politique de verification d'integration

Chaque appel API doit etre transforme en erreur applicative stable:

| Type de panne | Traduction applicative |
| --- | --- |
| 401/403 | `auth` ou `permission` |
| 404 domaine/zone | `not_found` |
| reponse cPanel incoherente | `transport` |
| mutation acceptee mais non visible | `verification` |

## 9. References documentaires a conserver

- o2switch: creation et usage des API tokens cPanel
- cPanel: `DomainInfo/list_domains`
- cPanel: `SubDomain/addsubdomain`
- cPanel: `DNS/mass_edit_zone`
- cPanel: gestion des API tokens
- cPanel API 2: module `SubDomain`
