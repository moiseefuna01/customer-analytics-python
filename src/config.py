"""Configuration centrale du projet : chemins, schéma et paramètres partagés.

Tous les scripts importent leurs chemins d'ici. Aucun chemin n'est écrit en dur
ailleurs, ce qui évite les écarts entre notebook, scripts et tests.
"""
from __future__ import annotations

from pathlib import Path

# --- Chemins -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_FILE = DATA_DIR / "raw" / "clients.csv"                 # source immuable (privée)
BRONZE_DIR = DATA_DIR / "bronze"
BRONZE_FILE = BRONZE_DIR / "clients.csv"                    # copie fidèle de la source
BRONZE_METADATA_FILE = BRONZE_DIR / "clients_ingestion_metadata.json"
SILVER_FILE = DATA_DIR / "silver" / "clients_clean.parquet"
GOLD_ANALYTICS_DIR = DATA_DIR / "gold" / "analytics"
GOLD_ML_DIR = DATA_DIR / "gold" / "ml"
GOLD_ML_FILE = GOLD_ML_DIR / "gold_ml_dataset.parquet"
GOLD_ML_CSV_FILE = GOLD_ML_DIR / "gold_ml_dataset.csv"

REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIT_REPORT_DIR = REPORTS_DIR / "audit"
SILVER_REPORT_DIR = REPORTS_DIR / "silver"
ANALYSIS_REPORT_DIR = REPORTS_DIR / "analysis"
ML_REPORT_DIR = REPORTS_DIR / "ml"

# --- Schéma de la source -----------------------------------------------------
EXPECTED_COLUMNS = [
    "client_id", "nom", "prenom", "age", "ville",
    "population_ville", "revenu_annuel", "type_compte", "solde", "statut",
]
DIRECT_IDENTIFIERS = ["nom", "prenom"]          # jamais au-delà de la couche Bronze
TECHNICAL_KEY = "client_id"                     # jamais au-delà de la couche Silver
TEXT_COLUMNS = ["nom", "prenom", "ville", "type_compte", "statut"]
NUMERIC_COLUMNS = ["age", "population_ville", "revenu_annuel", "solde"]
ALLOWED_VALUES = {
    "statut": {"Actif", "Inactif"},
    "type_compte": {"Epargne", "Premium", "Courant"},
}
AGE_MIN, AGE_MAX = 18, 120

# --- Colonnes de la couche Silver (pseudonymisée) ----------------------------
SILVER_COLUMNS = [c for c in EXPECTED_COLUMNS if c not in DIRECT_IDENTIFIERS]

# --- Segmentation Gold -------------------------------------------------------
AGE_BINS = [18, 25, 35, 45, 55, 65, 120]
AGE_LABELS = ["18-25 ans", "26-35 ans", "36-45 ans", "46-55 ans", "56-65 ans", "66 ans et plus"]
AGE_MISSING_LABEL = "Non renseigné"
INCOME_LABELS = [
    "Q1 - Revenus faibles", "Q2 - Revenus intermédiaires bas",
    "Q3 - Revenus intermédiaires hauts", "Q4 - Revenus élevés",
]
BALANCE_LABELS = [
    "Q1 - Soldes faibles", "Q2 - Soldes intermédiaires bas",
    "Q3 - Soldes intermédiaires hauts", "Q4 - Soldes élevés",
]

# --- Machine Learning --------------------------------------------------------
TARGET = "statut"
POSITIVE_CLASS = "Inactif"
NUMERIC_FEATURES = ["age", "population_ville", "revenu_annuel", "solde"]
CATEGORICAL_FEATURES = ["ville", "type_compte"]
ML_FEATURES = ["age", "ville", "population_ville", "revenu_annuel", "type_compte", "solde"]
TEST_SIZE = 0.20
CV_FOLDS = 5
RANDOM_STATE = 42
