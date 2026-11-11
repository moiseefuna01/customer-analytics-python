# Règles de qualité de la couche Silver

Implémentation : `src/silver/build_silver.py`. Tests : `tests/test_silver.py`.

Toutes les règles sont **bloquantes** : si l'une échoue, le script s'arrête et aucun fichier Silver
n'est écrit. Un fichier Silver présent sur le disque est donc un fichier validé.

| # | Règle | Justification | Contrôle |
|---|---|---|---|
| 1 | Les 10 colonnes attendues sont présentes | Le reste du pipeline en dépend | OK |
| 2 | Espaces superflus retirés des textes | Évite `"Actif "` ≠ `"Actif"` | OK |
| 3 | Doublons exacts supprimés (ligne entière identique) | Une même ligne saisie deux fois ne représente qu'un client | Vérifié |
| 4 | `client_id` unique après l'étape 3 | Une ligne par client ; deux lignes différentes pour un même identifiant exigent un arbitrage métier | Vérifié |
| 5 | Types explicites ; âge entier *nullable* | Types stables entre Parquet, CSV et Power BI | OK |
| 6 | `statut` ∈ {Actif, Inactif} ; `type_compte` ∈ {Epargne, Premium, Courant} | Domaine fermé, sans valeur manquante | OK |
| 7 | Âge entre 18 et 120 ans ; revenu ≥ 0 ; solde ≥ 0 ; population > 0 | Bornes de vraisemblance | OK |
| 8 | Une seule population par ville | Cohérence de la donnée de référence | OK |
| 9 | `nom` et `prenom` retirés | Minimisation des données personnelles | 2 colonnes retirées |

## Décisions de traitement

**Âges manquants : conservés.** Aucune imputation n'est faite dans Silver. L'imputation est
apprise dans le pipeline scikit-learn sur le seul jeu d'entraînement, afin d'éviter une fuite de
données. Dans les tables Gold, les âges absents sont regroupés dans la tranche « Non renseigné ».

**Valeurs atypiques : conservées.** Le repérage par IQR sert à signaler des valeurs à examiner ;
il ne prouve pas qu'elles sont erronées. Les valeurs de population des grandes villes sont
plausibles dans leur contexte et ne sont pas supprimées automatiquement.

**Doublons exacts : supprimés.** Cette règle technique doit être confirmée par le métier.
