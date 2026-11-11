# Méthodologie

## 1. Cadre

- **Unité d'observation :** un client après dédoublonnage (les effectifs exacts sont conservés dans les rapports locaux).
- **Cible :** le statut **observé** à la date d'extraction (`Actif` / `Inactif`), sans historique.
- **Portée :** description d'associations. Aucune prévision d'inactivité future, aucune causalité.

## 2. Analyse descriptive

Statistiques par statut (moyenne, médiane, écart-type), boîtes à moustaches, histogrammes,
tableaux croisés et corrélations de Pearson. Les statistiques d'âge portent uniquement sur les
observations renseignées ; les valeurs manquantes restent visibles dans les agrégats dédiés.

## 3. Tests d'association (`src/analysis/association_tests.py`)

| Variables | Test | Taille d'effet |
|---|---|---|
| Ville, type de compte, tranche d'âge, quartiles de revenu et de solde | Khi-deux d'indépendance | V de Cramér (0 = aucune association) |
| Âge, revenu, solde, population | Mann-Whitney (non paramétrique) | AUC = P(inactif > actif) ; 0,5 = aucune différence |

Neuf tests étant réalisés, les p-valeurs sont corrigées par la méthode de Holm, qui contrôle le
risque d'obtenir au moins un faux positif.

**Pourquoi tester avant d'interpréter ?** Des écarts descriptifs entre segments peuvent apparaître
par fluctuation d'échantillonnage, notamment lorsque les effectifs par segment sont modestes.
Le test global et la taille d'effet évitent de transformer ces écarts en recommandations non
étayées.

## 4. Modélisation (`src/ml/train_models.py`)

1. **Séparation** stratifiée entraînement / test (80 / 20, `random_state = 42`).
2. **Prétraitement dans le pipeline** : imputation médiane de l'âge, standardisation des
   variables numériques, encodage one-hot de la ville et du type de compte. Tout est appris sur
   le seul jeu d'entraînement.
3. **Modèles** : baseline (classe majoritaire), régression logistique, arbre de décision,
   forêt aléatoire, gradient boosting — paramètres par défaut, aucun réglage.
4. **Sélection** par validation croisée stratifiée à 5 plis sur l'entraînement, critère ROC-AUC.
   Le jeu de test n'intervient pas dans le choix.
5. **Évaluation finale** sur le test : accuracy, précision, rappel et F1 pour la classe
   `Inactif`, ROC-AUC, matrice de confusion.
6. **Test de permutation** (200 permutations de la cible) : le score réel est-il meilleur que
   ceux obtenus quand la cible est mélangée au hasard ?

Un signal est considéré comme méritant un examen complémentaire si le ROC-AUC maximal observé
en validation croisée atteint le seuil de repérage configuré **et** si le test de permutation
est significatif au seuil de 5 %. Ce critère est une règle exploratoire propre au projet, pas
une norme universelle.

**Pourquoi aucun réglage d'hyperparamètres ?** Régler des paramètres sur des données sans signal
ne fait qu'ajuster le bruit des plis de validation. Il sera pertinent si de nouvelles variables
apportent un signal.

**Pourquoi l'importance des variables n'est pas présentée ?** Un modèle à base d'arbres attribue
toujours des importances, même à du bruit, et favorise mécaniquement les variables continues
(plus de points de coupure). Sans pouvoir discriminant, ces importances ne décrivent rien.

## 5. Résultats

Les résultats chiffrés (effectifs, statistiques descriptives, p-valeurs, tailles d'effet,
validation croisée et matrices de confusion) sont produits dans `reports/` lors de l'exécution
locale du pipeline. Ils ne sont pas intégrés à la documentation publique, car ils sont dérivés
d'une source bancaire dont la divulgation doit être autorisée.

À la date de l'analyse, les tests d'association et les modèles évalués n'ont pas mis en évidence
de signal robuste permettant de distinguer le statut observé avec les variables disponibles.
Pour les valeurs exactes et les diagnostics détaillés, consulter les rapports locaux après une
exécution autorisée du pipeline.

## 6. Interprétation et suites

Les analyses ne mettent pas en évidence de signal exploitable avec les variables disponibles.
Cela ne démontre pas une indépendance parfaite et ne permet pas, à lui seul, de conclure que les
données sont synthétiques. Plusieurs explications restent possibles :

1. le statut peut dépendre d'informations absentes — fréquence des opérations, date de dernière
   connexion, ancienneté, produits détenus, contacts avec le conseiller ;
2. la règle métier qui définit `Actif` / `Inactif` peut ne pas correspondre aux variables présentes ;
3. les données peuvent être synthétiques, ou les variables peuvent avoir été générées sans relation ;
4. les effets éventuels peuvent être faibles, non linéaires ou conditionnels et ne pas être détectés
   par le protocole retenu.

Le seuil ROC-AUC de 0,55 utilisé par le script est un **seuil de repérage choisi pour ce projet**,
pas une norme universelle ni un seuil réglementaire. La décision doit être prise à partir de
l'ensemble du protocole, et non de ce seul seuil.

Pour une véritable étude de l'inactivité future, il faut des données **datées** : historique des
opérations, date d'ouverture du compte, date de dernière activité, date de référence et règle exacte
qui définit le statut. Les variables explicatives doivent être calculées avant la période cible afin
d'éviter toute fuite temporelle.
