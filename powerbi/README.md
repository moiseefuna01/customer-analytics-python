# Rapport Power BI

**État : à construire.** Le rapport cible comporte quatre pages reliées par une navigation dédiée.

## Sources locales

Les fichiers sont générés par `python -m src.pipeline` dans `data/gold/analytics/`.
Les CSV sont encodés en UTF-8 avec BOM, séparateur virgule et point décimal. Dans Power Query,
vérifiez le type de données et le paramètre régional (Anglais — États-Unis pour les décimaux si
Power BI interprète mal les nombres).

| Table | Grain | Usage principal |
|---|---|---|
| `gold_kpi_global` | 1 ligne | KPI globaux et contrôles |
| `gold_status_distribution` | 1 ligne par statut | Répartition Actif / Inactif |
| `gold_account_analysis` | 1 ligne par type de compte | Analyse des comptes |
| `gold_age_analysis` | 1 ligne par tranche d'âge | Analyse démographique |
| `gold_income_analysis` | 1 ligne par quartile de revenu | Analyse des revenus |
| `gold_balance_analysis` | 1 ligne par quartile de solde | Analyse des soldes |
| `gold_city_analysis` | 1 ligne par ville | Répartition géographique |
| `gold_fact_clients` | 1 ligne par client, sans identifiant | Table de faits locale pour les filtres et mesures dynamiques |

**Confidentialité :** `gold_fact_clients` ne contient ni nom, ni prénom, ni `client_id`, mais reste
au niveau individuel et comporte des attributs financiers et démographiques. Il doit rester local.
Ne publiez pas un fichier PBIX contenant cette table issue de la source bancaire réelle. Pour un
portfolio public, utilisez une source synthétique ou des données dont la publication est autorisée.

## Modèle de données et interactions

Pour les visuels qui doivent se filtrer entre eux, utiliser `gold_fact_clients` comme table de faits
principale et construire les mesures à partir de ses lignes. Les champs de filtre peuvent être pris
directement dans cette table ou dans des dimensions distinctes créées dans Power Query. Évitez de
relier toutes les tables agrégées entre elles en bidirectionnel : cela peut créer des chemins de
filtrage ambigus et des totaux incohérents.

Exemples de mesures DAX à créer après import de `gold_fact_clients` :

```DAX
Clients total = COUNTROWS(gold_fact_clients)

Clients actifs =
CALCULATE([Clients total], gold_fact_clients[statut] = "Actif")

Clients inactifs =
CALCULATE([Clients total], gold_fact_clients[statut] = "Inactif")

Taux d'activité (%) = DIVIDE([Clients actifs], [Clients total])

Taux d'inactivité (%) = DIVIDE([Clients inactifs], [Clients total])

Solde moyen = AVERAGE(gold_fact_clients[solde])

Revenu annuel moyen = AVERAGE(gold_fact_clients[revenu_annuel])
```

Formater les deux taux en pourcentage dans le modèle. `COUNTROWS` est approprié ici car Silver
valide une ligne par `client_id` avant de retirer cette clé de la table Gold de faits.

Les sept tables agrégées restent utiles pour contrôler et comparer les résultats globaux. Pour des
visuels dynamiques qui doivent réagir aux segments et aux filtres des autres pages, privilégier les
mesures calculées à partir de la table de faits.

## Pages prévues

1. **Vue d'ensemble** — cartes KPI, répartition du statut et synthèse du portefeuille.
2. **Profil démographique** — tranches d'âge, villes et populations ; filtres synchronisés.
3. **Comptes et finances** — types de comptes, quartiles de revenu et de solde.
4. **Activité du portefeuille** — statuts et indicateurs descriptifs, sans classement présenté comme
   un facteur causal ou un levier de ciblage.

## Navigation et expérience utilisateur

- Ajouter une barre de navigation avec quatre boutons (un par page), via les actions *Page
  précédente/suivante* ou les signets (*Bookmarks*) selon le design retenu.
- Synchroniser les segments pertinents entre les pages avec *Sync slicers*.
- Ajouter un bouton **Réinitialiser les filtres** à l'aide d'un signet dédié.
- Vérifier les interactions visuelles (*Modifier les interactions*) pour éviter les filtres
  inattendus.
- Afficher la date de référence et la définition métier du statut dans le rapport.

## Règle d'interprétation

Les tests réalisés dans le projet ne mettent pas en évidence d'association statistiquement
significative avec le statut à partir des variables disponibles. Le rapport doit donc décrire le
portefeuille, et non présenter les différences descriptives entre villes ou segments comme des
causes de l'inactivité.
