"""Couche Silver : données nettoyées, validées et pseudonymisées.

    python -m src.silver.build_silver

Règles appliquées (voir docs/data_quality_rules.md) :
1. schéma attendu présent ;
2. espaces superflus retirés des variables texte ;
3. doublons exacts supprimés (comparaison sur la ligne complète) ;
4. `client_id` unique après dédoublonnage ;
5. types numériques explicites, âge entier nullable ;
6. catégories autorisées pour `statut` et `type_compte` ;
7. bornes de cohérence (âge, revenu, solde, population) ;
8. une seule population par ville ;
9. identifiants directs (`nom`, `prenom`) retirés : ils ne quittent pas la couche Bronze.

Les âges manquants sont CONSERVÉS. Aucune imputation n'est faite ici : elle est
réalisée dans le pipeline de Machine Learning, sur les seules données
d'entraînement, pour éviter toute fuite de données.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import config
from src.utils.io import read_source_csv, write_json


class DataQualityError(ValueError):
    """Erreur levée lorsqu'une règle de qualité bloquante n'est pas respectée."""


def clean_clients(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Applique les règles Silver à un DataFrame Bronze. Retourne (silver, rapport)."""
    missing_columns = sorted(set(config.EXPECTED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise DataQualityError(f"Colonnes manquantes : {missing_columns}")

    df = df[config.EXPECTED_COLUMNS].copy()
    initial_rows = len(df)

    # 2. Nettoyage des espaces sur les variables texte
    for col in config.TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip()

    # 3. Doublons exacts, évalués sur la ligne complète (identifiants directs inclus)
    df = df.drop_duplicates().copy()
    duplicates_removed = initial_rows - len(df)

    # 4. Unicité de la clé technique
    df[config.TECHNICAL_KEY] = pd.to_numeric(df[config.TECHNICAL_KEY], errors="raise").astype("int64")
    conflicting_ids = int(df[config.TECHNICAL_KEY].duplicated().sum())
    if conflicting_ids:
        raise DataQualityError(
            f"{conflicting_ids} client_id restent dupliqués avec des valeurs différentes : "
            "arbitrage métier nécessaire avant de poursuivre."
        )

    # 5. Types numériques explicites
    for col in config.NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise")
    non_integer_ages = df["age"].dropna().mod(1).ne(0)
    if non_integer_ages.any():
        raise DataQualityError("Des âges non entiers ont été détectés.")
    df["age"] = df["age"].astype("Int64")            # entier nullable : les manquants restent <NA>
    df["population_ville"] = df["population_ville"].astype("int64")
    df["revenu_annuel"] = df["revenu_annuel"].astype("int64")
    df["solde"] = df["solde"].astype("float64")

    # 6. Catégories autorisées
    for col, allowed in config.ALLOWED_VALUES.items():
        if df[col].isna().any():
            raise DataQualityError(f"Valeurs manquantes dans {col}.")
        unexpected = set(df[col].unique()) - allowed
        if unexpected:
            raise DataQualityError(f"Valeurs inattendues dans {col} : {sorted(unexpected)}")

    # 7. Bornes de cohérence
    ages = df["age"].dropna()
    if ages.lt(config.AGE_MIN).any() or ages.gt(config.AGE_MAX).any():
        raise DataQualityError(f"Âges hors de l'intervalle [{config.AGE_MIN}, {config.AGE_MAX}].")
    if df["revenu_annuel"].lt(0).any():
        raise DataQualityError("Revenus annuels négatifs détectés.")
    if df["solde"].lt(0).any():
        raise DataQualityError("Soldes négatifs détectés.")
    if df["population_ville"].le(0).any():
        raise DataQualityError("Populations de ville non positives détectées.")

    # 8. Cohérence ville -> population
    populations_per_city = df.groupby("ville")["population_ville"].nunique()
    inconsistent = populations_per_city[populations_per_city > 1]
    if not inconsistent.empty:
        raise DataQualityError(
            f"Plusieurs populations pour une même ville : {sorted(inconsistent.index)}"
        )

    # Seul l'âge peut être manquant
    other_missing = df.drop(columns=["age"]).isna().sum()
    if other_missing.sum():
        raise DataQualityError(
            f"Valeurs manquantes inattendues : {other_missing[other_missing > 0].to_dict()}"
        )

    # 9. Pseudonymisation : retrait des identifiants directs
    silver = df[config.SILVER_COLUMNS].reset_index(drop=True)

    report = {
        "rows_bronze": int(initial_rows),
        "exact_duplicates_removed": int(duplicates_removed),
        "rows_silver": int(len(silver)),
        "unique_client_ids": int(silver[config.TECHNICAL_KEY].nunique()),
        "missing_ages_preserved": int(silver["age"].isna().sum()),
        "missing_age_rate_pct": round(float(silver["age"].isna().mean() * 100), 2),
        "status_counts": {str(k): int(v) for k, v in silver["statut"].value_counts().items()},
        "account_type_counts": {str(k): int(v) for k, v in silver["type_compte"].value_counts().items()},
        "distinct_cities": int(silver["ville"].nunique()),
        "direct_identifiers_removed": config.DIRECT_IDENTIFIERS,
        "columns": list(silver.columns),
        "dtypes": {col: str(dtype) for col, dtype in silver.dtypes.items()},
    }
    return silver, report


def _report_markdown(report: dict) -> str:
    lines = [
        "# Couche Silver — rapport d'exécution",
        "",
        "Rapport généré automatiquement par `src/silver/build_silver.py`.",
        "",
        "| Contrôle | Résultat |",
        "|---|---:|",
        f"| Lignes Bronze | {report['rows_bronze']:,} |".replace(",", " "),
        f"| Doublons exacts supprimés | {report['exact_duplicates_removed']} |",
        f"| Lignes Silver | {report['rows_silver']:,} |".replace(",", " "),
        f"| `client_id` uniques | {report['unique_client_ids']:,} |".replace(",", " "),
        f"| Âges manquants conservés | {report['missing_ages_preserved']} ({report['missing_age_rate_pct']} %) |",
        f"| Villes distinctes | {report['distinct_cities']} |",
        "",
        "## Répartition des statuts",
        "",
        "| Statut | Clients |",
        "|---|---:|",
    ]
    lines += [f"| {k} | {v:,} |".replace(",", " ") for k, v in sorted(report["status_counts"].items())]
    lines += ["", "## Répartition des types de compte", "", "| Type de compte | Clients |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |".replace(",", " ") for k, v in sorted(report["account_type_counts"].items())]
    lines += [
        "",
        "## Colonnes et types",
        "",
        "| Colonne | Type |",
        "|---|---|",
    ]
    lines += [f"| `{col}` | `{dtype}` |" for col, dtype in report["dtypes"].items()]
    lines += [
        "",
        f"Identifiants directs retirés : {', '.join(report['direct_identifiers_removed'])}.",
        "Toutes les règles bloquantes de `docs/data_quality_rules.md` sont respectées "
        "(sinon le script s'arrête avec une erreur).",
        "",
    ]
    return "\n".join(lines)


def build_silver(input_path: Path | str = config.BRONZE_FILE,
                 output_path: Path | str = config.SILVER_FILE,
                 report_dir: Path | str | None = config.SILVER_REPORT_DIR) -> tuple[pd.DataFrame, dict]:
    """Construit la couche Silver à partir du fichier Bronze et écrit le rapport qualité."""
    silver, report = clean_clients(read_source_csv(input_path))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(output_path, index=False, engine="pyarrow")

    if report_dir is not None:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        payload = {"run_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), **report}
        write_json(payload, report_dir / "silver_quality_report.json")
        (report_dir / "silver_quality_report.md").write_text(_report_markdown(report), encoding="utf-8")
    return silver, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Construction de la couche Silver.")
    parser.add_argument("--input", default=str(config.BRONZE_FILE))
    parser.add_argument("--output", default=str(config.SILVER_FILE))
    args = parser.parse_args()
    _, report = build_silver(args.input, args.output)
    print("=== SILVER ===")
    print(f"Lignes Bronze : {report['rows_bronze']} | Doublons supprimés : {report['exact_duplicates_removed']}")
    print(f"Clients conservés : {report['rows_silver']} | Âges manquants conservés : {report['missing_ages_preserved']}")
    print(f"Statuts : {report['status_counts']}")


if __name__ == "__main__":
    main()
