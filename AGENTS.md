i# PRD — Root-Me Ranking Slack Bot

## 1. Résumé

Ce document décrit les spécifications d'un bot Slack permettant à un groupe d'amis de consulter, à la demande, le classement Root-Me de ses membres directement dans un canal Slack. Le bot est implémenté en Python et s'appuie sur l'API publique de Root-Me ainsi que sur l'API Slack (Bolt for Python).

---

## 2. Contexte et problème

Un groupe de passionnés de cybersécurité participe ensemble aux challenges Root-Me. Actuellement, comparer les scores et progressions nécessite de consulter manuellement le profil de chaque membre sur le site. Ce processus est fastidieux et casse la dynamique de groupe.

Le bot vise à centraliser et automatiser cette consultation en offrant un classement instantané, lisible et motivant, directement dans Slack.

---

## 3. Objectifs

| Objectif | Mesure de succès |
|---|---|
| Afficher le classement des membres en une commande | Le bot répond en moins de 10 secondes |
| Permettre l'ajout/suppression de membres suivis | Les commandes de gestion fonctionnent sans erreur |
| Afficher le détail d'un membre | Score, rang, nombre de challenges validés affichés |
| Fiabilité | Le bot est disponible 99 % du temps sur le mois |

---

## 4. Utilisateurs cibles

Membres du groupe Slack (5 à 30 personnes) pratiquant Root-Me. Aucun rôle d'administration complexe n'est prévu : tout membre du canal peut interagir avec le bot.

---

## 5. Périmètre fonctionnel

### 5.1 Fonctionnalités — MVP (v1.0)

#### F1 — Commande `/rootme classement`

- **Description** : Affiche le classement trié par score décroissant de tous les membres enregistrés.
- **Données affichées par membre** : rang dans le groupe, pseudo Root-Me, score, nombre de challenges validés, rang global Root-Me.
- **Format de sortie** : message Slack formaté en blocs (Block Kit), avec emojis de podium (🥇🥈🥉) pour le top 3.
- **Gestion d'erreur** : si l'API Root-Me est injoignable, le bot renvoie un message d'erreur explicite.

#### F2 — Commande `/rootme profil <pseudo>`

- **Description** : Affiche le détail d'un membre spécifique.
- **Données affichées** : pseudo, score, rang global, nombre de challenges validés, nombre de challenges par catégorie (si disponible via l'API), lien vers le profil Root-Me.
- **Gestion d'erreur** : si le pseudo n'est pas trouvé, le bot suggère de vérifier l'orthographe.

#### F3 — Commande `/rootme ajouter <pseudo>`

- **Description** : Ajoute un pseudo Root-Me à la liste des membres suivis.
- **Validation** : le bot vérifie que le pseudo existe sur Root-Me via l'API avant de l'enregistrer.
- **Stockage** : le pseudo est persisté dans un fichier JSON local ou une base SQLite.

#### F4 — Commande `/rootme supprimer <pseudo>`

- **Description** : Retire un pseudo de la liste des membres suivis.
- **Confirmation** : le bot demande une confirmation via un bouton interactif avant suppression.

#### F5 — Commande `/rootme aide`

- **Description** : Affiche la liste des commandes disponibles avec une courte description de chacune.

### 5.2 Fonctionnalités — v2.0 (évolutions futures)

| ID | Fonctionnalité | Description |
|---|---|---|
| F6 | Classement automatique périodique | Envoi automatique du classement chaque lundi matin (cron) |
| F7 | Notification de progression | Le bot notifie le canal quand un membre valide un nouveau challenge |
| F8 | Graphiques de progression | Génération d'un graphique (matplotlib) montrant l'évolution des scores sur le temps |
| F9 | Défis internes | Possibilité de lancer des défis temporaires entre membres (« premier à valider le challenge X ») |

---

## 6. Architecture technique

### 6.1 Vue d'ensemble

```
┌────────────┐      HTTPS       ┌──────────────────┐      HTTPS      ┌────────────────┐
│   Slack    │  ◄──────────────► │   Bot Python     │ ──────────────► │  API Root-Me   │
│  (Canal)   │   Slack Bolt SDK │  (Flask/Uvicorn)  │   requests      │  api.root-me.org│
└────────────┘                  └──────┬───────────┘                 └────────────────┘
                                       │
                                       ▼
                                ┌──────────────┐
                                │  SQLite /    │
                                │  JSON file   │
                                └──────────────┘
```

### 6.2 Stack technique

| Composant | Technologie | Justification |
|---|---|---|
| Langage | Python 3.11+ | Écosystème riche, familiarité de l'équipe |
| Framework Slack | `slack-bolt` (Bolt for Python) | SDK officiel Slack, gestion native des commandes slash et interactions |
| Client HTTP | `httpx` (async) | Requêtes parallèles vers l'API Root-Me pour de meilleures performances |
| Persistance | SQLite via `sqlite3` (stdlib) | Léger, sans dépendance externe, suffisant pour < 100 membres |
| Formatage | Slack Block Kit | Messages riches et structurés |
| Hébergement | VPS / Railway / Render / Fly.io | Au choix, un processus Python long-running suffit |
| Gestion de config | Variables d'environnement (`.env` + `python-dotenv`) | Sécurité des tokens |

### 6.3 Dépendances Python

```
slack-bolt>=1.18.0
httpx>=0.27.0
python-dotenv>=1.0.0
```

---

## 7. API Root-Me — Points d'intégration

### 7.1 Authentification

L'API Root-Me nécessite un cookie d'authentification ou une API key. Chaque requête doit inclure le header :

```
Cookie: api_key=<ROOTME_API_KEY>
```

La clé API est récupérable depuis le compte Root-Me d'un des membres (section « Préférences API »).

### 7.2 Endpoints utilisés

| Endpoint | Méthode | Usage |
|---|---|---|
| `GET /auteurs?nom=<pseudo>` | GET | Rechercher un auteur par pseudo |
| `GET /auteurs/<id>` | GET | Récupérer le détail d'un auteur (score, rang, challenges) |
| `GET /auteurs/<id>/validations` | GET | Récupérer la liste des challenges validés |

### 7.3 Données extraites par auteur

```json
{
  "id": 123456,
  "nom": "pseudo",
  "score": 1250,
  "position": 4521,
  "validations": [
    { "id_challenge": 42, "titre": "HTML - Source", "date": "2025-01-15" }
  ]
}
```

> **Note** : La structure exacte des réponses doit être validée lors du développement. L'API Root-Me n'a pas de documentation OpenAPI officielle ; un travail d'exploration (reverse engineering léger) est nécessaire.

### 7.4 Rate limiting

L'API Root-Me applique un rate limit. Le bot doit :

- Espacer les requêtes (min. 500 ms entre chaque appel).
- Implémenter un mécanisme de retry avec backoff exponentiel.
- Mettre en cache les résultats pendant 5 minutes (dictionnaire en mémoire ou cache SQLite).

---

## 8. Commandes Slack — Spécifications détaillées

### 8.1 `/rootme classement`

**Trigger** : l'utilisateur tape `/rootme classement` dans le canal.

**Flux** :

1. Le bot envoie un accusé de réception immédiat (`ack()`) avec un message « ⏳ Récupération du classement en cours... ».
2. Le bot lit la liste des pseudos suivis en base.
3. Pour chaque pseudo, le bot appelle l'API Root-Me (en parallèle avec `asyncio.gather` et `httpx`).
4. Les résultats sont triés par score décroissant.
5. Le bot envoie un message formaté en Block Kit.

**Exemple de rendu Slack** :

```
🏆  Classement Root-Me du groupe

🥇  1. h4ck3r_42        — 2 450 pts  (385 challenges)  — #1 203 mondial
🥈  2. cyber_panda       — 1 890 pts  (298 challenges)  — #2 587 mondial
🥉  3. r00t_noob         — 1 250 pts  (189 challenges)  — #5 102 mondial
     4. script_kiddie_01  —   870 pts  (134 challenges)  — #8 445 mondial
     5. newbie_sec        —   340 pts  ( 52 challenges)  — #18 302 mondial

📅  Mis à jour : 12 mars 2026 à 14:32
```

### 8.2 `/rootme profil <pseudo>`

**Exemple de rendu** :

```
👤  Profil Root-Me : h4ck3r_42

   Score       : 2 450 pts
   Rang global : #1 203
   Challenges  : 385 validés

   📂 Par catégorie :
      Cracking      ██████████░  42/50
      Web-Client    █████████░░  38/45
      Web-Server    ████████░░░  31/40
      Réseau        ███████░░░░  28/38
      ...

   🔗 https://www.root-me.org/h4ck3r_42
```

---

## 9. Modèle de données

### 9.1 Table `members`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER, PK, AUTO | Identifiant interne |
| `rootme_pseudo` | TEXT, UNIQUE, NOT NULL | Pseudo Root-Me |
| `rootme_id` | INTEGER | ID numérique Root-Me (résolu à l'ajout) |
| `added_by` | TEXT | Slack user ID de la personne ayant ajouté le membre |
| `added_at` | DATETIME | Date d'ajout |

### 9.2 Table `cache_scores` (optionnel)

| Colonne | Type | Description |
|---|---|---|
| `rootme_id` | INTEGER, PK | ID Root-Me |
| `score` | INTEGER | Dernier score connu |
| `position` | INTEGER | Dernier rang connu |
| `challenges_count` | INTEGER | Nombre de challenges validés |
| `fetched_at` | DATETIME | Horodatage du cache |

---

## 10. Structure du projet

```
rootme-slack-bot/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                  # Point d'entrée, initialisation Slack Bolt
├── config.py                # Chargement des variables d'environnement
├── db/
│   ├── __init__.py
│   ├── database.py          # Initialisation SQLite, migrations
│   └── models.py            # CRUD members, cache
├── services/
│   ├── __init__.py
│   ├── rootme_client.py     # Client API Root-Me (httpx async)
│   └── ranking.py           # Logique de tri et formatage du classement
├── slack_handlers/
│   ├── __init__.py
│   ├── commands.py          # Handlers des commandes slash
│   └── interactions.py      # Handlers des boutons / interactions
├── utils/
│   ├── __init__.py
│   ├── formatter.py         # Construction des Block Kit messages
│   └── cache.py             # Logique de cache en mémoire / SQLite
└── tests/
    ├── test_rootme_client.py
    ├── test_ranking.py
    └── test_formatter.py
```

---

## 11. Configuration et secrets

Toutes les valeurs sensibles sont stockées en variables d'environnement :

```bash
# .env.example
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_APP_TOKEN=xapp-x-xxxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxx
ROOTME_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABASE_PATH=./data/bot.db
CACHE_TTL_SECONDS=300
ROOTME_REQUEST_DELAY_MS=500
```

---

## 12. Gestion des erreurs

| Scénario | Comportement attendu |
|---|---|
| API Root-Me indisponible (timeout / 5xx) | Message : « ⚠️ L'API Root-Me est temporairement indisponible. Réessaie dans quelques minutes. » |
| Pseudo inconnu lors de l'ajout | Message : « ❌ Le pseudo `<pseudo>` n'existe pas sur Root-Me. Vérifie l'orthographe. » |
| Rate limit atteint | Retry automatique avec backoff. Si > 3 tentatives, message d'erreur. |
| Commande mal formée | Message d'aide contextuel renvoyé à l'utilisateur. |
| Erreur interne du bot | Log de l'erreur complète. Message générique : « 💥 Une erreur interne est survenue. L'admin a été notifié. » |

---

## 13. Sécurité

- **Tokens Slack** : jamais commités dans le dépôt. Utiliser `.env` + `.gitignore`.
- **Clé API Root-Me** : stockée en variable d'environnement uniquement.
- **Validation des entrées** : les pseudos fournis par les utilisateurs sont sanitizés avant d'être utilisés dans les requêtes API (pas d'injection dans les URLs).
- **Vérification des signatures Slack** : activée par défaut dans Bolt, garantit que les requêtes proviennent bien de Slack.

---

## 14. Déploiement

### 14.1 Mode Socket (recommandé pour simplifier)

Utiliser le **Socket Mode** de Slack (`SLACK_APP_TOKEN`) pour éviter d'exposer un endpoint public. Aucun reverse proxy ou certificat TLS nécessaire.

### 14.2 Options d'hébergement

| Option | Coût | Complexité | Remarques |
|---|---|---|---|
| VPS (Hetzner, OVH) | ~3-5 €/mois | Moyenne | Contrôle total |
| Railway | Gratuit (limité) | Faible | Déploiement Git push |
| Render | Gratuit (limité) | Faible | Spin-down après inactivité |
| Fly.io | Gratuit (limité) | Faible | Bonne disponibilité |
| Raspberry Pi local | Coût matériel seul | Moyenne | Dépend de la connexion internet |

### 14.3 Process manager

Utiliser `systemd` (VPS) ou le Procfile de la plateforme pour garantir le redémarrage automatique du bot en cas de crash.

```procfile
worker: python main.py
```

---

## 15. Tests

| Type | Outil | Couverture |
|---|---|---|
| Unitaires | `pytest` | Services, formatage, cache |
| Intégration | `pytest` + `respx` (mock httpx) | Appels API Root-Me simulés |
| Smoke test Slack | Manuel | Vérifier les commandes dans un canal de test |

---

## 16. Jalons

| Jalon | Contenu | Estimation |
|---|---|---|
| **M1 — Setup** | Création du projet, config Slack App, connexion Bolt, commande `/rootme aide` fonctionnelle | 1 jour |
| **M2 — Core** | Intégration API Root-Me, commandes `classement` et `profil` | 2-3 jours |
| **M3 — Gestion membres** | Commandes `ajouter` / `supprimer`, persistance SQLite | 1 jour |
| **M4 — Polish** | Cache, gestion d'erreurs, rate limiting, tests | 1-2 jours |
| **M5 — Déploiement** | Mise en production, documentation README | 0.5 jour |

**Estimation totale : 5 à 7 jours** (en développement loisir, quelques heures par soir).

---

## 17. Limites connues et risques

| Risque | Impact | Mitigation |
|---|---|---|
| L'API Root-Me n'est pas officiellement documentée | La structure des réponses peut changer sans préavis | Encapsuler les appels dans un client dédié, facile à adapter |
| Rate limiting strict de Root-Me | Classement lent si beaucoup de membres | Cache agressif (5 min), requêtes parallèles contrôlées |
| Clé API Root-Me liée à un compte personnel | Si le compte est supprimé, le bot ne fonctionne plus | Documenter la procédure de remplacement de la clé |
| Socket Mode incompatible avec certains plans Slack très anciens | Le bot ne se connecte pas | Passer en mode HTTP avec un endpoint public |
