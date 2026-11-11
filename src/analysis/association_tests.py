"""Tests d'association entre les caractéristiques des clients et le statut observé.

    python -m src.analysis.association_tests

Objectif : distinguer les écarts réels des fluctuations d'échantillonnage avant
d'interpréter un classement de villes ou une « importance de variable ».

- Variables catégorielles : test du khi-deux d'indépendance + V de Cramér.
- Variables numériques : test de Mann-Whitney + taille d'effet AUC
  (probabilité qu'un client inactif ait une valeur plus élevée qu'un client actif ;
  0,5 = aucune différence).
- Les p-valeurs sont corrigées pour comparaisons multiples (méthode de Holm).

Ces tests mesurent des associations, jamais des causes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu

from src import config
from src.utils.io import markdown_table

CATEGORICAL_VARIABLES = ["ville", "type_compte", "tranche_age", "groupe_revenu", "groupe_solde"]
NUMERIC_VARIABLES = ["age", "revenu_annuel", "solde", "population_ville"]
ALPHA = 0.05


def holm_adjust(p_values: list[float]) -> list[float]:
    """Correction de Holm (contrôle du risque d'au moins un faux positif)."""
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running_max = 0.0
    for rank, index in enumerate(order):
        running_max = max(running_max, (len(p) - rank) * p[index])
        adjusted[index] = min(1.0, running_max)
    return adjusted.tolist()


def run_association_tests(fact: pd.DataFrame) -> pd.DataFrame:
    rows = []
    inactive = fact["statut"] == config.POSITIVE_CLASS

    for variable in CATEGORICAL_VARIABLES:
        contingency = pd.crosstab(fact[variable], fact["statut"])
        chi2, p_value, dof, _ = chi2_contingency(contingency)
        n = contingency.to_numpy().sum()
        cramers_v = float(np.sqrt(chi2 / (n * (min(contingency.shape) - 1))))
        rows.append({
            "variable": variable, "type": "catégorielle", "test": "khi-deux",
            "statistique": float(chi2), "ddl": int(dof), "p_valeur": float(p_value),
            "taille_effet": cramers_v, "mesure_effet": "V de Cramér (0 = aucune association)",
            "n": int(n),
        })

    for variable in NUMERIC_VARIABLES:
        values_inactive = fact.loc[inactive, variable].dropna().astype(float)
        values_active = fact.loc[~inactive, variable].dropna().astype(float)
        u_stat, p_value = mannwhitneyu(values_inactive, values_active, alternative="two-sided")
        auc = float(u_stat / (len(values_inactive) * len(values_active)))
        rows.append({
            "variable": variable, "type": "numérique", "test": "Mann-Whitney",
            "statistique": float(u_stat), "ddl": None, "p_valeur": float(p_value),
            "taille_effet": auc, "mesure_effet": "AUC (0,5 = aucune différence)",
            "n": int(len(values_inactive) + len(values_active)),
        })

    results = pd.DataFrame(rows)
    results["p_valeur_holm"] = holm_adjust(results["p_valeur"].tolist())
    results["significatif_5pct"] = results["p_valeur_holm"] < ALPHA
    return results


def _summary_markdown(results: pd.DataFrame) -> str:
    display = results[["variable", "test", "p_valeur", "p_valeur_holm", "taille_effet",
                       "mesure_effet", "significatif_5pct"]].copy()
    display["significatif_5pct"] = display["significatif_5pct"].map({True: "oui", False: "non"})
    significant = results.loc[results["significatif_5pct"], "variable"].tolist()
    if significant:
        verdict = (
            f"Association statistiquement significative (Holm, 5 %) pour : {', '.join(significant)}. "
            "Vérifier la taille d'effet avant toute interprétation métier."
        )
    else:
        verdict = (
            "Aucune association statistiquement significative n'a été détectée avec le statut "
            "(seuil 5 %, correction de Holm). Cela ne prouve pas une indépendance parfaite : les "
            "écarts observés entre segments sont compatibles avec les fluctuations d'échantillonnage "
            "et ne doivent pas être interprétés comme des différences métier établies."
        )
    return "\n".join([
        "# Tests d'association avec le statut observé",
        "",
        "Rapport généré automatiquement par `src/analysis/association_tests.py`.",
        "",
        markdown_table(display, float_format="{:.4f}"),
        "",
        "## Lecture",
        "",
        verdict,
        "",
        "Ces tests décrivent des associations univariées dans une photographie à un instant donné. "
        "Une absence de significativité n'est pas une preuve d'indépendance ; ces tests n'établissent "
        "aucune causalité et ne permettent aucune prévision.",
        "",
    ])


def build_association_report(fact_path: Path | str = config.GOLD_ANALYTICS_DIR / "gold_fact_clients.parquet",
                             report_dir: Path | str = config.ANALYSIS_REPORT_DIR) -> pd.DataFrame:
    results = run_association_tests(pd.read_parquet(fact_path))
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(report_dir / "association_tests.csv", index=False, encoding="utf-8-sig")
    (report_dir / "association_tests.md").write_text(_summary_markdown(results), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Tests d'association variables x statut.")
    parser.add_argument("--input", default=str(config.GOLD_ANALYTICS_DIR / "gold_fact_clients.parquet"))
    parser.add_argument("--report-dir", default=str(config.ANALYSIS_REPORT_DIR))
    args = parser.parse_args()
    results = build_association_report(args.input, args.report_dir)
    print("=== TESTS D'ASSOCIATION ===")
    print(results[["variable", "test", "p_valeur", "p_valeur_holm", "taille_effet"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
