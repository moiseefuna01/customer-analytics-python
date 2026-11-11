"""Couche Gold ML : table de modélisation (une ligne par client, sans identifiant).

    python -m src.gold.build_gold_ml

Contenu : les variables explicatives candidates et la cible `statut` (statut
OBSERVÉ à la date de l'extraction). Les âges manquants restent manquants :
l'imputation est apprise dans le pipeline scikit-learn, sur le jeu
d'entraînement uniquement.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src import config


def build_ml_dataset(silver: pd.DataFrame) -> pd.DataFrame:
    """Sélectionne les variables de modélisation et normalise les types pour scikit-learn."""
    required = [*config.ML_FEATURES, config.TARGET]
    missing = [col for col in required if col not in silver.columns]
    if missing:
        raise ValueError(f"Colonnes absentes de Silver : {missing}")
    if not silver[config.TECHNICAL_KEY].is_unique:
        raise ValueError("client_id dupliqués dans Silver : une ligne par client est requise.")

    gold_ml = silver[required].copy()
    gold_ml["age"] = gold_ml["age"].astype("float64")          # <NA> -> NaN, compris par scikit-learn
    for col in [*config.CATEGORICAL_FEATURES, config.TARGET]:
        gold_ml[col] = gold_ml[col].astype(object)

    observed = set(gold_ml[config.TARGET].unique())
    if observed != config.ALLOWED_VALUES[config.TARGET]:
        raise ValueError(f"Classes inattendues dans la cible : {sorted(map(str, observed))}")
    assert not np.isinf(gold_ml[config.NUMERIC_FEATURES].to_numpy(dtype=float)).any()
    return gold_ml.reset_index(drop=True)


def build_gold_ml(silver_path: Path | str = config.SILVER_FILE,
                  output_path: Path | str = config.GOLD_ML_FILE,
                  csv_output_path: Path | str | None = None) -> pd.DataFrame:
    """Construit Gold ML et l'exporte en Parquet (référence) et CSV (inspection).

    Le CSV et le Parquet sont des fichiers au niveau client : ils restent locaux
    et sont exclus du dépôt Git par les règles de confidentialité.
    """
    gold_ml = build_ml_dataset(pd.read_parquet(silver_path))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gold_ml.to_parquet(output_path, index=False, engine="pyarrow")

    csv_path = Path(csv_output_path) if csv_output_path is not None else output_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    gold_ml.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return gold_ml


def main() -> None:
    parser = argparse.ArgumentParser(description="Construction du dataset Gold ML.")
    parser.add_argument("--input", default=str(config.SILVER_FILE))
    parser.add_argument("--output", default=str(config.GOLD_ML_FILE))
    parser.add_argument("--csv-output", default=str(config.GOLD_ML_CSV_FILE))
    args = parser.parse_args()
    gold_ml = build_gold_ml(args.input, args.output, args.csv_output)
    print("=== GOLD ML ===")
    print(f"Lignes : {len(gold_ml)} | Variables : {config.ML_FEATURES} | Cible : {config.TARGET}")
    print(f"CSV : {args.csv_output}")
    print(f"Parquet : {args.output}")
    print(f"Âges manquants (imputés plus tard, dans le pipeline) : {int(gold_ml['age'].isna().sum())}")


if __name__ == "__main__":
    main()
