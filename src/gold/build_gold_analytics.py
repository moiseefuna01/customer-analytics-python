"""Couche Gold Analytics : tables prêtes pour le reporting Power BI.

    python -m src.gold.build_gold_analytics

Tables produites dans data/gold/analytics/ (Parquet + CSV) :

| Table                      | Grain                    | Usage Power BI                    |
|----------------------------|--------------------------|-----------------------------------|
| gold_kpi_global            | 1 ligne                  | cartes KPI                        |
| gold_status_distribution   | statut                   | anneau Actif / Inactif            |
| gold_account_analysis      | type de compte           | comptes                           |
| gold_age_analysis          | tranche d'âge            | démographie                       |
| gold_income_analysis       | quartile de revenu       | démographie                       |
| gold_balance_analysis      | quartile de solde        | soldes                            |
| gold_city_analysis         | ville                    | géographie                        |
| gold_fact_clients          | 1 ligne par client       | filtres et interactions croisées  |

`gold_fact_clients` est dé-identifiée (ni nom, ni prénom, ni client_id) mais reste
une table au niveau individuel : elle ne doit pas être publiée.

Les âges manquants ne sont pas imputés : ils forment la tranche « Non renseigné »
et sont exclus du calcul de l'âge moyen.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src import config
from src.utils.io import write_table

SEGMENT_METRICS = [
    "total_clients", "clients_actifs", "clients_inactifs",
    "taux_activite_pct", "taux_inactivite_pct", "proportion_portefeuille_pct",
    "age_moyen", "revenu_annuel_moyen", "solde_moyen",
]


def build_fact_clients(silver: pd.DataFrame) -> pd.DataFrame:
    """Table de faits dé-identifiée : une ligne par client, enrichie des segments d'analyse."""
    fact = silver.drop(columns=[config.TECHNICAL_KEY]).copy()
    fact["age"] = fact["age"].astype("float64")
    for col in ["ville", "type_compte", "statut"]:
        fact[col] = fact[col].astype(object)

    tranche = pd.cut(fact["age"], bins=config.AGE_BINS, labels=config.AGE_LABELS, include_lowest=True)
    fact["tranche_age"] = tranche.astype(object).where(tranche.notna(), config.AGE_MISSING_LABEL)
    fact["groupe_revenu"] = pd.qcut(fact["revenu_annuel"], q=4, labels=config.INCOME_LABELS).astype(object)
    fact["groupe_solde"] = pd.qcut(fact["solde"], q=4, labels=config.BALANCE_LABELS).astype(object)
    fact["est_inactif"] = (fact["statut"] == config.POSITIVE_CLASS).astype("int64")

    return fact[[
        "age", "tranche_age", "ville", "population_ville",
        "revenu_annuel", "groupe_revenu", "type_compte",
        "solde", "groupe_solde", "statut", "est_inactif",
    ]]


def segment_table(fact: pd.DataFrame, by: str, order: list[str] | None = None,
                  extra: dict | None = None) -> pd.DataFrame:
    """Indicateurs standard par segment. `order` fixe l'ordre d'affichage (colonne `ordre`)."""
    aggregations = {
        "total_clients": ("statut", "size"),
        "clients_inactifs": ("est_inactif", "sum"),
        "age_moyen": ("age", "mean"),                      # moyenne sur les âges renseignés
        "revenu_annuel_moyen": ("revenu_annuel", "mean"),
        "solde_moyen": ("solde", "mean"),
        **(extra or {}),
    }
    table = fact.groupby(by, observed=True).agg(**aggregations).reset_index()
    table["clients_inactifs"] = table["clients_inactifs"].astype("int64")
    table["clients_actifs"] = table["total_clients"] - table["clients_inactifs"]
    table["taux_activite_pct"] = table["clients_actifs"] / table["total_clients"] * 100
    table["taux_inactivite_pct"] = table["clients_inactifs"] / table["total_clients"] * 100
    table["proportion_portefeuille_pct"] = table["total_clients"] / len(fact) * 100

    extra_columns = list((extra or {}).keys())
    table = table[[by, *SEGMENT_METRICS, *extra_columns]]
    float_columns = table.select_dtypes(include="float").columns
    table[float_columns] = table[float_columns].round(2)

    if order is not None:
        rank = {label: position for position, label in enumerate(order, start=1)}
        table.insert(0, "ordre", table[by].map(rank).astype("int64"))
        table = table.sort_values("ordre")
    else:
        table = table.sort_values("total_clients", ascending=False)
    return table.reset_index(drop=True)


def build_gold_tables(silver: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Construit l'ensemble des tables Gold Analytics à partir de la couche Silver."""
    fact = build_fact_clients(silver)
    total = len(fact)
    inactifs = int(fact["est_inactif"].sum())
    actifs = total - inactifs

    kpi_global = pd.DataFrame([{
        "total_clients": total,
        "clients_actifs": actifs,
        "clients_inactifs": inactifs,
        "taux_activite_pct": round(actifs / total * 100, 2),
        "taux_inactivite_pct": round(inactifs / total * 100, 2),
        "age_moyen": round(float(fact["age"].mean()), 2),
        "ages_non_renseignes": int(fact["age"].isna().sum()),
        "revenu_annuel_moyen": round(float(fact["revenu_annuel"].mean()), 2),
        "solde_moyen": round(float(fact["solde"].mean()), 2),
        "solde_median": round(float(fact["solde"].median()), 2),
        "solde_total": round(float(fact["solde"].sum()), 2),
        "nombre_villes": int(fact["ville"].nunique()),
    }])

    status_distribution = pd.DataFrame({
        "statut": ["Actif", "Inactif"],
        "nombre_clients": [actifs, inactifs],
        "proportion_pct": [round(actifs / total * 100, 2), round(inactifs / total * 100, 2)],
    })

    age_order = [*config.AGE_LABELS, config.AGE_MISSING_LABEL]
    present_age_order = [label for label in age_order if label in set(fact["tranche_age"])]

    return {
        "gold_kpi_global": kpi_global,
        "gold_status_distribution": status_distribution,
        "gold_account_analysis": segment_table(fact, "type_compte"),
        "gold_age_analysis": segment_table(fact, "tranche_age", order=present_age_order),
        "gold_income_analysis": segment_table(
            fact, "groupe_revenu", order=config.INCOME_LABELS,
            extra={"revenu_min": ("revenu_annuel", "min"), "revenu_max": ("revenu_annuel", "max")},
        ),
        "gold_balance_analysis": segment_table(
            fact, "groupe_solde", order=config.BALANCE_LABELS,
            extra={"solde_min": ("solde", "min"), "solde_max": ("solde", "max")},
        ),
        "gold_city_analysis": segment_table(
            fact, "ville", extra={"population_ville": ("population_ville", "first")},
        ),
        "gold_fact_clients": fact,
    }


def validate_gold_tables(tables: dict[str, pd.DataFrame], silver: pd.DataFrame) -> None:
    """Réconciliation Gold <-> Silver. Lève AssertionError en cas d'écart."""
    total = len(silver)
    inactifs = int((silver["statut"] == config.POSITIVE_CLASS).sum())

    kpi = tables["gold_kpi_global"].iloc[0]
    assert kpi["total_clients"] == total, "KPI : total clients différent de Silver"
    assert kpi["clients_actifs"] + kpi["clients_inactifs"] == total, "KPI : actifs + inactifs != total"
    assert tables["gold_status_distribution"]["nombre_clients"].sum() == total

    for name in ["gold_account_analysis", "gold_age_analysis", "gold_income_analysis",
                 "gold_balance_analysis", "gold_city_analysis"]:
        table = tables[name]
        assert table["total_clients"].sum() == total, f"{name} : total différent de Silver"
        assert table["clients_inactifs"].sum() == inactifs, f"{name} : inactifs différents de Silver"
        assert (table["clients_actifs"] + table["clients_inactifs"] == table["total_clients"]).all()
        assert abs(table["proportion_portefeuille_pct"].sum() - 100) < 0.1, f"{name} : proportions != 100 %"

    assert len(tables["gold_fact_clients"]) == total
    forbidden = {*config.DIRECT_IDENTIFIERS, config.TECHNICAL_KEY}
    for name, table in tables.items():
        leaked = forbidden & set(table.columns)
        assert not leaked, f"{name} contient des identifiants : {sorted(leaked)}"


def build_gold_analytics(silver_path: Path | str = config.SILVER_FILE,
                         output_dir: Path | str = config.GOLD_ANALYTICS_DIR) -> dict[str, pd.DataFrame]:
    silver = pd.read_parquet(silver_path)
    tables = build_gold_tables(silver)
    validate_gold_tables(tables, silver)
    for name, table in tables.items():
        write_table(table, output_dir, name)
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description="Construction des tables Gold Analytics.")
    parser.add_argument("--input", default=str(config.SILVER_FILE))
    parser.add_argument("--output-dir", default=str(config.GOLD_ANALYTICS_DIR))
    args = parser.parse_args()
    tables = build_gold_analytics(args.input, args.output_dir)
    print("=== GOLD ANALYTICS ===")
    for name, table in tables.items():
        print(f"{name:<28} {table.shape[0]:>6} lignes x {table.shape[1]} colonnes")
    print("Réconciliation Gold <-> Silver : OK")


if __name__ == "__main__":
    main()
