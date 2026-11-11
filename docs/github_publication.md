# Publier le projet sur GitHub

## 1. Vérifications avant le premier commit

Depuis la racine du projet, environnement virtuel activé :

```bash
python -m src.pipeline    # régénère les données et rapports locaux
pytest                    # exécute la suite de tests, y compris les contrôles de confidentialité
```

`tests/test_privacy.py` vérifie que :
- le `.gitignore` exclut `data/`, les rapports locaux, les fichiers PBIX et les secrets ;
- Git ne suit aucun fichier de `data/` (à part `data/README.md`) ;
- aucun nom/prénom de la source n'apparaît dans les fichiers publiables, lorsque la source est
  disponible localement ;
- les notebooks ne contiennent pas de sorties ou de compteurs d'exécution enregistrés ;
- aucun tableau de notebook n'affiche d'identifiant ou de ligne au niveau client.

## 2. Créer le dépôt local

```bash
git init
git branch -M main
git add .
git status
```

Dans la liste affichée par `git status`, seuls les fichiers de documentation prévus doivent
apparaître : **aucun fichier de données dans `data/`** (sauf `data/README.md`), aucun résultat
calculé dans `reports/` (sauf `reports/README.md`), aucun `.venv/` et aucun `.pbix`. Si c'est le
cas, arrêtez-vous et vérifiez le `.gitignore` avant le commit.

```bash
git commit -m "Pipeline médaillon, tests statistiques, modèles et documentation"
```

## 3. Créer le dépôt distant

1. Sur github.com : **New repository** → nom `customer-analytics-python` → **ne cochez pas**
   « Add a README » (le projet en a déjà un).
2. Puis :

```bash
git remote add origin https://github.com/VOTRE-COMPTE/customer-analytics-python.git
git push -u origin main
```

3. Remplacez `VOTRE-COMPTE` dans les exemples d'URL du `README.md` et de cette documentation,
   puis commitez. Le badge Actions peut être ajouté après la création du dépôt.
4. Onglet **Actions** : le workflow `tests` doit être vert. Il s'exécute sur une source
   synthétique, puisque les données réelles ne sont pas sur GitHub.

## 4. Ce qui est publié

| Publié | Non publié |
|---|---|
| Code `src/`, tests, notebooks, documentation | Tout `data/` : source, Bronze, Silver, Gold |
| Captures Power BI réalisées sur données synthétiques, si souhaité | `.venv/`, caches, secrets |
| Rapports agrégés uniquement après autorisation explicite | Fichier PBIX contenant des données bancaires non autorisées |

Le notebook `notebooks/01_analyse_clients.ipynb` est publié **sans sorties enregistrées**. Il est
exécuté localement après le pipeline, mais les sorties doivent être effacées avant un commit afin
de ne pas embarquer des résultats provenant de la source privée. Relancez `pytest` avant de commiter.

Ne publiez pas non plus les rapports agrégés ni les captures du dashboard tant que leur divulgation
n'a pas été autorisée par le propriétaire des données. Les agrégats peuvent rester confidentiels,
même lorsqu'aucune ligne client n'est affichée.

## 5. Si un fichier sensible a été commité par erreur

Le retirer du dernier commit ne suffit pas : il reste dans l'historique. Si le dépôt n'a pas
encore été poussé, recréez-le (`rm -rf .git` puis reprenez l'étape 2). S'il a été poussé,
rendez le dépôt privé immédiatement, puis nettoyez l'historique avec `git filter-repo` ou
supprimez et recréez le dépôt.

## 6. Licence

Ajoutez un fichier `LICENSE` si vous souhaitez autoriser la réutilisation du code (par exemple
MIT, via **Add file → Create new file → LICENSE** sur GitHub). La licence couvre le code, pas les
données, qui ne sont pas publiées.
