# Alerte sécheresse VigiEau

`vigieau_alerte.yaml` — à instancier **une fois par capteur suivi**.

Notification à chaque changement du niveau de restriction d'eau publié par
[VigiEau](https://vigieau.gouv.fr/), le service du ministère de la Transition
écologique qui agrège les arrêtés préfectoraux sécheresse.

## Architecture

Le besoin se découpe en deux briques, parce qu'**aucun blueprint Home Assistant
ne peut émettre une requête HTTP** : les domaines blueprintables (`automation`,
`script`, `template`) n'ont pas d'action de récupération réseau.

| Brique | Où | Rôle |
| --- | --- | --- |
| Capteur REST | `configuration.yaml` | Interroge l'API VigiEau, expose le niveau |
| Blueprint | ce dossier | Observe le capteur, notifie les changements |

Le blueprint prend le capteur en **entrée** : il reste agnostique de sa
provenance et fonctionne aussi avec une intégration tierce
(par exemple [`kamaradclimber/vigieau`](https://github.com/kamaradclimber/vigieau)
via HACS), à condition que les états correspondent à l'échelle ci-dessous.

## Étape 1 — le capteur REST

L'API accepte soit un code INSEE (`commune`), soit des coordonnées
(`lat` / `lon`). **Utiliser les coordonnées** : Home Assistant connaît déjà
l'adresse de la maison, elle est exposée par `zone.home`. Rien à saisir, rien de
nominatif dans le YAML, et le cas des communes ambiguës disparaît (voir plus
bas).

Dans `configuration.yaml` (ou un fichier de `packages/`) :

```yaml
rest:
  - resource_template: >-
      https://api.vigieau.gouv.fr/api/zones?profil=particulier&lat={{ state_attr('zone.home', 'latitude') }}&lon={{ state_attr('zone.home', 'longitude') }}
    scan_interval: 21600     # 6 h : le niveau bouge quelques fois par saison
    timeout: 30
    sensor:
      - name: Sécheresse
        unique_id: vigieau_niveau
        icon: mdi:water-alert
        json_attributes_path: "$.[0]"
        json_attributes:
          - nom
          - departement
          - arrete
        value_template: >-
          {% if value_json is mapping %}
            unknown
          {% else %}
            {% set echelle = ['vigilance', 'alerte', 'alerte_renforcee', 'crise'] %}
            {% set ns = namespace(rang=-1) %}
            {% for z in value_json %}
              {% set n = z.niveauGravite | default('') %}
              {% if n in echelle and echelle.index(n) > ns.rang %}
                {% set ns.rang = echelle.index(n) %}
              {% endif %}
            {% endfor %}
            {{ echelle[ns.rang] if ns.rang >= 0 else 'pas_de_restriction' }}
          {% endif %}
```

`resource_template` est réévalué à chaque interrogation : déplacer la maison
dans **Paramètres → Système → Général** suffit à changer la zone suivie.

Recharger via **Outils de développement → YAML → Entités REST**, ou redémarrer.

Le capteur produit `sensor.secheresse`. Son état est la valeur brute de l'API,
pas un libellé : c'est ce que le blueprint et les templates comparent. La mise
en forme lisible se fait à l'affichage (voir plus bas).

> [!tip]
> Avec un `scan_interval` de 6 h, si `zone.home` n'est pas encore chargé au
> moment où la plateforme REST démarre, le capteur reste vide jusqu'à la
> prochaine interrogation. Une automatisation de rattrapage coûte quatre lignes :
>
> ```yaml
> automation:
>   - alias: Rafraîchir la sécheresse au démarrage
>     triggers:
>       - trigger: homeassistant
>         event: start
>     actions:
>       - delay: "00:01:00"
>       - action: homeassistant.update_entity
>         target:
>           entity_id: sensor.secheresse
> ```

### Variante : code INSEE en dur

Si la maison n'est pas le point à suivre (résidence secondaire, jardin partagé,
maison des parents), passer par le code INSEE de la commune — 5 caractères,
différent du code postal :

```bash
curl -s "https://geo.api.gouv.fr/communes?nom=Montpellier&fields=code,nom"
```

Puis remplacer `resource_template` par :

```yaml
    resource: https://api.vigieau.gouv.fr/api/zones
    params:
      commune: "34172"
      profil: particulier
```

> [!warning]
> C'est cette variante qui expose au cas ambigu : certaines communes renvoient
> une **erreur HTTP 409** — `La commune comporte plusieurs zones d'alerte de même
> type` (Nantes, `44109`, par exemple). Le code INSEE ne suffit alors pas à
> désigner une zone, et il faut de toute façon repasser aux coordonnées.

Pour retrouver le code INSEE d'une adresse quelconque, la Base Adresse Nationale
fait le géocodage inverse et renvoie le `citycode` :

```bash
curl -s "https://api-adresse.data.gouv.fr/reverse/?lat=47.2184&lon=-1.5536" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['features'][0]['properties']['citycode'])"
```

### Ce que renvoie l'API

Pas de clé, pas de quota annoncé. La réponse est une **liste de trois zones**
pour un même point :

| `type` | Ressource |
| --- | --- |
| `SUP` | Eaux superficielles (rivières, plans d'eau) |
| `SOU` | Eaux souterraines (nappes) |
| `AEP` | Alimentation en eau potable |

Chacune porte un `niveauGravite` parmi `vigilance`, `alerte`,
`alerte_renforcee`, `crise`. Le `value_template` ci-dessus retient **le plus
sévère des trois** — c'est celui qui contraint réellement les usages
domestiques. Pour ne suivre qu'une ressource, remplacer la boucle par un
`selectattr('type', 'eq', 'AEP')`.

Une **liste vide** signifie qu'aucun arrêté n'est en vigueur : le capteur vaut
alors `pas_de_restriction`.

Home Assistant passe le corps de la réponse au template **même sur un code HTTP
d'erreur**. La branche `value_json is mapping` du `value_template` intercepte ce
cas et force `unknown`, plutôt que de laisser croire à une levée des
restrictions ; le blueprint ignore cet état.

Le `json_attributes_path: "$.[0]"` prend le nom de zone et l'arrêté de la
**première** zone renvoyée. En pratique un même arrêté préfectoral couvre les
trois types pour un point donné ; si ce n'est pas le cas chez toi, le nom de zone
affiché peut ne pas être celui du niveau retenu. Le payload complet fait ~13 Ko à
cause de la liste des usages : ne pas l'exposer intégralement en attributs, et
exclure le capteur du recorder si l'historique n'a pas d'intérêt.

## Étape 2 — le blueprint

Le déclencheur est le changement d'état du capteur, en excluant `unknown` et
`unavailable` des deux côtés : un redémarrage de Home Assistant ou une coupure
de l'API ne produit donc aucune notification.

Le sens du changement est déduit du rang sur l'échelle :

```
pas_de_restriction < vigilance < alerte < alerte_renforcee < crise
```

## Variables disponibles dans les actions de notification

| Variable | Type | Contenu |
| --- | --- | --- |
| `message` | texte | Message prêt à l'emploi, adapté au sens du changement. |
| `titre` | texte | `Sécheresse : Alerte renforcée`, ou `Fin des restrictions d'eau`. |
| `sens` | texte | `aggravation` ou `levee`. |
| `niveau` | texte | Libellé du nouveau niveau. |
| `niveau_precedent` | texte | Libellé du niveau quitté. |
| `etat` / `etat_precedent` | texte | Valeurs brutes correspondantes. |
| `zone` | texte | Nom de la zone d'alerte, vide si le capteur ne l'expose pas. |
| `lien_arrete` | texte | URL du PDF de l'arrêté, `https://vigieau.gouv.fr/` à défaut. |

Exemple d'action à saisir dans le champ *Notification* :

```yaml
- action: notify.mobile_app_telephone
  data:
    title: "{{ titre }}"
    message: "{{ message }}"
    data:
      url: "{{ lien_arrete }}"
      push:
        interruption-level: "{{ 'time-sensitive' if sens == 'aggravation' else 'active' }}"
```

## Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Capteur de niveau | — | Le capteur REST créé à l'étape 1. |
| Niveau minimum notifié | Vigilance | Ignore les changements restant sous ce niveau. |
| Notifier les allègements | activé | Décocher pour ne recevoir que les durcissements. |

Le niveau minimum est comparé au **plus sévère des deux** niveaux du changement.
Avec un seuil sur *Alerte*, le passage `alerte → vigilance` est donc bien
notifié : c'est l'information qui dit qu'on peut de nouveau arroser.

## Le widget

L'état brut (`alerte_renforcee`) n'est pas fait pour être lu. Carte Markdown,
100 % native, à coller dans le tableau de bord :

```yaml
type: markdown
content: >-
  {% set n = states('sensor.secheresse') %}
  {% set v = {
    'pas_de_restriction': ['✅', 'Aucune restriction'],
    'vigilance': ['🟡', 'Vigilance'],
    'alerte': ['🟠', 'Alerte'],
    'alerte_renforcee': ['🔴', 'Alerte renforcée'],
    'crise': ['⛔', 'Crise']
  }.get(n, ['❔', 'Niveau inconnu']) %}
  ## {{ v[0] }} {{ v[1] }}
  {% if state_attr('sensor.secheresse', 'nom') %}
  {{ state_attr('sensor.secheresse', 'nom') }}
  {% endif %}
  {% set a = state_attr('sensor.secheresse', 'arrete') %}
  {% if a and a.cheminFichier %}
  [Arrêté préfectoral]({{ a.cheminFichier }})
  {% endif %}
```

Pour une carte Tile plutôt qu'un bloc Markdown, il faut un capteur `template:`
intermédiaire — la carte Tile ne rend pas de template dans `name` ni dans
`icon`, mais elle affiche l'icône dynamique d'un capteur :

```yaml
template:
  - sensor:
      - name: Niveau sécheresse
        state: >-
          {{ {'pas_de_restriction': 'Aucune restriction',
              'vigilance': 'Vigilance',
              'alerte': 'Alerte',
              'alerte_renforcee': 'Alerte renforcée',
              'crise': 'Crise'}.get(states('sensor.secheresse'), 'Inconnu') }}
        icon: >-
          {{ {'pas_de_restriction': 'mdi:water-check',
              'vigilance': 'mdi:water-alert-outline',
              'alerte': 'mdi:water-alert',
              'alerte_renforcee': 'mdi:water-remove',
              'crise': 'mdi:water-off'}.get(states('sensor.secheresse'),
                                            'mdi:help-circle-outline') }}
```

La couleur de l'icône d'une carte Tile est statique en natif : la faire varier
avec le niveau demande une carte custom (`mushroom`, `card-mod`) via HACS.

## Notes

- Les niveaux VigiEau ne sont pas des recommandations mais des **arrêtés
  préfectoraux** : le contenu exact des restrictions figure dans le PDF, dont le
  lien est exposé en attribut.
- Le champ `profil` de l'API (`particulier`, `exploitation`, `collectivite`,
  `entreprise`) ne change pas le `niveauGravite`, seulement la liste des usages
  restreints renvoyée.
- `scan_interval: 21600` est déjà généreux pour une donnée qui évolue quelques
  fois par saison. Inutile de descendre plus bas sur une API publique gratuite.
- L'état est porté par le capteur, pas par l'automatisation : un redémarrage de
  Home Assistant ne fait rien perdre. Le seul effet de bord est que le premier
  relevé après redémarrage part de `unknown`, cas explicitement écarté par le
  déclencheur.
