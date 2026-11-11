"""Exécute tout le workflow, de la source aux rapports, en une commande.

    python -m src.pipeline                      # source : data/raw/clients.csv
    python -m src.pipeline --source chemin.csv  # autre fichier source
    python -m src.pipeline --skip-ml            # sans la modélisation

Étapes : audit -> Bronze -> Silver -> Gold Analytics -> Gold ML ->
tests d'association -> comparaison de modèles.
"""
from __future__ import annotations

import argparse
import time

from src import config
from src.analysis.association_tests import build_association_report
from src.audit.audit_source import run_audit
from src.bronze.ingest_bronze import ingest_bronze
from src.gold.build_gold_analytics import build_gold_analytics
from src.gold.build_gold_ml import build_gold_ml
from src.ml.train_models import train_and_report
from src.silver.build_silver import build_silver


def run_pipeline(source: str = str(config.RAW_FILE), skip_ml: bool = False,
                 n_permutations: int = 200) -> None:
    start = time.perf_counter()

    print("[1/7] Audit de la source")
    audit = run_audit(source)
    print(f"      {audit['row_count_raw']} lignes, {audit['exact_duplicate_rows_after_first']} doublons exacts, "
          f"{audit['missing_value_cells_total']} cellules manquantes")

    print("[2/7] Bronze : copie fidèle + métadonnées")
    bronze = ingest_bronze(source)
    print(f"      SHA-256 {bronze['sha256'][:16]}…")

    print("[3/7] Silver : nettoyage, validation, pseudonymisation")
    _, silver_report = build_silver()
    print(f"      {silver_report['rows_silver']} clients, {silver_report['missing_ages_preserved']} âges manquants conservés")

    print("[4/7] Gold Analytics : tables de reporting")
    tables = build_gold_analytics()
    print(f"      {len(tables)} tables, réconciliation avec Silver OK")

    print("[5/7] Gold ML : table de modélisation")
    gold_ml = build_gold_ml()
    print(f"      {len(gold_ml)} lignes, {gold_ml.shape[1] - 1} variables + cible")

    print("[6/7] Tests d'association")
    tests = build_association_report()
    print(f"      {int(tests['significatif_5pct'].sum())} association(s) significative(s) sur {len(tests)}")

    if skip_ml:
        print("[7/7] Modélisation ignorée (--skip-ml)")
    else:
        print("[7/7] Comparaison de modèles (validation croisée + test de permutation)")
        results = train_and_report(n_permutations=n_permutations)
        print(f"      ROC-AUC CV maximal observé : {results['best_cv_roc_auc']:.3f} "
              f"| signal détecté : {'oui' if results['signal_detected'] else 'non'}")

    print(f"\nPipeline terminé en {time.perf_counter() - start:.1f} s. Rapports : {config.REPORTS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline complet Bronze -> Silver -> Gold -> rapports.")
    parser.add_argument("--source", default=str(config.RAW_FILE))
    parser.add_argument("--skip-ml", action="store_true")
    parser.add_argument("--permutations", type=int, default=200)
    args = parser.parse_args()
    run_pipeline(args.source, args.skip_ml, args.permutations)


if __name__ == "__main__":
    main()
