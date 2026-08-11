# Blueprints Home Assistant

Collection personnelle de blueprints d'automatisation pour
[Home Assistant](https://www.home-assistant.io/), en français.

Chaque dossier regroupe un thème et contient le blueprint accompagné de son
README : fonctionnement détaillé, tableau des options et limites connues.

## Blueprints disponibles

| Blueprint | Thème | Rôle | Instances |
| --- | --- | --- | --- |
| [`volets/volets_soleil.yaml`](volets/volets_soleil.yaml) | Volets | Fermeture progressive selon l'azimut solaire, la radiation et la température extérieure. | 1 par fenêtre |
| [`climatisation/clim_fenetre_ouverte.yaml`](climatisation/clim_fenetre_ouverte.yaml) | Climatisation | Coupe la clim/le chauffage à l'ouverture d'une fenêtre, restaure l'état exact à la fermeture. — [doc](climatisation/README.md) | 1 par pièce |
| [`eclairage/eclairage_mouvement.yaml`](eclairage/eclairage_mouvement.yaml) | Éclairage | Éclairage sur mouvement, luminosité et température de couleur adaptées au jour/à la nuit, réglages manuels respectés. — [doc](eclairage/README.md) | 1 par pièce |
| [`maintenance/batteries_faibles.yaml`](maintenance/batteries_faibles.yaml) | Maintenance | Balayage de toutes les batteries de l'installation, notification unique groupée. — [doc](maintenance/README.md) | 1 |
| [`fenetres/fenetre_ouverte_rappel.yaml`](fenetres/fenetre_ouverte_rappel.yaml) | Fenêtres | Rappel d'une fenêtre ouverte trop longtemps par temps froid, ou au départ de la maison. — [doc](fenetres/README.md) | 1 |

## Installation

Dans Home Assistant : **Paramètres → Automatisations et scènes → Blueprints →
Importer un blueprint**, puis coller l'URL du fichier. Par exemple :

```
https://github.com/nikkow/homeassistant-blueprints/blob/main/eclairage/eclairage_mouvement.yaml
```

Alternative manuelle : copier le fichier dans
`config/blueprints/automation/<dossier>/` puis recharger les automatisations.

## Conventions

- Syntaxe moderne : `triggers` / `conditions` / `actions`, avec `trigger:` comme
  clé de type (Home Assistant 2024.10+).
- Noms d'entrées, descriptions et commentaires en français.
- Pas de helper `input_*` à créer, sauf mention explicite dans le README du
  blueprint : l'état est porté par l'exécution de l'automatisation. Corollaire
  documenté au cas par cas — un redémarrage de Home Assistant interrompt les
  cycles en cours.
- Les entrées facultatives ont un `default` (`[]` pour une liste d'entités) et
  leur absence est gérée dans les templates, jamais par une erreur.
- Chaque blueprint indique en tête combien de fois il doit être instancié.

## Validation

Le dépôt est vérifié par [`.github/workflows/validation.yml`](.github/workflows/validation.yml)
à chaque push et chaque pull request. Deux étapes :

1. **`yamllint`** — formatage YAML, configuration dans
   [`.yamllint.yml`](.yamllint.yml). Mode `--strict` : les avertissements font
   échouer le job.
2. **`scripts/validate_blueprints.py`** — structure des blueprints :
   - le YAML se charge, tags `!input` / `!secret` / `!include` compris ;
   - `blueprint.name` et `blueprint.domain` sont présents, le domaine est connu ;
   - tout `!input` utilisé est déclaré (erreur), toute entrée déclarée est
     utilisée (avertissement) ;
   - une automatisation a au moins un déclencheur et une action ;
   - les entrées ne sont pas déclarées deux fois, sections comprises.

En local :

```bash
pip install pyyaml yamllint && yamllint -c .yamllint.yml --strict . && python scripts/validate_blueprints.py
```

Le script accepte aussi des chemins précis :

```bash
python scripts/validate_blueprints.py eclairage/eclairage_mouvement.yaml
```

Cette validation est statique : elle ne remplace pas un import réel dans Home
Assistant, qui seul vérifie les sélecteurs, les services appelés et le rendu des
templates.
