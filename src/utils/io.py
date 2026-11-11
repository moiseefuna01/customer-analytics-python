"""Fonctions d'entrée/sortie partagées."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def read_source_csv(path: Path | str) -> pd.DataFrame:
    """Lit un CSV source en détectant le séparateur et en gérant un éventuel BOM."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {path}. Consultez data/README.md pour placer la source."
        )
    return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")


def write_table(df: pd.DataFrame, directory: Path | str, name: str) -> dict[str, Path]:
    """Écrit une table en Parquet (référence) et en CSV UTF-8 avec BOM (Excel / Power BI)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    parquet_path = directory / f"{name}.parquet"
    csv_path = directory / f"{name}.csv"
    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return {"parquet": parquet_path, "csv": csv_path}


def write_json(payload: dict, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def markdown_table(df: pd.DataFrame, float_format: str = "{:.3f}") -> str:
    """Convertit un DataFrame en tableau Markdown sans dépendance externe."""

    def fmt(value) -> str:
        if isinstance(value, float):
            return float_format.format(value)
        return str(value)

    header = "| " + " | ".join(map(str, df.columns)) + " |"
    separator = "|" + "|".join(["---"] * len(df.columns)) + "|"
    rows = [
        "| " + " | ".join(fmt(v) for v in row) + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join([header, separator, *rows])
