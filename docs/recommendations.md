# Recommandations métier

## 1. Décision à prendre avec les résultats actuels

Les analyses d'association et les essais de classification ne mettent pas en évidence de signal
suffisant pour distinguer les statuts observés avec l'âge, la ville, la population de la ville, le
revenu annuel, le type de compte et le solde.

**Recommandation : ne pas déployer de score de ciblage et ne pas déclencher de campagne sur la base
des classements observés par ville, âge, revenu, solde ou type de compte.** Les écarts descriptifs
ne constituent pas une preuve de différence métier ni un lien causal.

L'absence de significativité ne prouve pas une indépendance parfaite. Elle signifie que le protocole
et les variables disponibles n'ont pas apporté de preuve suffisante dans cet échantillon.

## 2. Vérifications à mener avec les équipes métier et data

1. **Définir le statut.** Documenter précisément la règle qui attribue `Actif` ou `Inactif`, la date
de référence, la durée d'inactivité retenue et les éventuelles exceptions.
2. **Vérifier la provenance.** Confirmer si la source est réelle, synthétique ou partiellement
   simulée ; documenter la méthode d'anonymisation et les autorisations d'utilisation.
3. **Documenter les champs financiers.** Confirmer l'unité, la devise, la période de référence du
   revenu, la date du solde et la source des populations de villes.
4. **Contrôler les données sources.** Valider la suppression des doublons exacts avec le métier et
   vérifier que les règles de qualité reflètent les conventions de la banque.

## 3. Données complémentaires à prioriser

Pour comprendre l'inactivité, les variables statiques du fichier peuvent être insuffisantes. Avec
l'accord de la banque et dans un cadre de minimisation des données, prioriser :

- date de dernière opération et nombre d'opérations sur plusieurs fenêtres (30, 90, 180 jours) ;
- ancienneté du compte et date d'ouverture ;
- évolution du solde et flux entrants/sortants ;
- produits détenus et usage des canaux digitaux ;
- interactions avec le service client, réclamations et incidents, si leur usage est autorisé.

Les caractéristiques doivent être calculées avant la période durant laquelle l'inactivité est
observée. Les événements postérieurs à la cible ne doivent jamais servir de variables explicatives.

## 4. Prochaine étude recommandée

Construire un jeu longitudinal avec une date d'observation et un horizon cible explicites. Par
exemple : calculer les caractéristiques sur une fenêtre historique, puis définir l'inactivité sur
une période ultérieure selon la règle métier validée. Comparer les modèles à une baseline, utiliser
une séparation temporelle, mesurer la calibration et choisir un seuil en fonction du coût des faux
positifs et faux négatifs.

Ce nouveau protocole permettrait d'étudier une **inactivité future**. Le présent projet ne réalise
pas cette prévision : il analyse uniquement un statut observé à un instant donné.

## 5. Usage du dashboard Power BI

Le rapport Power BI doit rester descriptif : effectifs, proportions, distributions et filtres du
portefeuille. Les pages ne doivent pas présenter un classement de villes ou de segments comme une
liste de clients à cibler. La page dédiée à l'activité doit rappeler la définition et la date du
statut.
