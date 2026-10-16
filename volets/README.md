# Volets selon le soleil

`volets_soleil.yaml` : à instancier **une fois par façade** (une orientation =
une instance). Inspiré de l'article de
[domo.rem81](http://domo.rem81.com/index.php/2025/07/07/home-assistant-suivi-des-volets-selon-lazimut-solaire-et-la-radiation-ete/).

## Fonctionnement

Toutes les 10 minutes entre le lever et le coucher du soleil, l'automatisation
calcule une position cible pour les volets de la façade (100 = ouvert,
0 = fermé) :

| Situation | Cible |
| --- | --- |
| Soleil face aux fenêtres **et** température au-dessus du seuil de chaleur | 0 (fermé) |
| Soleil face aux fenêtres, au-dessus de l'élévation minimale, **et** ensoleillement au-dessus du seuil | Fermeture progressive selon la hauteur du soleil |
| Soleil hors de la façade **et** il fait chaud | Aucune action : les volets restent où ils sont |
| Capteur d'ensoleillement indisponible (et pas de chaleur face au soleil) | Aucune action |
| Tous les autres cas : soleil hors de la façade, ciel couvert, soleil trop bas | 100 (ouvert) |

« Face aux fenêtres » : l'écart entre l'azimut du soleil (`sun.sun`) et
l'orientation de la façade est inférieur ou égal à l'angle d'exposition. Le
calcul gère le passage par le nord : une façade orientée à 0° avec un angle de
60° suit le soleil de 300° à 60°.

Fermeture progressive : la position est
`100 − (élévation − élévation min) / (90 − élévation min) × 100`. Avec une
élévation minimale de 10°, un soleil à 50° donne 50 %, à 65° (midi en été en
France) environ 31 %.

Un volet n'est déplacé que si sa position actuelle diffère de la cible d'au
moins l'**écart minimal** (10 % par défaut). Un volet en cours de mouvement est
ignoré jusqu'au passage suivant.

## Capteurs nécessaires

- **`sun.sun`** : intégration Soleil, présente par défaut.
- **Un capteur d'ensoleillement**, un seul pour toute la maison : la façade est
  prise en compte par l'orientation, pas par le capteur. N'importe quelle
  unité convient, seul le seuil change :

  | Source | Unité | Seuil de départ |
  | --- | --- | --- |
  | Station météo avec capteur solaire | W/m² | 300 |
  | Capteur de luminosité extérieur | lux | 30 000 |
  | Open-Meteo, capteur REST ci-dessous | W/m² | 300 |
  | Couverture nuageuse Met.no inversée, ci-dessous | % | 60 |

- **Un capteur de température extérieure** (optionnel), par exemple le module
  extérieur d'une station Netatmo. Sans lui, pas de fermeture complète par
  chaleur. Avec plusieurs capteurs, la valeur la plus haute est retenue.

### Option gratuite 1 : radiation estimée par Open-Meteo

Dans `configuration.yaml`, sans clé d'API :

```yaml
rest:
  - resource_template: >-
      https://api.open-meteo.com/v1/forecast?latitude={{ state_attr('zone.home','latitude') }}&longitude={{ state_attr('zone.home','longitude') }}&current=shortwave_radiation
    scan_interval: 600
    sensor:
      - name: Radiation solaire
        unique_id: radiation_solaire_open_meteo
        value_template: "{{ value_json.current.shortwave_radiation }}"
        unit_of_measurement: "W/m²"
        device_class: irradiance
        state_class: measurement
```

Valeur modélisée, rafraîchie environ toutes les 15 minutes : elle distingue une
journée dégagée d'une journée couverte, pas un nuage qui passe.

### Option gratuite 2 : couverture nuageuse Met.no

L'attribut `cloud_coverage` de l'entité météo va de 0 à 100 % : plus il est
haut, moins il y a de soleil. Le blueprint attendant l'inverse, passer par un
capteur template (remplacer `weather.forecast_maison` par l'entité météo) :

```yaml
template:
  - sensor:
      - name: Ensoleillement estimé
        unit_of_measurement: "%"
        state: "{{ 100 - (state_attr('weather.forecast_maison', 'cloud_coverage') | float(100)) }}"
```

## Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Volets | Aucun | Doivent accepter `cover.set_cover_position`. |
| Orientation de la façade | 180° | 0 = nord, 90 = est, 180 = sud, 270 = ouest. |
| Angle d'exposition | 60° | Demi-ouverture du secteur où le soleil est jugé face aux fenêtres. |
| Élévation minimale | 10° | Sous cette hauteur, soleil considéré comme masqué. |
| Capteur d'ensoleillement | Aucun | Voir ci-dessus. |
| Seuil d'ensoleillement | 300 | Dans l'unité du capteur. |
| Marge de réouverture | 20 % | Une fois les volets baissés, il faut repasser sous seuil × (1 − marge) pour rouvrir. |
| Capteur de température extérieure | Aucun | Optionnel. |
| Seuil de chaleur | 28 °C | Fermeture complète face au soleil au-dessus. |
| Écart minimal de position | 10 % | Évite les micro-mouvements. |
| Pause après une modification manuelle | 2 h | 0 = ne pas respecter les modifications manuelles. |
| Entités de blocage | Aucun | Optionnel. Une entité à « on » suspend l'automatisation. |

## Modifications manuelles

Aucun helper n'est à créer : la pause est portée par l'exécution de
l'automatisation.

- Une minute après qu'un volet s'est immobilisé, sa position est comparée à la
  cible du moment. Si l'écart dépasse l'écart minimal, ou si l'automatisation ne
  voulait aucun mouvement, c'est une intervention manuelle : l'automatisation
  attend la durée de pause avant de reprendre.
- La pause vaut pour **tous les volets de l'instance**, pas seulement celui qui
  a bougé. Un nouveau mouvement manuel pendant la pause ne la prolonge pas.
- À la fin de la pause, le passage de suivi resté en attente s'exécute aussitôt
  et réapplique la cible.
- Un redémarrage de Home Assistant pendant une pause l'interrompt : le suivi
  reprend au passage suivant.

## Limites connues

- **Ouverture au lever du soleil** : dès le lever, la cible est « ouvert » tant
  que le soleil n'est pas gênant. Pour garder les volets fermés le matin
  (chambre, week-end), utiliser une entité de blocage. Après le coucher du
  soleil, l'automatisation ne fait plus rien : la fermeture du soir relève
  d'une autre automatisation.
- **Volets à position approximative** : si un volet s'arrête loin de la
  position demandée (plus que l'écart minimal), son arrivée est prise pour une
  intervention manuelle et déclenche une pause. Augmenter l'écart minimal, ou
  mettre la pause à 0.
- **Fermeture progressive simplifiée** : elle ne dépend que de la hauteur du
  soleil, pas de l'angle sous lequel il frappe la façade. Un soleil bas, rasant
  et de face entre profondément dans la pièce mais donne une fermeture faible.
  Monter l'élévation minimale si cela gêne.
- Le détail du calcul (azimut, cible, positions) est visible dans les traces de
  l'automatisation.
