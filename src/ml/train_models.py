"""Comparaison de modèles de classification du statut OBSERVÉ (Actif / Inactif).

    python -m src.ml.train_models

Protocole :
1. séparation train / test stratifiée (80 / 20, graine fixe) ;
2. prétraitement DANS le pipeline (imputation médiane de l'âge, standardisation,
   encodage one-hot) : il n'est appris que sur les données d'entraînement ;
3. baseline `DummyClassifier` + 4 algorithmes ;
4. validation croisée stratifiée sur le train pour comparer les modèles
   (le jeu de test ne sert pas à choisir un modèle) ;
5. évaluation unique sur le test ;
6. test de permutation : la performance est-elle distinguable du hasard ?

Le statut est une photographie : ce travail ne prédit ni churn ni inactivité future.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedKFold, cross_validate, permutation_test_score, train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src import config
from src.utils.io import markdown_table, write_json

BASELINE_NAME = "Baseline (classe majoritaire)"
SIGNAL_AUC_THRESHOLD = 0.55     # en dessous : pouvoir discriminant négligeable
ALPHA = 0.05


def load_xy(gold_ml: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """X = variables explicatives ; y = 1 si Inactif (classe d'intérêt), 0 si Actif."""
    X = gold_ml[config.ML_FEATURES].copy()
    y = (gold_ml[config.TARGET] == config.POSITIVE_CLASS).astype(int)
    return X, y


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = OneHotEncoder(handle_unknown="ignore")
    return ColumnTransformer([
        ("num", numeric, config.NUMERIC_FEATURES),
        ("cat", categorical, config.CATEGORICAL_FEATURES),
    ])


def get_models(random_state: int = config.RANDOM_STATE) -> dict:
    return {
        BASELINE_NAME: DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=random_state),
        "Decision Tree": DecisionTreeClassifier(random_state=random_state),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=random_state, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(random_state=random_state),
    }


def make_pipeline(model) -> Pipeline:
    return Pipeline([("preprocessor", build_preprocessor()), ("classifier", model)])


def evaluate_models(X: pd.DataFrame, y: pd.Series, n_permutations: int = 200,
                    cv_folds: int = config.CV_FOLDS,
                    random_state: int = config.RANDOM_STATE) -> dict:
    """Entraîne et évalue tous les modèles. Retourne tableaux, matrices et test de permutation."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.TEST_SIZE, random_state=random_state, stratify=y,
    )
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)

    rows, matrices = [], {}
    for name, model in get_models(random_state).items():
        pipeline = make_pipeline(model)
        cv_scores = cross_validate(
            pipeline, X_train, y_train, cv=cv,
            scoring={"roc_auc": "roc_auc", "f1": "f1", "accuracy": "accuracy"},
        )
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]
        rows.append({
            "modele": name,
            "cv_roc_auc_moyenne": cv_scores["test_roc_auc"].mean(),
            "cv_roc_auc_ecart_type": cv_scores["test_roc_auc"].std(),
            "cv_f1_inactif": cv_scores["test_f1"].mean(),
            "cv_accuracy": cv_scores["test_accuracy"].mean(),
            "test_accuracy": accuracy_score(y_test, y_pred),
            "test_precision_inactif": precision_score(y_test, y_pred, zero_division=0),
            "test_recall_inactif": recall_score(y_test, y_pred, zero_division=0),
            "test_f1_inactif": f1_score(y_test, y_pred, zero_division=0),
            "test_roc_auc": roc_auc_score(y_test, y_proba),
        })
        matrices[name] = confusion_matrix(y_test, y_pred, labels=[0, 1])

    comparison = (
        pd.DataFrame(rows)
        .sort_values("cv_roc_auc_moyenne", ascending=False)
        .reset_index(drop=True)
    )

    # Test de permutation sur le modèle le plus simple : si les variables contiennent
    # un signal, le score réel doit dépasser les scores obtenus avec une cible mélangée.
    score, permutation_scores, p_value = permutation_test_score(
        make_pipeline(LogisticRegression(max_iter=1000, random_state=random_state)),
        X_train, y_train, scoring="roc_auc", cv=cv,
        n_permutations=n_permutations, random_state=random_state, n_jobs=-1,
    )
    permutation = {
        "modele": "Logistic Regression",
        "roc_auc_reel": float(score),
        "roc_auc_permutations_moyenne": float(np.mean(permutation_scores)),
        "roc_auc_permutations_p95": float(np.quantile(permutation_scores, 0.95)),
        "n_permutations": int(n_permutations),
        "p_valeur": float(p_value),
    }

    trained = comparison[comparison["modele"] != BASELINE_NAME]
    best = trained.iloc[0]
    signal_detected = bool(
        best["cv_roc_auc_moyenne"] >= SIGNAL_AUC_THRESHOLD and p_value < ALPHA
    )
    return {
        "comparison": comparison,
        "confusion_matrices": matrices,
        "permutation_test": permutation,
        "best_model": str(best["modele"]),
        "best_cv_roc_auc": float(best["cv_roc_auc_moyenne"]),
        "signal_detected": signal_detected,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "test_majority_rate": float(max(y_test.mean(), 1 - y_test.mean())),
    }


def plot_confusion_matrices(matrices: dict, path: Path) -> None:
    names = [name for name in matrices if name != BASELINE_NAME]
    fig, axes = plt.subplots(1, len(names), figsize=(4 * len(names), 4), squeeze=False)
    for ax, name in zip(axes[0], names):
        matrix = matrices[name]
        ax.imshow(matrix, cmap="Blues")
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, f"{value}", ha="center", va="center",
                    color="white" if value > matrix.max() / 2 else "black", fontsize=12)
        ax.set_xticks([0, 1], labels=["Actif", "Inactif"])
        ax.set_yticks([0, 1], labels=["Actif", "Inactif"])
        ax.set_xlabel("Statut prédit")
        ax.set_ylabel("Statut réel")
        ax.set_title(name, fontsize=11)
    fig.suptitle("Matrices de confusion — jeu de test")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_cv_auc(comparison: pd.DataFrame, path: Path) -> None:
    data = comparison.sort_values("cv_roc_auc_moyenne")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(data["modele"], data["cv_roc_auc_moyenne"],
            xerr=data["cv_roc_auc_ecart_type"], color="#4C72B0", capsize=4)
    ax.axvline(0.5, color="red", linestyle="--", label="Hasard (0,5)")
    ax.set_xlim(0.40, 0.65)
    ax.set_xlabel("ROC-AUC — validation croisée (moyenne ± écart-type)")
    ax.set_title("Pouvoir discriminant des modèles")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _summary_markdown(results: dict) -> str:
    comparison = results["comparison"]
    permutation = results["permutation_test"]
    if results["signal_detected"]:
        verdict = (
            f"Le modèle présentant le ROC-AUC CV le plus élevé ({results['best_model']}) obtient "
            f"{results['best_cv_roc_auc']:.3f} en validation croisée, et le test de permutation "
            f"rejette l'hypothèse d'absence de signal (p = {permutation['p_valeur']:.3f}). "
            "Les variables disponibles contiennent une information sur le statut observé ; "
            "sa portée opérationnelle reste à évaluer."
        )
    else:
        verdict = (
            f"Aucun modèle ne se distingue du hasard : le ROC-AUC CV maximal observé "
            f"est de {results['best_cv_roc_auc']:.3f} ({results['best_model']}), pour 0,5 attendu "
            f"au hasard, et le test de permutation ne détecte pas de signal "
            f"(p = {permutation['p_valeur']:.3f}). Les écarts entre modèles sont du même ordre que "
            "la variabilité entre plis : il n'y a pas de « meilleur modèle » à retenir, et les "
            "importances de variables ne sont pas interprétables. Conclusion : les variables "
            "disponibles (âge, ville, revenu, type de compte, solde) ne permettent pas de "
            "distinguer les clients actifs des clients inactifs dans ce jeu de données."
        )
    return "\n".join([
        "# Comparaison des modèles de classification",
        "",
        "Rapport généré automatiquement par `src/ml/train_models.py`.",
        "",
        f"- Cible : statut observé, classe d'intérêt = `{config.POSITIVE_CLASS}`.",
        f"- Entraînement : {results['n_train']} clients ; test : {results['n_test']} clients "
        f"(séparation stratifiée, graine {config.RANDOM_STATE}).",
        f"- Validation croisée stratifiée à {config.CV_FOLDS} plis sur le jeu d'entraînement.",
        f"- Accuracy d'une prédiction constante sur le test : {results['test_majority_rate']:.3f}.",
        "",
        "## Résultats",
        "",
        markdown_table(comparison),
        "",
        "## Test de permutation (Logistic Regression, ROC-AUC)",
        "",
        f"- ROC-AUC réel : {permutation['roc_auc_reel']:.3f}",
        f"- ROC-AUC avec cible mélangée : moyenne {permutation['roc_auc_permutations_moyenne']:.3f}, "
        f"95e centile {permutation['roc_auc_permutations_p95']:.3f} "
        f"({permutation['n_permutations']} permutations)",
        f"- p-valeur : {permutation['p_valeur']:.3f}",
        "",
        "## Conclusion",
        "",
        verdict,
        "",
        "Rappel : le statut est observé à un instant donné, sans historique. Ces résultats ne "
        "constituent ni une prévision d'inactivité future ni une preuve de causalité.",
        "",
        "Figures : `confusion_matrices.png`, `cv_roc_auc.png`.",
        "",
    ])


def train_and_report(gold_ml_path: Path | str = config.GOLD_ML_FILE,
                     report_dir: Path | str = config.ML_REPORT_DIR,
                     n_permutations: int = 200) -> dict:
    X, y = load_xy(pd.read_parquet(gold_ml_path))
    results = evaluate_models(X, y, n_permutations=n_permutations)

    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    results["comparison"].round(4).to_csv(
        report_dir / "model_comparison.csv", index=False, encoding="utf-8-sig",
    )
    write_json(
        {key: results[key] for key in [
            "permutation_test", "best_model", "best_cv_roc_auc", "signal_detected",
            "n_train", "n_test", "test_majority_rate",
        ]},
        report_dir / "ml_summary.json",
    )
    (report_dir / "ml_summary.md").write_text(_summary_markdown(results), encoding="utf-8")
    plot_confusion_matrices(results["confusion_matrices"], report_dir / "confusion_matrices.png")
    plot_cv_auc(results["comparison"], report_dir / "cv_roc_auc.png")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparaison de modèles de classification.")
    parser.add_argument("--input", default=str(config.GOLD_ML_FILE))
    parser.add_argument("--report-dir", default=str(config.ML_REPORT_DIR))
    parser.add_argument("--permutations", type=int, default=200)
    args = parser.parse_args()
    results = train_and_report(args.input, args.report_dir, args.permutations)
    print("=== MACHINE LEARNING ===")
    print(results["comparison"].round(3).to_string(index=False))
    print(f"\nTest de permutation : p = {results['permutation_test']['p_valeur']:.3f}")
    print("Signal détecté :", "oui" if results["signal_detected"] else "non")


if __name__ == "__main__":
    main()
