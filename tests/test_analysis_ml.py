import numpy as np
import pytest

from src import config
from src.analysis.association_tests import holm_adjust, run_association_tests
from src.ml.train_models import BASELINE_NAME, evaluate_models, load_xy, make_pipeline
from sklearn.linear_model import LogisticRegression


def test_holm_adjustment_is_monotone_and_bounded():
    adjusted = holm_adjust([0.01, 0.04, 0.03, 0.5])
    assert adjusted == pytest.approx([0.04, 0.09, 0.09, 0.5])
    assert all(0 <= p <= 1 for p in adjusted)


def test_association_tests_cover_all_variables(gold_tables):
    results = run_association_tests(gold_tables["gold_fact_clients"])
    assert len(results) == 9
    assert results["p_valeur"].between(0, 1).all()
    assert (results["p_valeur_holm"] >= results["p_valeur"] - 1e-12).all()


def test_target_is_never_a_feature(gold_ml):
    X, y = load_xy(gold_ml)
    assert config.TARGET not in X.columns
    assert set(y.unique()) == {0, 1}
    assert y.sum() == (gold_ml[config.TARGET] == config.POSITIVE_CLASS).sum()


def test_pipeline_handles_missing_ages(gold_ml):
    X, y = load_xy(gold_ml)
    assert X["age"].isna().any()
    pipeline = make_pipeline(LogisticRegression(max_iter=1000)).fit(X, y)
    probabilities = pipeline.predict_proba(X)[:, 1]
    assert np.isfinite(probabilities).all()


def test_model_evaluation_runs_and_includes_baseline(gold_ml):
    X, y = load_xy(gold_ml)
    results = evaluate_models(X, y, n_permutations=5, cv_folds=3)
    comparison = results["comparison"]
    assert BASELINE_NAME in set(comparison["modele"])
    assert len(comparison) == 5
    metric_columns = [c for c in comparison.columns if c != "modele"]
    assert comparison[metric_columns].apply(lambda s: s.between(0, 1)).all().all()
    # Données synthétiques sans signal : le pipeline ne doit pas en inventer.
    assert results["signal_detected"] is False
    assert 0 <= results["permutation_test"]["p_valeur"] <= 1
