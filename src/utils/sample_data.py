"""Génère un jeu de données SYNTHÉTIQUE au même schéma que la source.

Utile pour exécuter le pipeline et les tests sans accès aux données privées :

    python -m src.utils.sample_data --rows 2000

Les valeurs sont tirées au hasard : elles ne décrivent aucun client réel et ne
reproduisent pas les résultats du jeu de données d'origine.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src import config

CITIES = {
    "Ville A": 2_100_000, "Ville B": 870_000, "Ville C": 520_000, "Ville D": 290_000,
    "Ville E": 170_000, "Ville F": 155_000, "Ville G": 120_000, "Ville H": 108_000,
}


def generate_sample(rows: int = 2000, duplicates: int = 5,
                    missing_age_rate: float = 0.02, seed: int = 0) -> pd.DataFrame:
    """Retourne un DataFrame synthétique au schéma de la source (doublons et âges manquants inclus)."""
    rng = np.random.default_rng(seed)
    cities = rng.choice(list(CITIES), size=rows)
    df = pd.DataFrame({
        "client_id": np.arange(1, rows + 1),
        "nom": [f"Nom{n:02d}" for n in rng.integers(1, 41, size=rows)],
        "prenom": [f"Prenom{n:02d}" for n in rng.integers(1, 21, size=rows)],
        "age": rng.integers(18, 81, size=rows).astype(float),
        "ville": cities,
        "population_ville": [CITIES[c] for c in cities],
        "revenu_annuel": rng.integers(18_000, 150_000, size=rows),
        "type_compte": rng.choice(sorted(config.ALLOWED_VALUES["type_compte"]), size=rows),
        "solde": rng.uniform(20, 120_000, size=rows).round(2),
        "statut": rng.choice(sorted(config.ALLOWED_VALUES["statut"]), size=rows),
    })
    missing_idx = rng.choice(rows, size=int(rows * missing_age_rate), replace=False)
    df.loc[missing_idx, "age"] = np.nan
    if duplicates:
        df = pd.concat([df, df.sample(duplicates, random_state=seed)], ignore_index=True)
    return df[config.EXPECTED_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère une source synthétique pour tester le pipeline."
    )
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", default=str(config.RAW_FILE))
    parser.add_argument("--force", action="store_true", help="Écrase le fichier s'il existe déjà.")
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"{output} existe déjà. Utilisez --force pour l'écraser.")
    output.parent.mkdir(parents=True, exist_ok=True)
    df = generate_sample(rows=args.rows, seed=args.seed)
    df.to_csv(output, index=False, encoding="utf-8")
    print(f"Source synthétique écrite : {output} ({len(df)} lignes)")


if __name__ == "__main__":
    main()
