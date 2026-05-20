# POC LAD MDPH — Lecture Automatique de Documents manuscrits

> Démonstrateur pédagogique d'extraction d'entités (Nom, Prénom, Âge) depuis des images manuscrites, via un Vision LLM au choix (Claude, Mistral ou Ollama local).

**Projet** : MDPH-2026-04 — Conseil départemental de Seine-Saint-Denis (CD93)
**Auteur** : Léon Dumas, chef de projet MOA — Maison Départementale des Personnes Handicapées
**Version** : 1.0

---

## ⚠️ Avertissement RGPD — À LIRE AVANT TOUT USAGE

Ce projet est un **POC (Proof of Concept) pédagogique**. Il sert :

- à démontrer une capacité technique à la direction MDPH,
- à servir de support de formation,
- à amorcer la discussion UX avec les agents MDPH.

**Ce POC NE DOIT JAMAIS être utilisé sur de vraies données d'usagers MDPH**, ni sur aucune donnée de santé ou personnelle réelle. Une utilisation en production exigerait au minimum :

- une **AIPD** (Analyse d'Impact Protection des Données) validée par le DPO,
- un **hébergement SecNumCloud** ou équivalent qualifié,
- des **contrats RGPD signés** avec les fournisseurs d'API (Anthropic, Mistral, etc.),
- un **journal d'audit** des accès et traitements,
- une **information préalable** des personnes concernées.

**Tester uniquement avec des images fictives ou anonymisées.**

---

## Fonctionnalités

- Chargement d'images manuscrites (JPG, PNG, WebP)
- Extraction automatique de **3 champs uniquement** : Nom, Prénom, Âge
- Le LLM répond `"non détecté"` plutôt que d'inventer une information
- **Validation humaine systématique** via un formulaire éditable
- Indicateur de confiance IA (élevée / moyenne / faible)
- Mode batch : plusieurs images dans la même session
- Génération d'un **PDF récapitulatif** des extractions validées
- Mode debug pour visualiser la réponse brute JSON du LLM
- 3 moteurs Vision LLM au choix :
  - **Claude (Anthropic)** — qualité maximale, modèle par défaut `claude-haiku-4-5` (le moins cher)
  - **Mistral (Pixtral)** — souverain européen
  - **Ollama (local)** — 100 % offline, aucune donnée ne quitte le poste

---

## Prérequis

- **Python 3.9** ou plus récent
- Une connexion internet (sauf en mode Ollama local)
- Selon le moteur choisi :
  - **Claude** → une clé API Anthropic
  - **Mistral** → une clé API Mistral
  - **Ollama** → Ollama installé localement + un modèle vision téléchargé

---

## Installation (étape par étape)

### 1. Récupérer le projet

Le dossier doit contenir `app.py`, `requirements.txt` et ce `README.md`.

### 2. Créer un environnement virtuel Python

Ouvrez **PowerShell** dans le dossier du projet et lancez :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell refuse l'activation, autorisez l'exécution une seule fois :

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 3. Installer les dépendances

```powershell
pip install -r requirements.txt
```

### 4. Lancer l'application

```powershell
streamlit run app.py
```

Streamlit ouvre automatiquement votre navigateur sur `http://localhost:8501`.

---

## Obtenir une clé API

### Anthropic (Claude)

1. Aller sur [https://console.anthropic.com/](https://console.anthropic.com/)
2. Créer un compte (ou se connecter)
3. Aller dans **API Keys** → **Create Key**
4. Copier la clé (commence par `sk-ant-...`)
5. **Coût indicatif** : `claude-haiku-4-5` ≈ 1 € pour ~1000 extractions

### Mistral (Pixtral)

1. Aller sur [https://console.mistral.ai/](https://console.mistral.ai/)
2. Créer un compte et activer le **Pay-as-you-go**
3. Aller dans **API Keys** → **Create new key**
4. Copier la clé

**Note** : Mistral est l'option **souveraine européenne** (hébergement UE).

---

## Installer Ollama (mode local, 100 % offline)

Le mode Ollama permet d'exécuter le modèle Vision **localement**, sans envoyer aucune donnée à un fournisseur externe. C'est l'option à privilégier pour expérimenter sur des données sensibles (même fictives).

### Installation

1. Télécharger Ollama : [https://ollama.com/download](https://ollama.com/download)
2. Installer (Windows : un simple `.exe`)
3. Au premier lancement, Ollama démarre automatiquement un serveur local sur `http://localhost:11434`

### Télécharger un modèle vision

Dans PowerShell :

```powershell
ollama pull qwen2.5vl:7b
```

Autres modèles vision disponibles :

```powershell
ollama pull llava:7b          # Plus léger
ollama pull qwen2.5vl:32b     # Plus précis mais nécessite ~24 Go RAM
```

### Vérifier l'installation

```powershell
ollama list
```

Vous devez voir `qwen2.5vl:7b` (ou autre) dans la liste.

**Prérequis matériel** : 8 Go de RAM minimum pour `qwen2.5vl:7b`, GPU NVIDIA recommandé pour la vitesse.

---

## Utilisation

1. **Sidebar gauche** : choisir le moteur Vision LLM et saisir la clé API (sauf pour Ollama)
2. **Colonne 1** : charger une image manuscrite et cliquer sur **Extraire les informations**
3. **Colonne 2** : vérifier le formulaire pré-rempli, corriger si besoin, puis **Valider et ajouter au lot**
4. Recommencer avec d'autres images si nécessaire
5. **En bas de page** : cliquer sur **Télécharger le récapitulatif PDF** quand le lot est complet

---

## Architecture (1 seul fichier)

```
PROJET LAD/
├── app.py                                       # Application Streamlit complète
├── requirements.txt                             # Dépendances Python
├── README.md                                    # Ce fichier
└── Prompt_pour_Claude_extraction_manuscrite.md  # Spécification d'origine
```

Le **prompt LLM** (la pièce maîtresse anti-hallucination) est défini en haut de `app.py` dans la constante `EXTRACTION_PROMPT`. Il est facilement modifiable sans toucher au reste du code.

---

## Limites du POC

Ce POC ne couvre **volontairement pas** :

- la production : pas d'authentification, pas de journalisation, pas de gestion des accès
- l'intégration au SI métier (Iodas / Multigest) : la validation simule simplement un ajout au lot
- les volumes industriels : traitement image par image
- la conformité RGPD complète : ce n'est pas son objectif
- la fiabilité 100 % : les modèles Vision actuels peuvent échouer sur des écritures manuscrites difficiles, c'est pourquoi la **validation humaine est obligatoire**

Pour passer en production, prévoir :

- un cadrage juridique (AIPD, contrats fournisseurs, information des personnes)
- une infrastructure conforme (SecNumCloud ou Ollama on-premise)
- une intégration au SI cible (API Iodas/Multigest)
- une supervision (logs, métriques, alertes)
- une boucle de feedback pour améliorer le prompt et mesurer la qualité

---

## Dépannage rapide

| Erreur | Cause probable | Solution |
|---|---|---|
| `Clé API Anthropic manquante` | Champ vide dans la sidebar | Saisir la clé API |
| `Connection refused` (Ollama) | Ollama n'est pas démarré | Lancer `ollama serve` ou redémarrer l'application Ollama |
| `model 'qwen2.5vl:7b' not found` | Modèle non téléchargé | Lancer `ollama pull qwen2.5vl:7b` |
| `Réponse LLM non valide (JSON malformé)` | Le modèle a halluciné ou renvoyé du texte hors JSON | Réessayer, ou changer de modèle. Voir la réponse brute dans l'expander "Mode debug" |
| Application très lente avec Ollama | Pas de GPU ou modèle trop gros | Essayer `llava:7b` (plus léger) |

---

## Crédits

- **Spécification** : `Prompt_pour_Claude_extraction_manuscrite.md` (Léon Dumas, mai 2026)
- **Développement** : Claude (Anthropic) — Opus 4.7
- **Cadre projet** : MDPH-2026-04, Conseil départemental de Seine-Saint-Denis
