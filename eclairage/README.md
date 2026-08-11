# Éclairage sur mouvement avec luminosité adaptative

`eclairage_mouvement.yaml` — à instancier **une fois par pièce**.

## Fonctionnement

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

## Détection d'une intervention manuelle

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

## Seuil de luminosité

La condition de luminosité n'est évaluée que lorsque **toutes les lumières
pilotées sont éteintes**. Sans cette précaution, une lampe allumée par
l'automatisation ferait remonter la mesure au-dessus du seuil et bloquerait la
prolongation du cycle au mouvement suivant.

Avec plusieurs capteurs, c'est la valeur la plus basse qui compte. Si aucun
capteur ne renvoie de valeur numérique, le seuil est ignoré.

## Options

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

## Notes

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
