# Rappel fenêtre restée ouverte

`fenetre_ouverte_rappel.yaml` — à instancier **une fois par logement**.

## Fonctionnement

Deux motifs de rappel, distingués par la variable `motif` :

- **`duree`** — une fenêtre est ouverte depuis plus longtemps que le délai
  configuré **et** la température extérieure est au niveau ou en dessous du
  seuil. Le rappel ne concerne que cette fenêtre.
- **`depart`** — une entité de présence passe à « absent ». Le rappel liste
  **toutes** les fenêtres encore ouvertes à cet instant, sans condition de
  température : partir en laissant une fenêtre ouverte se signale par tous les
  temps.

Le rappel est ensuite répété toutes les *N* minutes tant que les fenêtres
concernées restent ouvertes, dans la limite du nombre maximal de rappels.
L'attente s'interrompt immédiatement à la fermeture, et une notification de
fermeture facultative est alors envoyée.

`mode: parallel` : chaque fenêtre a son propre cycle de rappels, deux fenêtres
ouvertes en même temps donnent deux séries de notifications.

## Variables disponibles dans les actions de notification

| Variable | Type | Contenu |
| --- | --- | --- |
| `message` | texte | Message prêt à l'emploi, adapté au motif. |
| `titre` | texte | `Fenêtre ouverte` ou `Départ : fenêtre ouverte` |
| `motif` | texte | `duree` ou `depart` |
| `nombre` | entier | Nombre de fenêtres concernées par ce cycle. |
| `noms` | liste de textes | Noms conviviaux des fenêtres. |
| `cibles` | liste d'`entity_id` | Fenêtres suivies par ce cycle. |
| `temperature_ext` | nombre | Température retenue, `-999` si aucune mesure. |
| `repeat.index` | entier | Numéro du rappel en cours (1 = premier envoi). |

Exemple d'action à saisir dans le champ *Notification* :

```yaml
- action: notify.mobile_app_telephone
  data:
    title: "{{ titre }}"
    message: "{{ message }} (rappel {{ repeat.index }})"
```

## Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Délai avant le premier rappel | 10 min | Ignore les aérations courtes. |
| Capteurs de température extérieure | — | Vide = rappeler quelle que soit la température. |
| Seuil de température | 12 °C | Ne s'applique qu'au motif `duree`. |
| Entités de présence | — | Vide = pas de rappel au départ. |
| Intervalle entre deux rappels | 15 min | |
| Nombre maximal de rappels | 3 | 0 = indéfiniment. |
| Notification de fermeture | — | Facultative. |

## Notes

- Pour ne réagir qu'au départ du **dernier** occupant, indiquer un groupe de
  personnes (`group.famille`) plutôt que chaque `person`. Sinon chaque départ
  individuel déclenche un rappel.
- Deux déclencheurs couvrent le départ : passage à `not_home` (`person`,
  `group`, `device_tracker`) et passage de `on` à `off` (capteur de présence
  binaire).
- Avec plusieurs capteurs de température, c'est la valeur la plus basse qui est
  comparée au seuil.
- L'état est porté par l'exécution : un redémarrage de Home Assistant pendant un
  cycle de rappels l'interrompt. La fenêtre sera de nouveau signalée à la
  prochaine ouverture, pas avant.
