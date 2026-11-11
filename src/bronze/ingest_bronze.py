"""Couche Bronze : copie fidèle de la source + métadonnées de traçabilité.

    python -m src.bronze.ingest_bronze --source data/raw/clients.csv

Le fichier Bronze est une copie octet pour octet de la source : aucune valeur
n'est modifiée. Les métadonnées (empreinte SHA-256, taille, nombre de lignes,
horodatage) permettent de prouver quelle source a alimenté le pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.utils.io import read_source_csv, write_json


def sha256_of(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_bronze(source_path: Path | str = config.RAW_FILE,
                  bronze_path: Path | str = config.BRONZE_FILE,
                  metadata_path: Path | str | None = None) -> dict:
    """Copie la source en Bronze, contrôle le schéma et écrit les métadonnées."""
    source_path, bronze_path = Path(source_path), Path(bronze_path)
    if metadata_path is None:
        metadata_path = bronze_path.parent / config.BRONZE_METADATA_FILE.name
    if not source_path.exists():
        raise FileNotFoundError(
            f"Source introuvable : {source_path}. Placez le fichier autorisé dans data/raw/ "
            "ou générez une source synthétique : python -m src.utils.sample_data"
        )

    bronze_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() != bronze_path.resolve():
        shutil.copyfile(source_path, bronze_path)

    df = read_source_csv(bronze_path)
    missing = sorted(set(config.EXPECTED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Colonnes attendues absentes de la source : {missing}")

    metadata = {
        "ingestion_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file_name": source_path.name,
        "bronze_file_name": bronze_path.name,
        "sha256": sha256_of(bronze_path),
        "size_bytes": bronze_path.stat().st_size,
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "columns": list(map(str, df.columns)),
    }
    write_json(metadata, metadata_path)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion Bronze (copie fidèle + métadonnées).")
    parser.add_argument("--source", default=str(config.RAW_FILE))
    parser.add_argument("--output", default=str(config.BRONZE_FILE))
    args = parser.parse_args()
    metadata = ingest_bronze(args.source, args.output)
    print("=== BRONZE ===")
    print(f"Lignes : {metadata['row_count']} | Colonnes : {metadata['column_count']}")
    print(f"SHA-256 : {metadata['sha256']}")


if __name__ == "__main__":
    main()
