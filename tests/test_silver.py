import pandas as pd
import pytest

from src import config
from src.silver.build_silver import DataQualityError, clean_clients
from tests.conftest import MISSING_RATE, N_DUPLICATES, N_ROWS


def test_exact_duplicates_are_removed(silver, workspace):
    assert len(silver) == N_ROWS
    assert workspace["silver_report"]["exact_duplicates_removed"] == N_DUPLICATES
    assert not silver.duplicated().any()


def test_client_ids_are_unique(silver):
    assert silver["client_id"].is_unique


def test_missing_ages_are_preserved_not_imputed(silver):
    assert silver["age"].isna().sum() == int(N_ROWS * MISSING_RATE)
    assert str(silver["age"].dtype) == "Int64"


def test_direct_identifiers_do_not_reach_silver(silver):
    assert list(silver.columns) == config.SILVER_COLUMNS
    assert not set(config.DIRECT_IDENTIFIERS) & set(silver.columns)


def test_categories_and_ranges_are_valid(silver):
    for col, allowed in config.ALLOWED_VALUES.items():
        assert set(silver[col].unique()) <= allowed
    assert silver["age"].dropna().between(config.AGE_MIN, config.AGE_MAX).all()
    assert silver["revenu_annuel"].ge(0).all()
    assert silver["solde"].ge(0).all()
    assert silver["population_ville"].gt(0).all()


def test_silver_parquet_round_trip(workspace, silver):
    reloaded = pd.read_parquet(workspace["silver_path"])
    assert reloaded.shape == silver.shape
    assert reloaded["age"].isna().sum() == silver["age"].isna().sum()


def test_text_values_are_stripped(raw_df):
    dirty = raw_df.copy()
    dirty["statut"] = " " + dirty["statut"] + "  "
    cleaned, _ = clean_clients(dirty)
    assert set(cleaned["statut"].unique()) <= config.ALLOWED_VALUES["statut"]


def _corrupt(raw_df, column, value):
    corrupted = raw_df.copy()
    corrupted[column] = corrupted[column].astype(object)
    corrupted.loc[0, column] = value
    return corrupted


@pytest.mark.parametrize("column, value", [
    ("statut", "Suspendu"),
    ("type_compte", "Inconnu"),
    ("age", 12),
    ("age", 150),
    ("revenu_annuel", -1),
    ("solde", -0.01),
    ("population_ville", 0),
])
def test_blocking_rules_raise(raw_df, column, value):
    with pytest.raises(DataQualityError):
        clean_clients(_corrupt(raw_df, column, value))


def test_conflicting_client_id_raises(raw_df):
    conflict = raw_df.copy()
    conflict.loc[1, "client_id"] = conflict.loc[0, "client_id"]
    with pytest.raises(DataQualityError, match="client_id"):
        clean_clients(conflict)


def test_missing_column_raises(raw_df):
    with pytest.raises(DataQualityError, match="solde"):
        clean_clients(raw_df.drop(columns=["solde"]))
