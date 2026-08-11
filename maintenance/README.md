# Alerte batteries faibles

`batteries_faibles.yaml` — à instancier **une seule fois**.

## Fonctionnement

À l'heure choisie, l'automatisation balaye l'ensemble des entités de
l'installation et construit la liste de celles dont la batterie est au niveau ou
en dessous du seuil :

- les `sensor` de `device_class: battery` dont l'état est numérique ;
- optionnellement les `binary_sensor` de `device_class: battery` à `on` (batterie
  faible sans pourcentage) ;
- optionnellement toute entité exposant un attribut `battery_level`.

Si la liste est vide, rien n'est envoyé. Sinon, **une seule notification**
récapitulative est envoyée, triée du plus faible au plus élevé.

Aucune entité n'est à déclarer : les appareils ajoutés plus tard sont pris en
compte automatiquement.

## Variables disponibles dans l'action de notification

| Variable | Type | Contenu |
| --- | --- | --- |
| `message` | texte | Message complet, une ligne par appareil. |
| `titre` | texte | `Batteries faibles (3)` |
| `nombre` | entier | Nombre d'appareils concernés. |
| `liste` | liste de textes | `["Capteur salon : 12 %", …]` |
| `batteries` | liste de dicts | `nom`, `entite`, `niveau` (float, `-1` pour un capteur binaire), `texte`. |

Exemple d'action à saisir dans le champ *Notification* :

```yaml
- action: notify.mobile_app_telephone
  data:
    title: "{{ titre }}"
    message: "{{ message }}"
```

Ou, pour une notification persistante dans l'interface :

```yaml
- action: persistent_notification.create
  data:
    title: "{{ titre }}"
    message: "{{ message }}"
    notification_id: batteries_faibles
```

## Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Seuil d'alerte | 20 % | Comparaison « inférieur ou égal ». |
| Heure de vérification | 09:00 | |
| Jours de vérification | tous | Ne cocher qu'un jour transforme l'alerte en rappel hebdomadaire. |
| Entités à ignorer | — | Capteurs mal déclarés ou en panne connue. |
| Inclure les capteurs binaires | activé | `binary_sensor` de classe `battery`. |
| Inclure l'attribut `battery_level` | désactivé | Peut produire des doublons avec le capteur dédié du même appareil. |

## Notes

- La répétition est celle du déclencheur : l'alerte est renvoyée à chaque
  vérification tant que la batterie n'est pas remplacée. Espacer les rappels se
  fait en réduisant la liste des jours.
- Les entités `unavailable` / `unknown` sont ignorées : elles relèvent de la
  détection d'entités mortes, pas de l'alerte batterie.
- Le balayage parcourt toutes les entités une fois par jour ; le coût est
  négligeable, mais éviter d'en faire un `time_pattern` à la minute.
