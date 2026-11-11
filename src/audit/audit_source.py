"""Audit reproductible de la source, sans jamais exporter de nom ni de prénom.

    python -m src.audit.audit_source --input data/raw/clients.csv

Le script ne modifie aucune donnée. Il écrit un rapport JSON et un rapport
Markdown dans reports/audit/ : schéma, valeurs manquantes, doublons, contrôles
de cohérence, catégories inattendues et résumé numérique.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.utils.io import read_source_csv, write_json


def _json_safe(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def run_audit(input_path: Path | str = config.RAW_FILE,
              output_dir: Path | str = config.AUDIT_REPORT_DIR) -> dict:
    input_path, output_dir = Path(input_path), Path(output_dir)
    df = read_source_csv(input_path)

    missing_columns = sorted(set(config.EXPECTED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Colonnes attendues absentes : {missing_columns}")

    exact_duplicates = int(df.duplicated(keep="first").sum())
    df_dedup = df.drop_duplicates()
    conflicting_ids = int(df_dedup["client_id"].duplicated().sum())

    categorical = {}
    for col in df.select_dtypes(exclude=[np.number]).columns:
        if col in config.DIRECT_IDENTIFIERS:
            # Ne jamais exposer de nom ni de prénom dans un rapport.
            categorical[col] = {
                "distinct_values": int(df[col].nunique()),
                "note": "Identifiant direct : valeurs volontairement omises",
            }
        else:
            categorical[col] = {
                "distinct_values": int(df[col].nunique()),
                "top_values": {str(k): int(v) for k, v in df[col].value_counts(dropna=False).head(10).items()},
            }

    unexpected_categories = {
        col: sorted(set(df[col].dropna().astype(str).str.strip().unique()) - allowed)
        for col, allowed in config.ALLOWED_VALUES.items()
    }
    coherence_checks = {
        f"age < {config.AGE_MIN}": int(df["age"].lt(config.AGE_MIN).sum()),
        f"age > {config.AGE_MAX}": int(df["age"].gt(config.AGE_MAX).sum()),
        "revenu_annuel < 0": int(df["revenu_annuel"].lt(0).sum()),
        "solde < 0": int(df["solde"].lt(0).sum()),
        "population_ville <= 0": int(df["population_ville"].le(0).sum()),
        "villes avec plusieurs populations": int(
            (df.groupby("ville")["population_ville"].nunique() > 1).sum()
        ),
    }
    missing_age_by_status = {
        str(status): {"clients": int(len(group)), "ages_manquants": int(group["age"].isna().sum())}
        for status, group in df_dedup.groupby("statut")
    }
    numeric_summary = {
        col: {str(k): _json_safe(v) for k, v in df[col].describe().items()}
        for col in config.NUMERIC_COLUMNS
    }

    report = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file_name": input_path.name,
        "source_file_size_bytes": input_path.stat().st_size,
        "row_count_raw": int(len(df)),
        "column_count": int(df.shape[1]),
        "columns": list(map(str, df.columns)),
        "unexpected_columns": sorted(set(df.columns) - set(config.EXPECTED_COLUMNS)),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "missing_values": {str(k): int(v) for k, v in df.isna().sum().items()},
        "missing_value_cells_total": int(df.isna().sum().sum()),
        "exact_duplicate_rows_after_first": exact_duplicates,
        "row_count_after_exact_deduplication": int(len(df_dedup)),
        "unique_client_ids": int(df["client_id"].nunique()),
        "conflicting_client_ids_after_deduplication": conflicting_ids,
        "unexpected_categories": unexpected_categories,
        "coherence_checks": coherence_checks,
        "missing_age_by_status_after_deduplication": missing_age_by_status,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical,
        "status_counts_raw": {str(k): int(v) for k, v in df["statut"].value_counts().items()},
        "status_counts_after_exact_deduplication": {
            str(k): int(v) for k, v in df_dedup["statut"].value_counts().items()
        },
        "privacy_note": "Les identifiants directs (nom, prenom) ne sont jamais écrits dans ce rapport.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(report, output_dir / "audit_summary.json")
    (output_dir / "audit_summary.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _markdown(report: dict) -> str:
    lines = [
        "# Audit de la source",
        "",
        "Rapport généré automatiquement par `src/audit/audit_source.py`. Aucune donnée n'a été modifiée.",
        "",
        f"- Fichier source : `{report['source_file_name']}` (contenu CSV)",
        f"- Lignes brutes : **{report['row_count_raw']}**",
        f"- Colonnes : **{report['column_count']}**",
        f"- Doublons exacts (après la première occurrence) : **{report['exact_duplicate_rows_after_first']}**",
        f"- Lignes après dédoublonnage exact : **{report['row_count_after_exact_deduplication']}**",
        f"- `client_id` distincts : **{report['unique_client_ids']}**",
        f"- `client_id` en conflit après dédoublonnage : **{report['conflicting_client_ids_after_deduplication']}**",
        f"- Cellules manquantes : **{report['missing_value_cells_total']}**",
        "",
        "## Colonnes",
        "",
        "| Colonne | Type lu | Valeurs manquantes |",
        "|---|---|---:|",
    ]
    lines += [
        f"| `{col}` | `{report['dtypes'][col]}` | {report['missing_values'][col]} |"
        for col in report["columns"]
    ]
    lines += ["", "## Statuts", "", "| Statut | Lignes brutes | Après dédoublonnage |", "|---|---:|---:|"]
    lines += [
        f"| {status} | {count} | {report['status_counts_after_exact_deduplication'].get(status, 0)} |"
        for status, count in sorted(report["status_counts_raw"].items())
    ]
    lines += ["", "## Âges manquants par statut (après dédoublonnage)", "",
              "| Statut | Clients | Âges manquants |", "|---|---:|---:|"]
    lines += [
        f"| {status} | {values['clients']} | {values['ages_manquants']} |"
        for status, values in sorted(report["missing_age_by_status_after_deduplication"].items())
    ]
    lines += ["", "## Contrôles de cohérence", "", "| Contrôle | Lignes concernées |", "|---|---:|"]
    lines += [f"| {label} | {count} |" for label, count in report["coherence_checks"].items()]
    lines += ["", "## Catégories inattendues", ""]
    lines += [
        f"- `{col}` : {values if values else 'aucune'}"
        for col, values in report["unexpected_categories"].items()
    ]
    lines += ["", "## Résumé numérique", "",
              "| Colonne | Effectif | Moyenne | Écart-type | Min | Médiane | Max |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for col, stats in report["numeric_summary"].items():
        lines.append(
            f"| `{col}` | {stats['count']:.0f} | {stats['mean']:.2f} | {stats['std']:.2f} | "
            f"{stats['min']:.2f} | {stats['50%']:.2f} | {stats['max']:.2f} |"
        )
    lines += [
        "",
        "## Limites d'interprétation",
        "",
        "- Les données sont une photographie à un instant donné : le statut est une étiquette observée, "
        "pas un événement futur.",
        "- Une association entre une caractéristique et le statut n'est pas une preuve de causalité.",
        "- La suppression des doublons exacts est une règle technique ; elle doit être confirmée par le métier.",
        "- La définition et l'unité des variables métier restent à confirmer (voir `docs/data_dictionary.md`).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit de la source sans export d'identifiants directs.")
    parser.add_argument("--input", default=str(config.RAW_FILE), help="Chemin du CSV source.")
    parser.add_argument("--output-dir", default=str(config.AUDIT_REPORT_DIR))
    args = parser.parse_args()
    report = run_audit(args.input, args.output_dir)
    print("=== AUDIT DE LA SOURCE ===")
    print(f"Lignes : {report['row_count_raw']} | Colonnes : {report['column_count']}")
    print(f"Doublons exacts : {report['exact_duplicate_rows_after_first']} | "
          f"Cellules manquantes : {report['missing_value_cells_total']}")
    print(f"Contrôles de cohérence : {report['coherence_checks']}")
    print(f"Catégories inattendues : {report['unexpected_categories']}")


if __name__ == "__main__":
    main()
