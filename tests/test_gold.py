import pytest

from src import config
from src.gold.build_gold_analytics import validate_gold_tables

SEGMENT_TABLES = [
    "gold_account_analysis", "gold_age_analysis", "gold_income_analysis",
    "gold_balance_analysis", "gold_city_analysis",
]
FORBIDDEN_COLUMNS = {*config.DIRECT_IDENTIFIERS, config.TECHNICAL_KEY}


def test_expected_tables_are_built(gold_tables):
    assert set(gold_tables) == {
        "gold_kpi_global", "gold_status_distribution", *SEGMENT_TABLES, "gold_fact_clients",
    }


def test_gold_reconciles_with_silver(gold_tables, silver):
    validate_gold_tables(gold_tables, silver)


@pytest.mark.parametrize("name", SEGMENT_TABLES)
def test_segment_totals_match_silver(gold_tables, silver, name):
    table = gold_tables[name]
    assert table["total_clients"].sum() == len(silver)
    assert table["clients_inactifs"].sum() == (silver["statut"] == "Inactif").sum()
    assert ((table["taux_activite_pct"] + table["taux_inactivite_pct"]).sub(100).abs() < 0.02).all()


def test_kpi_global_matches_silver(gold_tables, silver):
    kpi = gold_tables["gold_kpi_global"].iloc[0]
    assert kpi["total_clients"] == len(silver)
    assert kpi["ages_non_renseignes"] == silver["age"].isna().sum()
    # L'âge moyen est calculé sur les seuls âges renseignés (aucune imputation).
    assert kpi["age_moyen"] == pytest.approx(float(silver["age"].mean()), abs=0.01)
    assert kpi["solde_moyen"] == pytest.approx(silver["solde"].mean(), abs=0.01)


def test_missing_ages_have_their_own_bracket(gold_tables, silver):
    ages = gold_tables["gold_age_analysis"].set_index("tranche_age")
    assert ages.loc[config.AGE_MISSING_LABEL, "total_clients"] == silver["age"].isna().sum()
    assert list(gold_tables["gold_age_analysis"]["ordre"]) == sorted(gold_tables["gold_age_analysis"]["ordre"])


def test_no_identifier_in_any_gold_table(gold_tables, gold_ml):
    for table in [*gold_tables.values(), gold_ml]:
        assert not FORBIDDEN_COLUMNS & set(table.columns)


def test_gold_ml_structure(gold_ml, silver):
    assert list(gold_ml.columns) == [*config.ML_FEATURES, config.TARGET]
    assert len(gold_ml) == len(silver)
    assert set(gold_ml[config.TARGET].unique()) == config.ALLOWED_VALUES[config.TARGET]
    # Les âges manquants ne sont pas imputés avant la séparation train / test.
    assert gold_ml["age"].isna().sum() == silver["age"].isna().sum()
    assert gold_ml.drop(columns=["age"]).notna().all().all()
