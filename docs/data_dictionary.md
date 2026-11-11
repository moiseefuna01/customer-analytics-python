# Dictionnaire de données

Les interprétations marquées « à confirmer » doivent être validées avec la documentation métier
de la banque avant toute utilisation opérationnelle.

## Source (`data/raw/clients.csv`) — 10 colonnes

| Colonne | Type | Description | Présence par couche | Remarque |
|---|---|---|---|---|
| `client_id` | entier | Identifiant technique du client | Bronze, Silver | Unique après retrait des doublons exacts ; retiré à partir de Gold |
| `nom` | texte | Nom de famille | Bronze uniquement | **Identifiant direct** : retiré dès la couche Silver |
| `prenom` | texte | Prénom | Bronze uniquement | **Identifiant direct** : retiré dès la couche Silver |
| `age` | entier (nullable) | Âge en années | toutes | 200 valeurs manquantes (2 %), conservées sans imputation |
| `ville` | texte | Ville de résidence | toutes | 30 villes |
| `population_ville` | entier | Population de la ville | toutes | Une valeur par ville ; date et source à confirmer |
| `revenu_annuel` | entier | Revenu annuel du client, en euros | toutes | Période de référence à confirmer |
| `type_compte` | texte | `Epargne`, `Premium` ou `Courant` | toutes | Définitions des catégories à confirmer |
| `solde` | décimal | Solde du compte à la date d'extraction, en euros | toutes | Date d'extraction inconnue |
| `statut` | texte | `Actif` ou `Inactif` à la date d'extraction | toutes | **Règle métier d'attribution inconnue** : c'est l'information la plus importante à obtenir |

## Colonnes ajoutées dans Gold Analytics (`gold_fact_clients`)

| Colonne | Définition |
|---|---|
| `tranche_age` | 18-25, 26-35, 36-45, 46-55, 56-65, 66 ans et plus ; `Non renseigné` si l'âge manque |
| `groupe_revenu` | Quartile de `revenu_annuel` (Q1 = 25 % des revenus les plus faibles) |
| `groupe_solde` | Quartile de `solde` |
| `est_inactif` | 1 si `statut = Inactif`, sinon 0 (pratique pour calculer un taux par moyenne) |

## Indicateurs des tables de segments

Les tables `gold_account_analysis`, `gold_age_analysis`, `gold_income_analysis`,
`gold_balance_analysis` et `gold_city_analysis` ont les mêmes colonnes d'indicateurs :

| Colonne | Définition |
|---|---|
| `ordre` | Ordre d'affichage du segment (tables ordonnées uniquement) |
| `total_clients` | Nombre de clients du segment |
| `clients_actifs`, `clients_inactifs` | Effectifs par statut |
| `taux_activite_pct`, `taux_inactivite_pct` | Part du segment, en % (somme = 100) |
| `proportion_portefeuille_pct` | Part du segment dans le portefeuille, en % |
| `age_moyen` | Moyenne des âges **renseignés** du segment |
| `revenu_annuel_moyen`, `solde_moyen` | Moyennes du segment |

`gold_kpi_global` contient en plus `ages_non_renseignes`, `solde_median`, `solde_total` et `nombre_villes`.
