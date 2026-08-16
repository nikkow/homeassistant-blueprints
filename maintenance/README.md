# Maintenance

- [Alerte batteries faibles](#alerte-batteries-faibles) — `batteries_faibles.yaml`
- [Redémarrage d'une box par sa prise](#redémarrage-dune-box-par-sa-prise) — `box_indisponible_redemarrage.yaml`

---

## Alerte batteries faibles

`batteries_faibles.yaml` — à instancier **une seule fois**.

### Fonctionnement

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

### Variables disponibles dans l'action de notification

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

### Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Seuil d'alerte | 20 % | Comparaison « inférieur ou égal ». |
| Heure de vérification | 09:00 | |
| Jours de vérification | tous | Ne cocher qu'un jour transforme l'alerte en rappel hebdomadaire. |
| Entités à ignorer | — | Capteurs mal déclarés ou en panne connue. |
| Inclure les capteurs binaires | activé | `binary_sensor` de classe `battery`. |
| Inclure l'attribut `battery_level` | désactivé | Peut produire des doublons avec le capteur dédié du même appareil. |

### Notes

- La répétition est celle du déclencheur : l'alerte est renvoyée à chaque
  vérification tant que la batterie n'est pas remplacée. Espacer les rappels se
  fait en réduisant la liste des jours.
- Les entités `unavailable` / `unknown` sont ignorées : elles relèvent de la
  détection d'entités mortes, pas de l'alerte batterie.
- Le balayage parcourt toutes les entités une fois par jour ; le coût est
  négligeable, mais éviter d'en faire un `time_pattern` à la minute.

---

## Redémarrage d'une box par sa prise

`box_indisponible_redemarrage.yaml` — à instancier **une fois par box**.

Écrit pour une box **iDiamant** (volets Bubendorff) exposée par l'intégration
**Netatmo** via un compte développeur : la box perd sa connexion au cloud, les
volets passent `unavailable` et n'en sortent qu'après une coupure de courant.
Le blueprint reste générique — n'importe quel appareil alimenté par une prise
pilotable convient.

### Fonctionnement

1. Une des entités surveillées passe `unavailable` et le reste pendant le
   **délai avant détection** (30 s par défaut).
2. Les conditions de sécurité sont vérifiées (voir plus bas).
3. Cycle, répété jusqu'au **nombre de tentatives** :
   - la prise est éteinte pendant la **durée de coupure** (30 s) ;
   - elle est rallumée, puis la **durée de démarrage** (1 min) laisse à la box
     le temps de booter et de rejoindre son cloud ;
   - l'entrée d'intégration est rechargée
     (`homeassistant.reload_config_entry`) ;
   - l'automatisation attend, au plus pendant le **délai de vérification**
     (3 min), que **toutes** les entités surveillées soient redevenues
     disponibles.
   Le cycle s'arrête dès que tout est revenu.
4. Notification facultative de succès ou d'échec.

Comme la panne fait basculer toutes les entités en même temps, le déclencheur
part plusieurs fois : `mode: single` + `max_exceeded: silent` ne retiennent que
la première exécution, sans remplir le journal.

### Rechargement de l'intégration

Par défaut, aucun identifiant n'est à saisir : l'entrée à recharger est déduite
des entités surveillées, et une entrée n'est rechargée qu'une fois même si
plusieurs entités y renvoient.

L'option **ID de l'entrée d'intégration** sert de repli pour le cas où
l'intégration échoue au point que ses entités disparaissent de l'installation :
il n'y a alors plus rien à cibler. L'identifiant se lit dans l'URL de la page de
l'intégration, après `config_entry/`.

Le rechargement porte sur **toute l'entrée**. Si le même compte Netatmo expose
aussi un thermostat ou des caméras, ils sont rechargés en même temps — sans
danger, mais leurs entités clignotent brièvement.

### Garde-fous

| Garde-fou | Rôle |
| --- | --- |
| **Délai de garde** (30 min) | Durée minimale entre deux cycles, pour ne pas enchaîner les coupures quand la cause n'est pas la box. Repose sur `last_triggered` de l'automatisation, sans helper. |
| **Prise disponible** | Si la prise est elle-même `unavailable`, le cycle est abandonné : c'est le symptôme d'un redémarrage de Home Assistant, où couper la prise ne servirait à rien. |
| **Conditions supplémentaires** | À toi de les remplir, par exemple « la connexion Internet est rétablie » — recycler la prise ne répare pas une panne du cloud Netatmo. |

### Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Entités à surveiller | — | Quelques entités représentatives de la box. En déclarer plusieurs évite de recycler la prise à cause d'un seul appareil hors de portée radio. |
| Prise à recycler | — | `switch`, `light` ou `input_boolean`. |
| Délai avant détection | 30 s | Monter à 60–120 s réduit les faux positifs au redémarrage de Home Assistant. |
| Durée de coupure | 30 s | |
| Durée de démarrage | 1 min | Trop court : le rechargement se fait dans le vide et la tentative est perdue. |
| Délai de vérification | 3 min | Attente maximale du retour des entités après rechargement. |
| Nombre de tentatives | 2 | |
| Délai de garde | 30 min | |
| ID de l'entrée d'intégration | — | Repli, voir plus haut. |
| Conditions supplémentaires | — | |
| Notification de succès / d'échec | — | |

### Variables disponibles dans les notifications

| Variable | Type | Contenu |
| --- | --- | --- |
| `message` | texte | Résumé prêt à l'emploi, adapté au succès ou à l'échec. |
| `titre` | texte | `Box redémarrée` ou `Box toujours indisponible`. |
| `nombre` | entier | Entités indisponibles au moment du déclenchement. |
| `noms` | liste de textes | Leurs noms. |
| `restantes` | liste d'`entity_id` | Entités toujours indisponibles à la fin (vide en cas de succès). |
| `noms_restants` | liste de textes | Leurs noms, ou leur `entity_id` si l'entité a disparu. |
| `tentatives` | entier | Nombre maximal de cycles configuré. |

```yaml
- action: notify.mobile_app_telephone
  data:
    title: "{{ titre }}"
    message: "{{ message }}"
```

### Notes et limites

- **Une panne du cloud ou d'Internet** produit exactement le même symptôme
  qu'une box figée. Le blueprint coupera la prise pour rien, une fois, puis le
  délai de garde le retiendra. Renseigner une condition supplémentaire sur
  l'état de la connexion supprime ce cas.
- **Le déclencheur ne se répète pas.** Si les entités restent `unavailable`
  après toutes les tentatives, leur état ne change plus et rien ne relance
  l'automatisation : c'est la boucle de tentatives qui insiste, pas le
  déclencheur. Prévoir la notification d'échec pour être averti.
- **Un redémarrage de Home Assistant interrompt un cycle en cours** — la prise
  pourrait rester éteinte. Le risque est limité à la fenêtre de 30 s de
  coupure ; si la prise alimente autre chose que la box, en tenir compte.
- **Usure matérielle** : une coupure d'alimentation brutale n'est pas anodine
  pour la box. Garder un délai de garde généreux et un nombre de tentatives
  faible.
- Si l'automatisation est déclenchée manuellement, elle exécute le cycle sans
  condition d'indisponibilité — pratique pour tester le câblage et les délais.
