"""Fixtures partagées : un mini-projet synthétique construit dans un dossier temporaire.

Les tests unitaires n'ont donc besoin d'aucune donnée privée et tournent en CI.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.bronze.ingest_bronze import ingest_bronze
from src.gold.build_gold_analytics import build_gold_tables
from src.gold.build_gold_ml import build_ml_dataset
from src.silver.build_silver import build_silver
from src.utils.sample_data import generate_sample

N_ROWS, N_DUPLICATES, MISSING_RATE = 600, 5, 0.02


@pytest.fixture(scope="session")
def raw_df() -> pd.DataFrame:
    return generate_sample(rows=N_ROWS, duplicates=N_DUPLICATES, missing_age_rate=MISSING_RATE, seed=7)


@pytest.fixture(scope="session")
def workspace(tmp_path_factory, raw_df):
    """Exécute Bronze puis Silver sur la source synthétique."""
    root = tmp_path_factory.mktemp("projet")
    raw_path = root / "raw" / "clients.csv"
    raw_path.parent.mkdir()
    raw_df.to_csv(raw_path, index=False, encoding="utf-8")

    bronze_path = root / "bronze" / "clients.csv"
    metadata = ingest_bronze(raw_path, bronze_path)
    silver_path = root / "silver" / "clients_clean.parquet"
    silver, report = build_silver(bronze_path, silver_path, report_dir=root / "reports")
    return {
        "root": root, "raw_path": raw_path, "bronze_path": bronze_path,
        "silver_path": silver_path, "metadata": metadata,
        "silver": silver, "silver_report": report,
    }


@pytest.fixture(scope="session")
def silver(workspace) -> pd.DataFrame:
    return workspace["silver"]


@pytest.fixture(scope="session")
def gold_tables(silver) -> dict[str, pd.DataFrame]:
    return build_gold_tables(silver)


@pytest.fixture(scope="session")
def gold_ml(silver) -> pd.DataFrame:
    return build_ml_dataset(silver)
