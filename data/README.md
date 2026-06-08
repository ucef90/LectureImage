# Base de noms — RAG correctif

Ce dossier contient les fichiers utilisés par le module de correction
post-extraction ([name_corrector.py](../name_corrector.py)) pour rattraper
les erreurs de lecture du LLM via fuzzy matching.

## Fichiers fournis (starter pack)

- `prenoms_fr.txt` — ~500 prénoms (français, maghrébins, européens, subsahariens)
- `noms_fr.txt` — ~500 noms de famille (mêmes origines)

Une entrée par ligne. Les lignes commençant par `#` sont des commentaires.

**Convention de casse :**
- Prénoms en `Casse Capitalisée` (ex. `Youssef`)
- Noms en `MAJUSCULES` (convention état civil française, ex. `EL MOUTEE`)

Le matching `rapidfuzz` est en pratique insensible à la casse, mais respecter
la convention donne une sortie cohérente.

## Étendre avec la base INSEE officielle

### Prénoms — fichier officiel des prénoms

L'INSEE publie un fichier exhaustif des prénoms attribués en France depuis
1900 (plus de 12 000 prénoms distincts).

1. Téléchargement : https://www.insee.fr/fr/statistiques/7633685
   - Fichier : `nat2022.csv` (ou la version la plus récente)
   - Format : CSV `sexe;preusuel;annais;nombre`

2. Script d'extraction (à exécuter une fois) :

   ```python
   import pandas as pd

   df = pd.read_csv("nat2022.csv", sep=";", encoding="utf-8")
   # Filtre : prénoms attribués au moins 50 fois (sinon trop de bruit)
   counts = df.groupby("preusuel")["nombre"].sum()
   frequent = counts[counts >= 50].index.tolist()
   # Normalise la casse
   frequent = sorted({p.title() for p in frequent if p not in ("_PRENOMS_RARES", "XXXX")})

   with open("data/prenoms_fr.txt", "w", encoding="utf-8") as f:
       f.write("# Source : INSEE nat2022.csv (prénoms ≥ 50 attributions)\n")
       for p in frequent:
           f.write(p + "\n")
   ```

3. Résultat : ~3 500 prénoms (vs ~500 dans le starter pack).

### Noms de famille — fichier officiel

L'INSEE publie un fichier des patronymes du fichier électoral (très volumineux).
Pour le POC, le starter pack couvre déjà les ~500 noms les plus fréquents en
France (top INSEE) + noms d'origine maghrébine / subsaharienne / européenne.

Sources possibles pour étendre :
- **Filae** (généalogie) : top patronymes — https://www.filae.com/
- **Genealogie.com** : top 1 000 patronymes français — utile pour les noms européens
- **Données ouvertes Maroc / Algérie / Tunisie** : pour étoffer les noms maghrébins

⚠️ Aucun fichier exhaustif des patronymes n'est en libre accès direct
au format CSV (contraintes RGPD côté Filae). Pour un POC, le starter pack
suffit largement. Pour une extension production, prévoir un partenariat
avec un fournisseur de données ou une collecte interne MDPH.

## Personnalisation locale CD93

Tu peux ajouter à `noms_fr.txt` et `prenoms_fr.txt` les noms/prénoms
spécifiquement présents dans la population de Seine-Saint-Denis (forte
présence maghrébine et subsaharienne), en complément du starter pack.

Tout ajout est pris en compte au prochain lancement de l'application
(les fichiers sont lus à l'initialisation par [name_corrector.py](../name_corrector.py)).

## Format des fichiers

```
# Commentaires précédés de #
# Une entrée par ligne
# Lignes vides ignorées

MARTIN
BERNARD
EL MOUTEE
```

Pas de virgule, pas de CSV, pas de JSON — texte brut UTF-8.
