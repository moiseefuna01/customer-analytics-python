# Dossier `data/`

Ce dossier n'est **jamais publié** : le `.gitignore` exclut tout son contenu, sauf ce fichier.

## Organisation

| Dossier | Contenu | Produit par |
|---|---|---|
| `raw/` | Source autorisée `clients.csv` (immuable, contient noms et prénoms) | vous |
| `bronze/` | Copie fidèle de la source + `clients_ingestion_metadata.json` | `src/bronze/ingest_bronze.py` |
| `silver/` | `clients_clean.parquet` — nettoyé, validé, sans nom ni prénom | `src/silver/build_silver.py` |
| `gold/analytics/` | 8 tables de reporting (Parquet + CSV) pour Power BI | `src/gold/build_gold_analytics.py` |
| `gold/ml/` | `gold_ml_dataset.parquet` + `gold_ml_dataset.csv` — table de modélisation | `src/gold/build_gold_ml.py` |

## Démarrer

1. Copiez le fichier source autorisé dans `data/raw/clients.csv`
   (le contenu doit être du CSV, même si l'extension d'origine était `.xls`).
2. Lancez `python -m src.pipeline` depuis la racine du projet.

Sans accès à la source, générez des données synthétiques au même schéma :
`python -m src.utils.sample_data`. Les résultats obtenus ne correspondent alors pas à ceux du README.
