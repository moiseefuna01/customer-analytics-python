"""Contrôles sur les fichiers réellement produits dans data/ (ignorés s'ils sont absents).

Ils vérifient que les couches présentes sur le disque sont cohérentes entre elles,
quelle que soit la source utilisée (données autorisées ou source synthétique).
"""
import json

import pandas as pd
import pytest

from src import config
from src.bronze.ingest_bronze import sha256_of
from src.gold.build_gold_analytics import validate_gold_tables

GOLD_TABLES = [
    "gold_kpi_global", "gold_status_distribution", "gold_account_analysis", "gold_age_analysis",
    "gold_income_analysis", "gold_balance_analysis", "gold_city_analysis", "gold_fact_clients",
]

pytestmark = pytest.mark.skipif(
    not config.SILVER_FILE.exists(),
    reason="Pipeline non exécuté : lancez `python -m src.pipeline`.",
)


def test_bronze_matches_its_metadata():
    metadata = json.loads(config.BRONZE_METADATA_FILE.read_text(encoding="utf-8"))
    assert sha256_of(config.BRONZE_FILE) == metadata["sha256"]


def test_silver_on_disk_respects_the_rules():
    silver = pd.read_parquet(config.SILVER_FILE)
    assert list(silver.columns) == config.SILVER_COLUMNS
    assert silver["client_id"].is_unique
    assert not silver.duplicated().any()
    assert silver.drop(columns=["age"]).notna().all().all()
    for col, allowed in config.ALLOWED_VALUES.items():
        assert set(silver[col].unique()) <= allowed


def test_gold_on_disk_reconciles_with_silver():
    silver = pd.read_parquet(config.SILVER_FILE)
    tables = {name: pd.read_parquet(config.GOLD_ANALYTICS_DIR / f"{name}.parquet") for name in GOLD_TABLES}
    validate_gold_tables(tables, silver)
    for name in GOLD_TABLES:
        csv = pd.read_csv(config.GOLD_ANALYTICS_DIR / f"{name}.csv", encoding="utf-8-sig")
        assert csv.shape == tables[name].shape, f"{name} : CSV et Parquet divergent"


def test_gold_ml_on_disk_matches_silver():
    silver = pd.read_parquet(config.SILVER_FILE)
    gold_ml = pd.read_parquet(config.GOLD_ML_FILE)
    assert len(gold_ml) == len(silver)
    assert list(gold_ml.columns) == [*config.ML_FEATURES, config.TARGET]
    assert gold_ml["age"].isna().sum() == silver["age"].isna().sum()
    gold_ml_csv = pd.read_csv(config.GOLD_ML_CSV_FILE, encoding="utf-8-sig")
    assert gold_ml_csv.shape == gold_ml.shape
    assert list(gold_ml_csv.columns) == list(gold_ml.columns)


def test_only_expected_files_in_gold_analytics():
    expected = {f"{name}.{ext}" for name in GOLD_TABLES for ext in ("csv", "parquet")}
    present = {path.name for path in config.GOLD_ANALYTICS_DIR.iterdir() if path.is_file()}
    assert present == expected, f"Fichiers inattendus : {sorted(present - expected)}"


def test_gold_ml_exports_both_formats():
    assert config.GOLD_ML_FILE.exists()
    assert config.GOLD_ML_CSV_FILE.exists()
