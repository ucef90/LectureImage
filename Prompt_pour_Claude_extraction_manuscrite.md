# PROMPT À DONNER À CLAUDE — Projet d'extraction d'entités sur écriture manuscrite

> Copier-coller intégralement le bloc ci-dessous dans une nouvelle conversation Claude
> (claude.ai, Claude Code, ou via API). Claude développera l'application.

---

```
═══════════════════════════════════════════════════════════════
RÔLE
═══════════════════════════════════════════════════════════════

Tu es un développeur Python senior spécialisé dans les applications IA
métier pour le secteur public français. Tu maîtrises Streamlit, les APIs
de Vision LLM (Claude, Mistral, Ollama) et les bonnes pratiques de
développement (code lisible, gestion d'erreurs, sécurité, RGPD).

═══════════════════════════════════════════════════════════════
CONTEXTE DU PROJET
═══════════════════════════════════════════════════════════════

Je suis chef de projet MOA au Conseil départemental de Seine-Saint-Denis
(CD93), à la Maison Départementale des Personnes Handicapées (MDPH).

Je dois développer un POC (prototype) pour démontrer une capacité IA :
la lecture automatique de documents manuscrits (LAD) avec extraction
d'entités précises, en vue d'alimenter le SI métier Iodas/Multigest.

Ce POC sera utilisé :
- pour présenter à mon sponsor (Lucie Dufour, Directrice) une démo concrète
- comme support pédagogique en formation
- comme base de discussion avec les agents MDPH pour valider l'UX cible

Ce POC NE SERA PAS utilisé sur de vraies données usagers (RGPD, AIPD non
encore validée). Il sera testé avec des images fictives ou anonymisées.

═══════════════════════════════════════════════════════════════
BESOIN FONCTIONNEL
═══════════════════════════════════════════════════════════════

L'application doit :

1. Permettre à un utilisateur de charger une image (JPG, PNG, WebP)
   contenant du texte manuscrit en français.

2. Envoyer cette image à un modèle Vision LLM avec un prompt qui demande
   d'extraire UNIQUEMENT 3 informations :
   - Nom de famille
   - Prénom
   - Âge

3. Le modèle doit IGNORER tout autre texte présent dans l'image
   (adresses, numéros, dates, commentaires, etc.).

4. Si une information est absente ou illisible, le modèle doit répondre
   "non détecté" pour ce champ, sans rien inventer.

5. Afficher le résultat sous forme d'un FORMULAIRE pré-rempli, avec :
   - 3 champs éditables (Nom, Prénom, Âge)
   - Un indicateur de confiance IA (élevée / moyenne / faible)
   - Un bouton "Valider" qui simule l'enregistrement
   - Un bouton "Corriger" qui permet à l'utilisateur de modifier avant validation

6. La validation humaine doit être SYSTÉMATIQUE : aucune donnée extraite
   ne doit être enregistrée sans confirmation de l'utilisateur.

═══════════════════════════════════════════════════════════════
EXIGENCES TECHNIQUES
═══════════════════════════════════════════════════════════════

- Langage : Python 3.9+
- Interface : Streamlit (page web locale)
- Vision LLM : prévoir 3 options au choix dans l'application
  - Option 1 : API Claude (anthropic) — qualité maximale
  - Option 2 : API Mistral (mistralai) — souverain européen
  - Option 3 : Ollama local (modèle qwen2.5vl ou llava) — 100% offline

- L'utilisateur choisit son moteur dans la sidebar Streamlit
- Pour Claude et Mistral : champ de saisie sécurisé pour la clé API
- Pour Ollama : sélecteur de modèle

- Format de réponse du LLM : JSON strict avec les clés :
  { "nom": "...", "prenom": "...", "age": "...",
    "confiance": "élevée|moyenne|faible", "remarques": "..." }

- Gestion d'erreurs robuste (JSON malformé, API indisponible, image
  invalide, clé API manquante, etc.)

- Code commenté en français, lisible, organisé en fonctions claires.

═══════════════════════════════════════════════════════════════
EXIGENCES UX
═══════════════════════════════════════════════════════════════

- Interface en français
- Sobre et institutionnelle (ce sera utilisé en démo secteur public)
- Bandeau d'avertissement visible : "POC pédagogique — pas de vraies données"
- Indicateur de chargement pendant l'appel au LLM
- Affichage clair du score de confiance (couleur : vert / orange / rouge)
- Possibilité de voir la réponse brute JSON du LLM (mode debug, dans un expander)

═══════════════════════════════════════════════════════════════
LIVRABLES ATTENDUS
═══════════════════════════════════════════════════════════════

1. Un fichier `app.py` contenant l'application complète, prête à lancer
2. Un fichier `requirements.txt` avec les dépendances
3. Un fichier `README.md` qui explique :
   - Comment installer (étape par étape)
   - Comment obtenir une clé API (liens vers Anthropic et Mistral)
   - Comment installer Ollama si on veut le mode local
   - Comment lancer l'application
   - Les limites du POC (pas pour la production)

═══════════════════════════════════════════════════════════════
CONTRAINTES IMPORTANTES À RESPECTER
═══════════════════════════════════════════════════════════════

- Ne PAS prétendre que ce POC est utilisable en production
- Ne PAS oublier d'indiquer que la validation humaine est obligatoire
- Ne PAS inclure de fonctionnalité qui contournerait le RGPD
- Indiquer clairement dans le README et dans l'UI que ce POC ne doit
  jamais traiter de vraies données MDPH ou de santé sans hébergement
  SecNumCloud, AIPD validée, et clauses RGPD avec les fournisseurs
- Le prompt envoyé au LLM doit être conçu pour MINIMISER les
  hallucinations (instructions strictes, "non détecté" si pas sûr)

═══════════════════════════════════════════════════════════════
DÉMARCHE ATTENDUE
═══════════════════════════════════════════════════════════════

Avant de coder, tu dois :

1. Me confirmer ce que tu as compris en 3-4 lignes
2. Me poser 2-3 questions si quelque chose n'est pas clair
3. Me proposer une structure de fichiers (arborescence)
4. Me proposer le prompt EXACT que tu vas envoyer au LLM (c'est la
   pièce maîtresse, je dois pouvoir le valider)

Ensuite seulement, tu produiras le code complet.

═══════════════════════════════════════════════════════════════

C'est parti.
```

---

## CONSEILS POUR UTILISER CE PROMPT

### Quand l'utiliser
- Dans une **nouvelle conversation Claude** (claude.ai, app Claude)
- Dans **Claude Code** (le terminal pour développeurs)
- Via **l'API Anthropic** si tu intègres dans un autre outil

### Ce qui se passera ensuite
Claude va :
1. Te confirmer ce qu'il a compris
2. Te poser quelques questions (réponds-y)
3. Te montrer le prompt qu'il enverra au modèle (tu peux le faire ajuster)
4. Te livrer 3 fichiers : `app.py`, `requirements.txt`, `README.md`

### Si tu veux une variante plus simple

Si tu veux que Claude te livre directement le code sans poser de questions, retire la section "Démarche attendue" du prompt et ajoute en bas :

```
Produis directement le code complet sans phase de validation préalable.
```

### Si tu veux étendre les fonctionnalités

Tu peux modifier la section "Besoin fonctionnel" pour ajouter des champs.
Exemple, remplacer le point 2 par :

```
2. Envoyer cette image à un modèle Vision LLM avec un prompt qui demande
   d'extraire les informations suivantes :
   - Nom de famille
   - Prénom
   - Date de naissance
   - Âge
   - Adresse postale
   - Numéro de téléphone
   - Numéro de dossier MDPH s'il est présent
```

### Si tu veux une version multi-pages

Remplace la section "Besoin fonctionnel" point 1 par :

```
1. Permettre à un utilisateur de charger un fichier (JPG, PNG, WebP ou PDF
   multi-pages) contenant du texte manuscrit en français. Si PDF, traiter
   chaque page séparément et présenter les résultats par page.
```

---

## VARIANTES DE PROMPTS POUR D'AUTRES BESOINS

### Variante 1 — Tu veux juste un mini-script Python sans interface

```
Écris-moi un script Python (50 lignes max) qui :
- Prend en argument un chemin vers une image manuscrite
- Appelle l'API Claude Vision pour extraire nom, prénom, âge
- Affiche le résultat en JSON dans la console

Code commenté en français. Gestion d'erreurs basique.
```

### Variante 2 — Tu veux comparer plusieurs modèles

```
Écris-moi une application Streamlit qui compare la précision de
3 modèles Vision LLM (Claude, Mistral Pixtral, GPT-4o) sur l'extraction
de nom/prénom/âge depuis une image manuscrite.

L'utilisateur charge une image, l'application lance les 3 modèles en
parallèle, et affiche les 3 résultats côte à côte avec leur temps de
réponse et leur coût estimé.
```

### Variante 3 — Tu veux la version locale uniquement (RGPD strict)

```
Écris-moi une application Streamlit qui extrait nom/prénom/âge d'une
image manuscrite en utilisant UNIQUEMENT Ollama en local (qwen2.5vl).
Aucun appel à une API externe ne doit être possible.

Justifie ce choix dans le README en expliquant que pour des données
sensibles (santé, données personnelles), seule la solution locale
garantit qu'aucune donnée ne quitte le poste.
```

---

## CE QUE CE PROMPT GARANTIT

✅ Claude comprendra le contexte métier (MDPH, secteur public, RGPD)
✅ Claude utilisera les bonnes pratiques (validation humaine, JSON strict)
✅ Claude refusera d'industrialiser sans cadrage (intégrité méthodologique)
✅ Le code livré sera commenté, structuré, fonctionnel
✅ Le README sera complet pour qu'un non-développeur puisse l'installer

## CE QUE CE PROMPT NE GARANTIT PAS

❌ Que le code marche du premier coup (parfois 1-2 itérations nécessaires)
❌ Que l'extraction soit fiable à 100% (limites des modèles Vision sur manuscrit)
❌ Que ce POC soit utilisable en production (il ne l'est pas, c'est volontaire)
❌ La conformité RGPD réelle (qui passe par DPO, AIPD, contrats fournisseurs)

---

**Auteur** : Léon Dumas — CD93 — Projet MDPH-2026-04
**Usage** : Personnel et pédagogique
**Version** : 1.0 — Mai 2026
