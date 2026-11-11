"""Garde-fous de confidentialité avant publication."""
import json
import re
import subprocess

import pandas as pd
import pytest

from src import config

PUBLISHABLE_SUFFIXES = {".md", ".json", ".csv", ".ipynb", ".py", ".txt", ".yml"}


def _personal_names() -> set[str]:
    source = pd.read_csv(config.BRONZE_FILE, sep=None, engine="python", encoding="utf-8-sig")
    values = set()
    for column in config.DIRECT_IDENTIFIERS:
        values.update(str(v) for v in source[column].dropna().unique() if len(str(v)) >= 4)
    return values


def _publishable_files():
    for folder in ["docs", "reports", "notebooks", "powerbi"]:
        for path in (config.PROJECT_ROOT / folder).rglob("*"):
            if path.is_file() and path.suffix in PUBLISHABLE_SUFFIXES and ".ipynb_checkpoints" not in path.parts:
                yield path
    yield config.PROJECT_ROOT / "README.md"


def test_gitignore_protects_data_and_secrets():
    rules = (config.PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for rule in [
        "data/**", "!data/README.md", "*.csv", "*.parquet", "*.xlsx",
        ".env", ".venv/", "reports/**", "!reports/README.md", "*.pbix",
    ]:
        assert rule in rules, f"Règle absente du .gitignore : {rule}"


def test_git_ignores_every_data_file():
    """Si le projet est un dépôt Git, aucun fichier de data/ (hors README) ne doit être suivi ni suivable."""
    if not (config.PROJECT_ROOT / ".git").exists():
        pytest.skip("Pas encore de dépôt Git.")
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "data"],
        cwd=config.PROJECT_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert listed in ([], ["data/README.md"]), f"Fichiers de données exposés à Git : {listed}"


def test_no_identifier_columns_in_reports():
    for path in (config.PROJECT_ROOT / "reports").rglob("*.csv"):
        columns = set(pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns)
        assert not columns & {*config.DIRECT_IDENTIFIERS, config.TECHNICAL_KEY}, path


@pytest.mark.skipif(not config.BRONZE_FILE.exists(), reason="Source absente : contrôle impossible.")
def test_no_personal_name_in_publishable_files():
    """Aucun nom/prénom de la source ne doit apparaître dans un fichier publiable."""
    names = _personal_names()
    if not names:
        pytest.skip("Aucun nom/prénom exploitable dans la source de contrôle.")
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, sorted(names))) + r")\b", re.IGNORECASE)
    leaks = {}
    for path in _publishable_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".ipynb":
            text = json.dumps(json.loads(text), ensure_ascii=False)
        found = set(pattern.findall(text))
        if found:
            leaks[str(path.relative_to(config.PROJECT_ROOT))] = len(found)
    assert not leaks, f"Noms de famille détectés (nombre de noms distincts par fichier) : {leaks}"


def test_notebooks_do_not_publish_customer_level_records():
    """Les notebooks peuvent contenir des agrégats, jamais des lignes client."""
    forbidden_headers = {"client_id", "nom", "prenom"}
    customer_attributes = {"age", "ville", "revenu_annuel", "solde", "statut"}

    for path in (config.PROJECT_ROOT / "notebooks").rglob("*.ipynb"):
        if ".ipynb_checkpoints" in path.parts:
            continue
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook.get("cells", []):
            for output in cell.get("outputs", []):
                html = output.get("data", {}).get("text/html", "")
                if isinstance(html, list):
                    html = "".join(html)
                headers = {
                    re.sub(r"<.*?>", "", item).strip().lower()
                    for item in re.findall(r"<th[^>]*>(.*?)</th>", html, flags=re.IGNORECASE | re.DOTALL)
                }
                assert not (headers & forbidden_headers), (
                    f"Identifiant ou colonne personnelle affichée dans {path.relative_to(config.PROJECT_ROOT)}"
                )
                assert not customer_attributes.issubset(headers), (
                    f"Aperçu de lignes client détecté dans {path.relative_to(config.PROJECT_ROOT)}"
                )


def test_notebooks_are_saved_without_outputs():
    """Les sorties calculées sur la source privée ne doivent pas être commitées."""
    for path in (config.PROJECT_ROOT / "notebooks").rglob("*.ipynb"):
        if ".ipynb_checkpoints" in path.parts:
            continue
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell_number, cell in enumerate(notebook.get("cells", [])):
            if cell.get("cell_type") == "code":
                assert not cell.get("outputs"), (
                    f"Sorties à effacer avant publication : {path.relative_to(config.PROJECT_ROOT)} "
                    f"(cellule {cell_number})"
                )
                assert cell.get("execution_count") is None, (
                    f"Compteur d'exécution à effacer : {path.relative_to(config.PROJECT_ROOT)} "
                    f"(cellule {cell_number})"
                )
