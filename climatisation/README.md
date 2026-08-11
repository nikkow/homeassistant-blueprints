# Coupure clim/chauffage à l'ouverture d'une fenêtre

`clim_fenetre_ouverte.yaml` — à instancier **une fois par pièce**.

## Fonctionnement

1. Une fenêtre de la pièce s'ouvre et le reste plus longtemps que le *délai avant coupure*.
2. Si au moins un équipement `climate` de la pièce est en marche, son état complet est
   sauvegardé dans une scène créée à la volée (`scene.backup_clim_<nom_automatisation>`),
   puis l'équipement est éteint.
3. L'automatisation attend que **toutes** les fenêtres de la pièce soient refermées.
4. La scène est rejouée : mode HVAC, consigne, preset, vitesse de ventilation, etc.
   sont remis exactement comme avant l'ouverture.
5. La scène temporaire est supprimée (`scene.delete`), y compris quand la
   restauration a été abandonnée.

### Cycle de vie de la scène

Les scènes créées par `scene.create` vivent en mémoire jusqu'au prochain
redémarrage ou `scene.reload`. Le blueprint appelle donc `scene.delete` sur tous
les chemins de sortie — restauration effectuée, dépassement de la durée maximale,
ou équipement rallumé à la main — pour ne laisser aucune entité `scene.backup_clim_*`
derrière lui. L'appel est en `continue_on_error` car `scene.delete` n'existe qu'à
partir de Home Assistant 2023.4 ; sur une version antérieure la scène subsiste
simplement jusqu'au prochain rechargement, sans casser l'automatisation.

Une exécution interrompue (redémarrage de HA, rechargement des automatisations
fenêtre ouverte) peut laisser une scène orpheline : elle sera écrasée au prochain
cycle, l'ID étant dérivé du nom de l'automatisation.

L'état est porté par l'exécution de l'automatisation, donc **aucun helper
`input_*` n'est à créer**. Corollaire : si Home Assistant redémarre alors que la
fenêtre est ouverte, l'exécution en cours est perdue et la restauration n'aura
pas lieu.

## Options

| Option | Défaut | Rôle |
| --- | --- | --- |
| Délai avant coupure | 30 s | Ignore les ouvertures brèves. |
| Délai avant restauration | 0 s | Laisse la pièce se refermer avant de relancer. |
| Durée maximale d'ouverture | 0 (désactivé) | Au-delà, la restauration est abandonnée : l'équipement reste éteint. |
| Ne restaurer que si rien n'a été touché | activé | Annule la restauration si un équipement a été rallumé à la main pendant l'ouverture. |

## Notes

- Si aucun équipement n'est en marche à l'ouverture, l'automatisation ne se
  déclenche pas : rien n'est éteint, rien n'est restauré.
- `mode: single` : une réouverture de fenêtre pendant qu'une exécution attend la
  fermeture est ignorée, ce qui est le comportement voulu.
- La coupure utilise `climate.turn_off`. Si un équipement ne supporte pas
  l'extinction, remplacer par `climate.set_hvac_mode` avec `hvac_mode: "off"`.
