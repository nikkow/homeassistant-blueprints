#!/usr/bin/env python3
"""Validation statique des blueprints Home Assistant du dépôt.

Ne remplace pas un import réel dans Home Assistant : ce script vérifie ce qui
peut l'être sans instance HA — syntaxe YAML, structure du bloc `blueprint`,
et cohérence entre les entrées déclarées et les `!input` utilisés.

Usage : python scripts/validate_blueprints.py [chemin...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

DOMAINES_VALIDES = {"automation", "script", "template"}
# Dossiers explorés par défaut : tout le dépôt sauf ceux-ci.
EXCLUS = {".git", ".github", "scripts", "node_modules", "venv", ".venv"}


class Input:
    """Marqueur pour le tag `!input` d'un blueprint."""

    def __init__(self, nom: str) -> None:
        self.nom = nom

    def __repr__(self) -> str:  # pragma: no cover - confort de débogage
        return f"!input {self.nom}"


class BlueprintLoader(yaml.SafeLoader):
    """SafeLoader qui accepte les tags propres à Home Assistant."""


def _input(loader: yaml.Loader, node: yaml.Node) -> Input:
    return Input(str(loader.construct_scalar(node)))


def _opaque(loader: yaml.Loader, node: yaml.Node) -> str:
    return f"<{node.tag}>"


BlueprintLoader.add_constructor("!input", _input)
for tag in ("!secret", "!include", "!env_var", "!include_dir_list",
            "!include_dir_merge_list", "!include_dir_named",
            "!include_dir_merge_named"):
    BlueprintLoader.add_constructor(tag, _opaque)


def collecte_inputs(noeud) -> set[str]:
    """Retourne les noms de tous les `!input` rencontrés dans la structure."""
    if isinstance(noeud, Input):
        return {noeud.nom}
    if isinstance(noeud, dict):
        return set().union(*(collecte_inputs(v) for v in noeud.values())) if noeud else set()
    if isinstance(noeud, list):
        return set().union(*(collecte_inputs(v) for v in noeud)) if noeud else set()
    return set()


def declare_inputs(bloc, erreurs: list[str], fichier: Path) -> set[str]:
    """Aplatit `blueprint.input`, en tenant compte des sections."""
    noms: set[str] = set()
    if not isinstance(bloc, dict):
        return noms
    for nom, definition in bloc.items():
        # Une section est une entrée dont la définition contient elle-même
        # une clé `input` (regroupement visuel introduit par HA 2024.6).
        if isinstance(definition, dict) and "input" in definition:
            for sous_nom in declare_inputs(definition["input"], erreurs, fichier):
                if sous_nom in noms:
                    erreurs.append(f"{fichier}: entrée « {sous_nom} » déclarée deux fois")
                noms.add(sous_nom)
            continue
        if nom in noms:
            erreurs.append(f"{fichier}: entrée « {nom} » déclarée deux fois")
        noms.add(nom)
    return noms


def valide(fichier: Path) -> tuple[list[str], list[str], bool]:
    """Retourne (erreurs, avertissements, le fichier est un blueprint)."""
    erreurs: list[str] = []
    avertissements: list[str] = []

    try:
        contenu = yaml.load(fichier.read_text(encoding="utf-8"), Loader=BlueprintLoader)
    except yaml.YAMLError as exc:
        return [f"{fichier}: YAML invalide — {exc}"], [], False

    if not isinstance(contenu, dict) or "blueprint" not in contenu:
        # Fichier YAML du dépôt qui n'est pas un blueprint : rien à vérifier.
        return [], [], False

    bloc = contenu["blueprint"]
    if not isinstance(bloc, dict):
        return [f"{fichier}: la clé « blueprint » doit être un dictionnaire"], [], True

    for cle in ("name", "domain"):
        if not bloc.get(cle):
            erreurs.append(f"{fichier}: « blueprint.{cle} » manquant")

    domaine = bloc.get("domain")
    if domaine and domaine not in DOMAINES_VALIDES:
        erreurs.append(
            f"{fichier}: domaine « {domaine} » inconnu "
            f"(attendu : {', '.join(sorted(DOMAINES_VALIDES))})"
        )

    if not bloc.get("description"):
        avertissements.append(f"{fichier}: pas de description")

    declarees = declare_inputs(bloc.get("input", {}), erreurs, fichier)
    utilisees = collecte_inputs({k: v for k, v in contenu.items() if k != "blueprint"})

    for nom in sorted(utilisees - declarees):
        erreurs.append(f"{fichier}: « !input {nom} » utilisé mais non déclaré")
    for nom in sorted(declarees - utilisees):
        avertissements.append(f"{fichier}: entrée « {nom} » déclarée mais jamais utilisée")

    if domaine == "automation":
        if not (contenu.get("triggers") or contenu.get("trigger")):
            erreurs.append(f"{fichier}: automatisation sans déclencheur")
        if not (contenu.get("actions") or contenu.get("action")):
            erreurs.append(f"{fichier}: automatisation sans action")

    return erreurs, avertissements, True


def fichiers_a_valider(args: list[str]) -> list[Path]:
    if args:
        return sorted(Path(a) for a in args)
    racine = Path(__file__).resolve().parent.parent
    return sorted(
        chemin
        for chemin in racine.rglob("*.yaml")
        if not EXCLUS & set(chemin.relative_to(racine).parts)
    )


def main() -> int:
    fichiers = fichiers_a_valider(sys.argv[1:])
    if not fichiers:
        print("Aucun fichier YAML trouvé.")
        return 1

    erreurs: list[str] = []
    avertissements: list[str] = []
    blueprints = 0

    for fichier in fichiers:
        f_erreurs, f_avertissements, est_blueprint = valide(fichier)
        blueprints += 1 if est_blueprint else 0
        erreurs += f_erreurs
        avertissements += f_avertissements

    for ligne in avertissements:
        print(f"AVERTISSEMENT  {ligne}")
    for ligne in erreurs:
        print(f"ERREUR         {ligne}")

    print(
        f"\n{blueprints} blueprint(s) analysé(s) sur {len(fichiers)} fichier(s) — "
        f"{len(erreurs)} erreur(s), {len(avertissements)} avertissement(s)."
    )
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
