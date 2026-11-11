# Audit du dépôt et corrections apportées

> Journal historique des corrections. Les chiffres détaillés issus de la source bancaire ont été retirés de cette documentation publique ; ils restent dans les rapports locaux générés après exécution.

Audit réalisé sur les versions successives du projet. Chaque constat est suivi de sa correction.

## 1. Constats bloquants

### 1.1 Deux couches Silver contradictoires
`src/cleaning/build_silver.py` produisait un Parquet qui **conservait** les âges manquants ;
le notebook produisait un CSV qui les **imputait globalement**. Les tables Gold et le dataset ML
provenaient du CSV imputé, à l'inverse de ce qu'annonçait `docs/silver_data_quality.md`.

**Conséquences :** imputation avant la séparation entraînement / test (fuite de données),
une tranche d'âge artificiellement gonflée et une dispersion de l'âge sous-estimée.

**Correction :** une seule couche Silver (`data/silver/clients_clean.parquet`) produite par
`src/silver/build_silver.py` ; âges conservés ; imputation déplacée dans le pipeline
scikit-learn ; tranche « Non renseigné » dans Gold.

### 1.2 Conclusions tirées du bruit
Le notebook présentait un modèle comme « meilleur », classait les villes et commentait
l'importance des variables à partir de résultats descriptifs et prédictifs fragiles. La revue
statistique n'a pas mis en évidence de signal robuste en validation croisée ou dans les tests
d'association. Les classements descriptifs étaient donc insuffisants pour justifier des
recommandations de ciblage.

**Correction :** ajout de tests d'association avec correction de Holm, d'une validation
croisée, d'un test de permutation et d'intervalles de confiance par ville ; conclusions
réécrites ; importances des variables retirées.

### 1.3 Données personnelles dans les sorties du notebook
Les sorties de `df.head()`, `df.iloc[...]` et de plusieurs filtres affichaient des enregistrements
au niveau individuel, alors que le notebook n'était pas exclu par le `.gitignore`. Des
identifiants directs circulaient aussi dans l'ancienne Silver.

**Correction :** `nom` et `prenom` retirés dès Silver ; nouveau notebook qui ne les affiche
jamais ; ancien notebook de travail retiré de la version publique ; test automatique qui recherche
les noms de la source dans les fichiers publiables.

## 2. Erreurs

| Constat | Correction |
|---|---|
| Section D.5.1 : valeurs de population de deux villes inversées | Correction et cohérence des valeurs de référence vérifiées |
| Chemin relatif `data/gold/analytics` depuis `notebooks/` : tables écrites dans `notebooks/data/` | Chemins centralisés dans `src/config.py`, calculés depuis la racine |
| Tables Gold en double (`account_analysis` et `gold_account_analysis`) et incohérentes | Une seule convention : `gold_<thème>` |
| README : commande `--input "data/clients.csv"` vers un fichier inexistant ; statut « audit in progress » | README réécrit |
| `docs/initial_audit_results.md` : source annoncée « absente de l'archive » alors qu'elle y était | Remplacé par les rapports générés dans `reports/` |
| Gold Analytics et Gold ML produits uniquement dans le notebook | Scripts `src/gold/` |
| Couche Bronze sans script ni métadonnées malgré la promesse de traçabilité | `src/bronze/ingest_bronze.py` (copie + SHA-256) |
| `profile_data.py` : section 9 hors de la fonction après un `return` possible | Fusionné dans `src/audit/audit_source.py` |
| `scipy` utilisé implicitement, `ipykernel` absent de `requirements.txt` | Ajoutés |
| Tests codés en dur sur les chiffres de la source, impossibles à exécuter sans elle | Tests sur source synthétique + contrôles de cohérence des fichiers réels |
| Règles `.gitignore` insuffisantes pour les résultats dérivés | Règles revues : données, rapports calculés et PBIX exclus par défaut |
| Archive de 196 Mo, dont 192 Mo d'environnement virtuel Windows (`.venv`) | `.venv` exclu ; environnement recréé depuis `requirements.txt` |

## 3. Éléments ajoutés

- `src/pipeline.py` : tout le workflow en une commande.
- `src/utils/sample_data.py` : source synthétique pour exécuter le projet sans données privées.
- Suite de tests automatisés couvrant Bronze, Silver, Gold, analyse, ML et confidentialité (le nombre exact évolue avec les ajouts).
- Intégration continue GitHub Actions (Python 3.12 et 3.13).
- Rapports générés automatiquement dans `reports/`.
- Documentation : dictionnaire de données, règles de qualité, méthodologie, publication GitHub.
- Table `gold_fact_clients` (dé-identifiée) pour les filtres et interactions du rapport Power BI.

## 4. Points restant à valider avec la banque

- La règle métier qui attribue le statut Actif / Inactif.
- La date d'extraction, l'unité et la période de référence du revenu et du solde.
- La validation de la suppression des doublons exacts.
- L'origine réelle ou synthétique des données.


## 5. Revue finale de publication

Une vérification complémentaire de l'archive destinée à GitHub a identifié les points suivants :

- Un aperçu de dix lignes Bronze était enregistré dans le notebook avec `client_id`, âge, ville,
  revenu, solde et statut. Cet aperçu a été remplacé par des métadonnées non individuelles.
- Les sorties et compteurs d'exécution des notebooks sont effacés avant publication ; un test
  automatique bloque le commit si des sorties réapparaissent.
- Les tests de confidentialité contrôlent également les colonnes d'identification dans les
  tableaux affichés et les noms/prénoms lorsqu'une source est disponible localement.
- Gold ML est exporté en Parquet et CSV pour inspection et traitement ; ces fichiers restent
  locaux et sont exclus du dépôt.
- Les rapports générés et les fichiers PBIX sont ignorés par Git par défaut. Les rapports agrégés
  ne doivent être publiés qu'après autorisation explicite du propriétaire des données.
- Les formulations statistiques ont été nuancées : ne pas détecter d'association n'est pas une
  preuve d'indépendance parfaite ; l'étude ne démontre ni causalité ni prédiction future.
