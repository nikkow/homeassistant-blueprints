# Éclairage

- [Éclairage sur mouvement avec luminosité adaptative](#éclairage-sur-mouvement-avec-luminosité-adaptative) — `eclairage_mouvement.yaml`
- [Éclairage extérieur sur détection de personne](#éclairage-extérieur-sur-détection-de-personne) — `eclairage_sonnette.yaml`

---

## Éclairage sur mouvement avec luminosité adaptative

`eclairage_mouvement.yaml` — à instancier **une fois par pièce**.

### Fonctionnement

1. Un capteur de mouvement de la pièce passe à « détecté ».
2. Si la luminosité mesurée est sous le seuil (ou qu'aucune lumière n'est
   allumée et qu'aucun capteur de luminosité n'est renseigné), les lumières sont
   allumées avec la luminosité et la température de couleur du moment — réglages
   de jour ou de nuit selon la plage horaire.
3. Juste après la transition, l'automatisation relève une **empreinte** de
   chaque lumière (état + luminosité effective).
4. L'automatisation attend que **tous** les capteurs soient retombés, puis
   décompte le délai d'extinction. Un nouveau mouvement pendant ce délai relance
   le cycle (`mode: restart`).
5. À l'extinction, chaque lumière est comparée à son empreinte. Celles qui ont
   changé entre-temps sont laissées allumées.

### Détection d'une intervention manuelle

L'empreinte est la seule mémoire utilisée : **aucun helper `input_*` n'est à
créer**. Ce que cela couvre et ce que cela ne couvre pas :

- Une lumière tamisée, éteinte puis rallumée, ou modifiée par une scène pendant
  le délai d'extinction ne sera **pas** éteinte automatiquement.
- Une lumière allumée à la main alors qu'il n'y a aucun mouvement n'est pas
  concernée : l'automatisation ne se déclenche pas.
- En revanche, si un mouvement est détecté après un réglage manuel, le cycle
  reprend la main et réapplique la luminosité cible. C'est le comportement voulu
  pour que la pièce ne reste pas figée sur un réglage oublié ; utiliser une
  *entité de blocage* pour neutraliser complètement l'automatisation.
- Un redémarrage de Home Assistant pendant le délai d'extinction perd
  l'exécution en cours : les lumières restent allumées jusqu'au mouvement
  suivant.

### Seuil de luminosité

La condition de luminosité n'est évaluée que lorsque **toutes les lumières
pilotées sont éteintes**. Sans cette précaution, une lampe allumée par
l'automatisation ferait remonter la mesure au-dessus du seuil et bloquerait la
prolongation du cycle au mouvement suivant.

Avec plusieurs capteurs, c'est la valeur la plus basse qui compte. Si aucun
capteur ne renvoie de valeur numérique, le seuil est ignoré.

### Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Seuil de luminosité | 20 lx | Ignoré si aucun capteur n'est renseigné. |
| Délai avant extinction | 2 min | Décompté une fois tous les capteurs retombés. |
| Début / fin du mode nuit | 22:00 → 07:00 | Plage passant minuit gérée. |
| Luminosité jour / nuit | 100 % / 25 % | |
| Température de couleur jour / nuit | 4000 K / 2200 K | **0 = ne pas envoyer**, pour les lumières non réglables en blanc. |
| Durée de transition | 1 s | Envoyée à l'allumage et à l'extinction. |
| Respecter les réglages manuels | activé | Voir plus haut. |
| Entités de blocage | — | Tant qu'une est à `on`, l'automatisation ne fait rien. |

### Notes

- Les lumières sont sélectionnées par entité (et non par cible) : le blueprint a
  besoin de la liste pour relever l'empreinte et n'éteindre qu'un sous-ensemble.
- `transition` est envoyée systématiquement. Les intégrations qui ne la
  supportent pas l'ignorent, parfois avec un avertissement dans le journal :
  mettre 0 dans ce cas.
- Si la température de couleur est renseignée alors qu'une lumière ne la
  supporte pas, l'appel échoue pour cette lumière. Créer une instance séparée
  par type de lumière, ou mettre 0.
- L'attente de fin de mouvement n'a pas de délai de garde : un capteur bloqué
  sur « détecté » maintient les lumières allumées indéfiniment. C'est
  volontaire — le capteur est alors le problème à traiter — mais l'*entité de
  blocage* permet de reprendre la main sans désactiver l'automatisation.

---

## Éclairage extérieur sur détection de personne

`eclairage_sonnette.yaml` — à instancier **une fois par entrée** (porte,
portail…).

### Fonctionnement

1. Un capteur « personne » de la sonnette reste à « détecté » pendant la
   **durée de présence minimale** (3 s par défaut).
2. S'il fait nuit (soleil sous l'élévation choisie), qu'aucune entité de
   blocage n'est active et que la lumière n'est pas déjà allumée à la main, la
   lumière s'allume.
3. Après la transition, une **empreinte** de chaque lumière est relevée (état +
   luminosité), comme pour l'éclairage sur mouvement.
4. L'automatisation attend que tous les capteurs de maintien soient retombés,
   puis décompte le délai. Un mouvement pendant le décompte le remet à zéro ;
   une nouvelle détection de personne relance le cycle (`mode: restart`).
5. À l'extinction, seules les lumières identiques à leur empreinte sont
   éteintes.

### Filtrer les passants

Trois leviers, du plus efficace au moins efficace :

1. **Zone de détection** dans l'application de la sonnette (Reolink, UniFi
   Protect, Ring, Netatmo…) : limiter la détection au perron et exclure le
   trottoir. C'est le filtre principal ; Home Assistant ne voit que le résultat.
2. **Capteur « personne »** plutôt que « mouvement » : ignore voitures, chats
   et ombres.
3. **Durée de présence minimale** : un passant traverse le champ en 1 à 3 s,
   un visiteur qui s'approche de la porte y reste plus longtemps. Augmenter à
   5 s si des passants déclenchent encore, la diminuer si l'allumage semble
   tardif.

> Si le capteur personne de la sonnette retombe très vite (impulsion de
> quelques secondes), la durée minimale peut empêcher tout allumage : la
> mettre à 0 et s'appuyer uniquement sur la zone de détection.

### Fausse détection à l'extinction

Une sonnette à caméra (Aqara G4 notamment) voit l'extinction de la lumière
comme un mouvement : l'image change brusquement et la caméra bascule en vision
nocturne infrarouge. Sans précaution, la lumière se rallume, s'éteint après le
délai, se rallume… en boucle.

Une détection dont le **début** tombe à moins du *délai de garde* (15 s par
défaut) du passage d'une lumière à « off » est donc ignorée. C'est le début de
la détection qui compte, pas la fin de la durée de présence minimale : un
capteur qui reste actif longtemps après l'extinction est bien filtré. Si la
boucle persiste, augmenter le délai ; la contrepartie est qu'un visiteur
arrivant juste à l'extinction ne rallume pas la lumière.

### Allumage manuel

- Lumière allumée à la main avant toute détection : l'automatisation ne fait
  rien, ni allumage ni extinction.
- Lumière modifiée pendant un cycle (luminosité, couleur via l'appli Hue,
  éteinte puis rallumée) : elle n'est pas éteinte à la fin du cycle.
- Une nouvelle détection de personne pendant un cycle réapplique la
  luminosité cible, comme pour l'éclairage sur mouvement.

L'allumage manuel est reconnu par l'attribut `current` de l'automatisation au
moment du déclenchement : une lumière allumée alors qu'aucun cycle n'est en
cours est considérée comme manuelle. **Aucun helper n'est à créer.**

### Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Capteurs de détection de personne | — | Déclenchent l'allumage. |
| Durée de présence minimale | 3 s | Filtre les passants. 0 = immédiat. |
| Capteurs de maintien | capteurs personne | Prolongent l'éclairage. Ex. : capteur de mouvement de la sonnette. |
| Délai avant extinction | 3 min | Décompté une fois tous les capteurs de maintien retombés. |
| Élévation solaire maximale | 0° | 0° = coucher du soleil, -6° = nuit noire ; 90 = toujours. |
| Luminosité | 100 % | |
| Température de couleur | 2700 K | **0 = ne pas envoyer.** |
| Durée de transition | 1 s | |
| Délai de garde après extinction | 15 s | Ignore la fausse détection provoquée par l'extinction. 0 = désactivé. |
| Entités de blocage | — | Tant qu'une est à `on`, rien ne se passe. |

### Notes

- Les capteurs de maintien peuvent inclure le **mouvement** de la sonnette,
  plus sensible : un passant prolonge alors une lumière déjà allumée, mais ne
  l'allume jamais.
- La condition de nuit n'est pas réévaluée pendant un cycle : une détection au
  lever du soleil prolonge l'éclairage au lieu de l'abandonner allumé.
- Un redémarrage de Home Assistant pendant un cycle le perd : la lumière reste
  allumée jusqu'à la prochaine détection. Elle sera alors considérée comme
  allumée à la main et laissée telle quelle — l'éteindre une fois suffit à
  rétablir le fonctionnement.
- Sonnettes sans `binary_sensor` (Google Nest notamment, qui n'expose que des
  événements) : créer un capteur binaire template déclenché par l'événement,
  avec `auto_off`, et le passer en entrée.
