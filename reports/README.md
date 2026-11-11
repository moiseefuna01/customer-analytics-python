# Rapports générés localement

Les sous-dossiers `audit/`, `silver/`, `analysis/` et `ml/` sont alimentés par les scripts du
pipeline (`python -m src.pipeline`). Ils peuvent contenir des statistiques issues de la source
bancaire autorisée ; ils sont donc exclus du dépôt Git par défaut.

Avant toute publication d'un rapport agrégé, vérifier que sa divulgation est autorisée par le
propriétaire des données. L'absence de lignes individuelles ne signifie pas automatiquement que
les résultats agrégés sont publics.
