import json

import pytest

from src import config
from src.bronze.ingest_bronze import ingest_bronze, sha256_of


def test_bronze_is_byte_identical_to_source(workspace):
    assert workspace["bronze_path"].read_bytes() == workspace["raw_path"].read_bytes()


def test_bronze_metadata_describes_the_file(workspace, raw_df):
    metadata_file = workspace["bronze_path"].parent / config.BRONZE_METADATA_FILE.name
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert metadata["row_count"] == len(raw_df)
    assert metadata["columns"] == config.EXPECTED_COLUMNS
    assert metadata["sha256"] == sha256_of(workspace["bronze_path"])


def test_bronze_rejects_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_bronze(tmp_path / "absent.csv", tmp_path / "bronze.csv")


def test_bronze_rejects_incomplete_schema(tmp_path, raw_df):
    source = tmp_path / "incomplet.csv"
    raw_df.drop(columns=["statut"]).to_csv(source, index=False)
    with pytest.raises(ValueError, match="statut"):
        ingest_bronze(source, tmp_path / "bronze.csv")
