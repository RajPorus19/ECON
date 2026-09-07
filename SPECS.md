Oui. Je te propose de spécifier **ECON comme un vrai produit**, avec une architecture suffisamment précise pour commencer à coder directement, mais sans over-engineering inutile.

# ECON — Complete Technical Specification

## 1. Vision

**ECON = Execution & Cognitive Optimization Network**

ECON est un moteur local d'automatisation capable de transformer progressivement des commandes en langage naturel en **flows déterministes exécutables**, afin de réduire :

* les appels au LLM ;
* le nombre de tokens consommés ;
* la latence ;
* la dépendance au raisonnement du LLM ;
* les actions répétitives.

Le LLM, par exemple Hermes/DeepSeek, sert principalement de **teacher / compiler / fallback**.

ECON devient progressivement capable de répondre seul.

---

# 2. Exemple fondamental

Utilisateur :

> « Lance Sonic Crossworlds »

### Première fois

```text
Voice
 ↓
STT
 ↓
ECON
 ↓
Unknown
 ↓
Hermes
 ↓
Intent = launch_program
Entity = Sonic Crossworlds
Provider = Steam
Command = steam steam://rungameid/...
 ↓
Execute
 ↓
Store knowledge
```

### 100e fois

```text
Voice
 ↓
STT
 ↓
ECON
 ↓
"lance" → launch_program
"Sonic Crossworlds" → known entity
 ↓
Known flow
 ↓
Execute
```

**0 appel LLM.**

---

# 3. Architecture générale

```text
                     ┌─────────────────────┐
                     │     Microphone      │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │       STT           │
                     │   Whisper / etc.     │
                     └──────────┬──────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────┐
│                       ECON                            │
│                                                      │
│  ┌────────────┐      ┌──────────────┐               │
│  │ Normalizer │ ───► │ Intent Router │               │
│  └────────────┘      └──────┬───────┘               │
│                              │                       │
│                    ┌─────────┴─────────┐             │
│                    ▼                   ▼             │
│              Known Flow           Unknown           │
│                    │                   │             │
│                    │                   ▼             │
│                    │              Hermes            │
│                    │                   │             │
│                    │                   ▼             │
│                    │             Flow Builder       │
│                    │                   │             │
│                    └─────────┬─────────┘             │
│                              ▼                       │
│                         Executor                    │
│                              │                       │
│                              ▼                       │
│                         Knowledge                   │
└──────────────────────────────────────────────────────┘
```

Le Web UI ne doit **pas** être dans le chemin critique.

```text
                    ECON Core
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       CLI/API       Web UI       Database
```

---

# 4. Principes architecturaux

## Règle #1 — LLM en dernier recours

Le pipeline doit toujours essayer :

```text
exact match
↓
normalized match
↓
alias match
↓
entity match
↓
pattern match
↓
flow matching
↓
LLM
```

Jamais :

```text
Every request → LLM
```

---

## Règle #2 — Le LLM doit créer des connaissances réutilisables

Une réponse du LLM ne doit pas simplement être :

```json
{
  "command": "..."
}
```

Elle doit potentiellement créer :

```text
Intent
Entity
Alias
Flow
Action
Provider
Capability
Relationship
```

---

## Règle #3 — Toute connaissance doit avoir une confiance

Exemple :

```json
{
  "confidence": 0.97,
  "source": "llm",
  "verified": true
}
```

---

# 5. Concepts fondamentaux

ECON repose sur 7 primitives.

## 5.1 Intent

Ce que l'utilisateur veut faire.

Exemples :

```text
launch_program
play_media
pause_media
stop_media
open_website
search_web
send_message
shutdown_computer
```

---

## 5.2 Entity

Une chose sur laquelle l'action porte.

Exemples :

```text
Sonic Crossworlds
Rick and Morty
Firefox
Spotify
Discord
Jellyfin
```

---

## 5.3 Entity Type

```text
application
game
movie
tv_show
music
website
person
device
service
file
folder
```

---

## 5.4 Action

Une opération réellement exécutable.

Exemples :

```text
shell.execute
http.request
application.launch
application.close
media.play
media.pause
filesystem.open
```

---

## 5.5 Flow

Une séquence d'actions permettant d'accomplir une intention.

Exemple :

```text
play_media(Rick and Morty)
```

devient :

```text
resolve_media
      ↓
resolve_jellyfin
      ↓
resolve_media_id
      ↓
play_media
```

---

## 5.6 Provider

Le système qui permet d'effectuer l'action.

```text
Steam
Jellyfin
Spotify
Firefox
Docker
Linux
Windows
macOS
```

---

## 5.7 Alias

Une manière différente de désigner quelque chose.

```text
"Sonic"
"Sonic Crossworlds"
"le Sonic"
"Sonic racing"
```

peuvent pointer vers :

```text
entity: sonic_crossworlds
```

---

# 6. Data Model

Je partirais sur **PostgreSQL**.

Pas besoin de Neo4j au début.

Le graphe peut parfaitement être représenté par des tables relationnelles.

---

# 7. `entities`

```sql
entities
---------
id
name
type
description
normalized_name
metadata
confidence
usage_count
last_used_at
created_at
updated_at
```

Exemple :

```json
{
  "id": "01...",
  "name": "Sonic Crossworlds",
  "type": "game",
  "normalized_name": "sonic crossworlds",
  "metadata": {
    "platform": "steam",
    "app_id": "..."
  },
  "usage_count": 42
}
```

---

# 8. `aliases`

```sql
aliases
-------
id
entity_id
alias
normalized_alias
confidence
usage_count
created_at
```

Exemple :

```text
"Sonic"
"Sonic Cross"
"le jeu Sonic"
```

→ `Sonic Crossworlds`

---

# 9. `intents`

```sql
intents
-------
id
name
description
confidence
usage_count
created_at
updated_at
```

Exemple :

```json
{
  "name": "launch_program",
  "description": "Launch an application or game"
}
```

---

# 10. `intent_aliases`

```sql
intent_aliases
--------------
id
intent_id
phrase
normalized_phrase
confidence
```

Exemple :

```text
lance
démarre
ouvre
exécute
start
run
```

→ `launch_program`

---

# 11. `providers`

```sql
providers
---------
id
name
type
config
capabilities
created_at
```

Exemple :

```json
{
  "name": "Jellyfin",
  "type": "media_server",
  "capabilities": [
    "search",
    "play",
    "pause",
    "stop"
  ]
}
```

---

# 12. `actions`

C'est une table **extrêmement importante**.

```sql
actions
-------
id
name
type
description
executor
parameters_schema
security_level
created_at
updated_at
```

Exemples :

```text
shell.execute
http.request
process.launch
process.kill
filesystem.open
filesystem.delete
```

---

# 13. `action_versions`

Ne modifie pas directement une commande existante.

Versionne-la.

```sql
action_versions
---------------
id
action_id
version
definition
enabled
verified
created_at
```

Exemple :

```json
{
  "action": "steam.launch",
  "version": 2,
  "executor": "shell",
  "command": "steam steam://rungameid/{app_id}",
  "verified": true
}
```

---

# 14. `flows`

```sql
flows
-----
id
name
description
intent_id
version
confidence
usage_count
success_count
failure_count
enabled
created_at
updated_at
```

Exemple :

```text
Flow:
launch_program → Sonic Crossworlds
```

---

# 15. `flow_nodes`

```sql
flow_nodes
----------
id
flow_id
node_type
action_id
entity_id
position
config
```

---

# 16. `flow_edges`

```sql
flow_edges
----------
id
flow_id
source_node_id
target_node_id
condition
```

Tu obtiens ainsi ton graphe.

---

# 17. Exemple de flow

```text
Flow: launch Sonic Crossworlds

Node 1
type = resolve_entity
entity = Sonic Crossworlds

        ↓

Node 2
type = resolve_provider
provider = Steam

        ↓

Node 3
type = execute_action
action = steam.launch
```

---

# 18. Flow Definition

Je recommande d'avoir **un format JSON canonique**.

Exemple :

```json
{
  "name": "launch_game",
  "version": 1,
  "inputs": {
    "game": {
      "type": "entity",
      "entity_type": "game"
    }
  },
  "nodes": [
    {
      "id": "resolve_game",
      "type": "resolve_entity"
    },
    {
      "id": "launch",
      "type": "action",
      "action": "steam.launch"
    }
  ],
  "edges": [
    {
      "from": "resolve_game",
      "to": "launch"
    }
  ]
}
```

---

# 19. Request Processing

Lorsqu'une phrase arrive :

```text
"Lance Sonic Crossworlds"
```

elle passe par :

### Step 1 — Normalize

```text
"Lance Sonic Crossworlds"

↓

"lance sonic crossworlds"
```

Nettoyage :

* accents ;
* ponctuation ;
* espaces ;
* casing ;
* filler words.

---

# 20. Step 2 — Token classification

ECON tente de reconnaître :

```text
lance
  ↓
intent candidate

Sonic Crossworlds
  ↓
entity candidate
```

---

# 21. Step 3 — Intent matching

Chercher dans :

```text
exact alias
↓
normalized alias
↓
prefix
↓
pattern
↓
fuzzy matching
```

Par exemple :

```text
"lance"
"lancer"
"lance-moi"
"démarre"
"ouvre"
```

→

```text
launch_program
```

---

# 22. Step 4 — Entity matching

Recherche :

```text
exact
↓
normalized
↓
alias
↓
fuzzy
↓
semantic
```

Mais **semantic search ne doit pas forcément impliquer un LLM**.

Tu peux utiliser des embeddings locaux plus tard.

---

# 23. Step 5 — Flow matching

ECON cherche :

```text
intent = launch_program
entity = Sonic Crossworlds
```

Puis :

```text
flow candidates
```

Exemple :

```text
launch_program + game + Steam
```

---

# 24. Step 6 — Confidence

Chaque étape produit un score.

Exemple :

```text
Intent confidence       0.99
Entity confidence       1.00
Provider confidence     0.98
Flow confidence         0.99
```

Score final :

```text
0.98
```

Si :

```text
confidence >= threshold
```

→ execute.

Sinon :

```text
→ Hermes
```

---

# 25. Le fallback Hermes

Hermes reçoit **le minimum nécessaire**.

Pas forcément :

> "Here is the entire system..."

Mais plutôt un contexte structuré :

```json
{
  "request": "Lance Sonic Crossworlds",
  "known_intents": [
    "launch_program"
  ],
  "candidate_entities": [],
  "candidate_flows": [],
  "available_providers": [
    "steam",
    "jellyfin"
  ],
  "available_actions": [
    "shell.execute",
    "steam.launch"
  ]
}
```

Hermes répond avec une **structured output**, pas du texte libre.

---

# 26. Hermes Output

Exemple :

```json
{
  "intent": {
    "name": "launch_program",
    "create": false
  },
  "entities": [
    {
      "name": "Sonic Crossworlds",
      "type": "game",
      "create": true
    }
  ],
  "provider": {
    "name": "Steam",
    "create": false
  },
  "flow": {
    "create": true
  },
  "actions": [
    {
      "type": "shell",
      "command": "steam steam://rungameid/123456"
    }
  ]
}
```

---

# 27. Très important : Hermes ne doit PAS avoir accès direct au shell

Je séparerais :

```text
Hermes
   ↓
Proposed Action
   ↓
ECON Validator
   ↓
Permission / Security
   ↓
Executor
```

Jamais :

```text
Hermes → os.system()
```

---

# 28. Executor

L'executor possède plusieurs backends.

```text
Executor
├── ShellExecutor
├── HTTPExecutor
├── ProcessExecutor
├── FilesystemExecutor
├── BrowserExecutor
└── CustomExecutor
```

---

# 29. Shell Executor

Exemple :

```json
{
  "type": "shell",
  "command": "steam steam://rungameid/123456"
}
```

L'executor doit utiliser `subprocess`, **jamais `shell=True` par défaut**.

---

# 30. Security Model

Chaque action possède :

```text
security_level
```

Par exemple :

| Niveau | Action                  |
| ------ | ----------------------- |
| 0      | lecture                 |
| 1      | application launch      |
| 2      | HTTP request            |
| 3      | filesystem modification |
| 4      | process kill            |
| 5      | destructive/system      |

ECON peut avoir :

```text
AUTO
CONFIRM
DENY
```

Exemple :

```text
launch Firefox
→ AUTO

delete directory
→ CONFIRM

shutdown computer
→ CONFIRM

rm -rf /
→ DENY
```

---

# 31. Learning System

C'est probablement **la feature principale du projet**.

Après chaque Hermes execution :

```text
Request
 ↓
Hermes interpretation
 ↓
Execution
 ↓
Success?
 ↓
Knowledge update
```

Si succès :

```text
increase confidence
increase usage_count
create aliases
save flow
```

Si échec :

```text
decrease confidence
mark flow unreliable
ask Hermes again
```

---

# 32. Knowledge Confidence

Exemple :

```text
Sonic Crossworlds
confidence = 0.87
```

Après 10 exécutions réussies :

```text
confidence = 0.97
```

Après un échec :

```text
confidence = 0.90
```

Tu peux utiliser une formule plus robuste ensuite, mais pour le MVP :

```text
success → +0.02
failure → -0.10
```

avec :

```text
min = 0
max = 1
```

---

# 33. Learning des synonymes

Si l'utilisateur dit régulièrement :

```text
"Lance Sonic"
```

et ECON sait qu'il veut dire :

```text
Sonic Crossworlds
```

après plusieurs confirmations :

```text
"Sonic"
 ↓
Sonic Crossworlds
```

devient un alias.

Mais **ne crée pas automatiquement un alias après une seule utilisation ambiguë**.

---

# 34. Usage Frequency

Chaque élément doit avoir :

```text
usage_count
last_used_at
success_count
failure_count
```

Cela permet une optimisation très intéressante.

Si :

```text
Sonic Crossworlds → 300 usages
```

ECON peut garder cette entité extrêmement facilement accessible.

---

# 35. Hot Knowledge

Créer un cache mémoire :

```text
Hot intents
Hot entities
Hot flows
Hot aliases
```

Au démarrage :

```text
PostgreSQL
 ↓
Load frequently used knowledge
 ↓
RAM
```

Donc :

```text
speech → router → RAM → executor
```

peut être extrêmement rapide.

---

# 36. Cache Layers

Je ferais :

```text
L1
Exact phrase cache

L2
Normalized phrase cache

L3
Intent/entity cache

L4
Flow cache

L5
Database

L6
Hermes
```

C'est **la mécanique d'économie principale**.

---

# 37. Exemple

Premier appel :

```text
"Lance Sonic Crossworlds"

L1 MISS
L2 MISS
L3 MISS
L4 MISS
DB MISS
Hermes
```

Après apprentissage :

```text
"Lance Sonic Crossworlds"

L1 HIT

→ execute
```

---

# 38. Mais attention au problème du cache exact

Tu ne veux pas seulement apprendre :

```text
"Lance Sonic Crossworlds"
```

Tu veux apprendre :

```text
launch_program(
    target = Sonic Crossworlds
)
```

Ainsi :

```text
Lance Sonic Crossworlds
Démarre Sonic Crossworlds
Ouvre Sonic Crossworlds
Start Sonic Crossworlds
```

peuvent converger vers le même flow.

---

# 39. Graph Model

Conceptuellement :

```text
[Phrase]
   │
   ▼
[Intent]
   │
   ▼
[Entity]
   │
   ▼
[Provider]
   │
   ▼
[Flow]
   │
   ▼
[Action]
   │
   ▼
[Executor]
```

Exemple :

```text
"Lance Rick and Morty sur Jellyfin"

        │
        ▼
    play_media
        │
        ├──────────────┐
        ▼              ▼
Rick and Morty      Jellyfin
        │              │
        ▼              ▼
    TV Show       Media Server
        │              │
        └──────┬───────┘
               ▼
          play_media
               │
               ▼
         HTTP Executor
```

---

# 40. Web App

Je ferais 6 pages.

## Dashboard

```text
ECON

Requests today          1,238
LLM calls                  72
LLM avoidance            94.2%

Tokens saved             182k
Average latency           48ms
```

---

# 41. Requests

Historique :

```text
08:43  Lance Sonic Crossworlds
       ✓ ECON
       31ms

08:44  Mets Rick and Morty
       ✓ ECON
       43ms

08:45  Lance Blender
       ⚡ Hermes
       2.4s
```

---

# 42. Knowledge

```text
Intents
Entities
Aliases
Providers
Actions
Flows
```

---

# 43. Graph Explorer

Interface interactive.

```text
              launch_program
                /          \
               /            \
       application          game
          /                   \
     Firefox             Sonic Crossworlds
                              |
                            Steam
                              |
                        steam.launch
```

Click sur un node :

```text
Name
Type
Confidence
Usage
Aliases
Connected flows
Last execution
```

---

# 44. Flow Editor

Un éditeur graphique :

```text
┌─────────────┐
│ Resolve     │
│ Entity      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Resolve     │
│ Provider    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Execute     │
│ steam.launch │
└─────────────┘
```

Possibilité de :

* modifier ;
* désactiver ;
* tester ;
* versionner ;
* supprimer.

---

# 45. Hermes Activity

Une page extrêmement utile :

```text
Hermes Calls

Request:
"Lance Sonic Crossworlds"

Reason:
Unknown entity

Decision:
Create entity

Created:
Sonic Crossworlds

Created:
Steam launch flow

Tokens:
1,824

Result:
SUCCESS
```

Cela permet de comprendre **pourquoi ECON a appelé le LLM**.

---

# 46. Optimizations

Dashboard :

```text
LLM avoidance
─────────────

launch_program       99.8%
play_media            94.2%
open_application      99.1%
web_search             31.2%
```

Tu peux donc identifier où ECON apprend bien et où il est mauvais.

---

# 47. Architecture backend

Vu ton background Python/Django, je partirais clairement sur :

```text
Python
FastAPI
PostgreSQL
Redis
Pydantic
SQLAlchemy
```

Pas Django pour le core.

Pourquoi ?

ECON est davantage un **runtime / daemon** qu'une application CRUD classique.

Le web UI peut éventuellement être :

```text
Next.js
TypeScript
React
Tailwind
React Flow
```

---

# 48. Backend structure

```text
econom/
│
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── requests.py
│   │   │   ├── flows.py
│   │   │   ├── entities.py
│   │   │   ├── intents.py
│   │   │   ├── actions.py
│   │   │   ├── providers.py
│   │   │   └── stats.py
│   │   │
│   │   └── router.py
│   │
│   ├── core/
│   │   ├── router.py
│   │   ├── matcher.py
│   │   ├── resolver.py
│   │   ├── confidence.py
│   │   └── cache.py
│   │
│   ├── execution/
│   │   ├── executor.py
│   │   ├── shell.py
│   │   ├── http.py
│   │   └── process.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   └── compiler.py
│   │
│   ├── knowledge/
│   │   ├── entities.py
│   │   ├── intents.py
│   │   ├── flows.py
│   │   └── learning.py
│   │
│   ├── models/
│   │
│   └── config.py
│
├── tests/
│
├── migrations/
│
└── pyproject.toml
```

---

# 49. Runtime API

Le daemon expose par exemple :

```http
POST /v1/execute
```

Body :

```json
{
  "text": "Lance Sonic Crossworlds"
}
```

Response :

```json
{
  "status": "success",
  "intent": "launch_program",
  "entity": "Sonic Crossworlds",
  "flow_id": "flow_123",
  "execution_time_ms": 31,
  "llm_used": false
}
```

---

# 50. Debug mode

Très important.

```http
POST /v1/execute?debug=true
```

Response :

```json
{
  "input": "Lance Sonic Crossworlds",

  "normalization": {
    "text": "lance sonic crossworlds"
  },

  "intent": {
    "value": "launch_program",
    "confidence": 0.99
  },

  "entity": {
    "value": "Sonic Crossworlds",
    "confidence": 1
  },

  "flow": {
    "id": "flow_123",
    "confidence": 0.98
  },

  "llm_used": false,

  "execution": {
    "action": "steam.launch",
    "status": "success"
  }
}
```

---

# 51. CLI

Je ferais aussi une CLI.

```bash
econom run "Lance Sonic Crossworlds"
```

```bash
econom flows list
```

```bash
econom entities list
```

```bash
econom graph Sonic
```

```bash
econom learn
```

```bash
econom test "Lance Rick and Morty"
```

---

# 52. Voice Client

Le voice client est séparé du core.

```text
econom-voice
```

Pipeline :

```text
Microphone
 ↓
VAD
 ↓
STT
 ↓
POST /v1/execute
```

Donc ECON ne dépend absolument pas de Whisper.

Tu peux remplacer :

```text
Whisper
Faster-Whisper
Whisper.cpp
```

sans modifier le moteur.

---

# 53. Event System

Chaque opération génère un event :

```json
{
  "event": "execution.completed",
  "request_id": "...",
  "flow_id": "...",
  "success": true,
  "duration_ms": 42
}
```

Events :

```text
request.received
request.matched
llm.called
knowledge.created
flow.created
execution.started
execution.completed
execution.failed
```

Ça servira énormément au dashboard.

---

# 54. Observability

Stocker :

```text
request
intent
entity
flow
LLM used?
tokens
latency
execution result
```

Puis calculer :

```text
LLM avoidance rate
average latency
tokens consumed
tokens saved
flow success rate
```

---

# 55. Token Saving Calculation

Pour chaque requête :

```text
estimated_tokens_without_econ
-
actual_tokens
=
tokens_saved
```

Par exemple :

```text
Hermes call:
1,200 tokens

ECON:
0 tokens

saved:
1,200
```

Attention : il faut appeler ça **estimated savings** si le baseline n'est pas réellement exécuté.

---

# 56. Self-improvement loop

Le cycle complet devient :

```text
             ┌───────────────┐
             │ User Request  │
             └───────┬───────┘
                     ▼
               ECON Router
                     │
             ┌───────┴───────┐
             │               │
           KNOWN           UNKNOWN
             │               │
             │               ▼
             │             Hermes
             │               │
             │               ▼
             │          New Knowledge
             │               │
             │               ▼
             │          New Flow
             │               │
             └───────┬───────┘
                     ▼
                  Execute
                     │
                ┌────┴────┐
                ▼         ▼
             Success    Failure
                │         │
                ▼         ▼
             Reinforce  Penalize
                │         │
                └────┬────┘
                     ▼
                 Knowledge
```

C'est **le cœur d'ECON**.

---

# 57. MVP

Surtout, **ne développe pas tout ça dès le départ**.

### Phase 1

Objectif :

> Faire fonctionner `"Lance Firefox"` sans LLM après apprentissage.

Implement :

```text
FastAPI
Postgres
Entity
Intent
Alias
Flow
Shell Executor
Hermes connector
Basic router
```

---

### Phase 2

Ajouter :

```text
confidence
learning
flow versioning
execution history
Redis cache
```

---

### Phase 3

Ajouter :

```text
Web UI
graph explorer
flow editor
statistics
Hermes logs
```

---

### Phase 4

Ajouter :

```text
embeddings
semantic matching
automatic aliases
provider discovery
plugins
```

---

### Phase 5

Ajouter le voice client :

```text
VAD
 ↓
Whisper
 ↓
ECON
```

---

# 58. Ce que je NE ferais PAS au début

### ❌ Neo4j

Postgres suffit.

### ❌ Multi-agent

Aucun intérêt pour le problème.

### ❌ Vector DB

Pas nécessaire pour le MVP.

### ❌ LangChain

Tu contrôles beaucoup mieux le système sans abstraction inutile.

### ❌ LLM pour classifier chaque phrase

C'est précisément ce qu'ECON cherche à éliminer.

### ❌ Agent autonome avec accès root

Très mauvaise idée.

---

# 59. Plugin System

À terme :

```text
plugins/
├── steam
├── jellyfin
├── spotify
├── discord
├── docker
├── linux
└── browser
```

Chaque plugin déclare :

```yaml
name: steam

entities:
  - game

capabilities:
  - launch

actions:
  - steam.launch
```

ECON découvre alors les capacités disponibles.

---

# 60. Exemple Steam plugin

```yaml
name: steam

entity_types:
  - game

actions:
  - id: steam.launch
    executor: shell

    parameters:
      app_id:
        type: string

    command:
      - steam
      - "steam://rungameid/{app_id}"
```

---

# 61. Exemple Jellyfin plugin

```yaml
name: jellyfin

capabilities:
  - search
  - play
  - pause
  - stop

actions:
  - jellyfin.search
  - jellyfin.play
```

L'utilisateur dit :

> "Mets Rick and Morty"

ECON peut donc composer :

```text
play_media
   ↓
jellyfin.search
   ↓
jellyfin.play
```

---

# 62. Une propriété essentielle : composabilité

Tu ne veux pas avoir :

```text
Flow A = "Lance Sonic"
Flow B = "Lance Firefox"
Flow C = "Lance VLC"
Flow D = "Lance Spotify"
```

comme quatre flows complètement indépendants.

Tu veux :

```text
launch_program
       │
       ├── application
       └── game
```

avec des actions spécialisées :

```text
steam.launch
firefox.launch
vlc.launch
spotify.launch
```

Ainsi ECON apprend **des concepts**, pas uniquement des phrases.

---

# 63. Architecture conceptuelle finale

```text
                         USER
                           │
                           ▼
                     Speech-to-Text
                           │
                           ▼
                    ┌───────────────┐
                    │ ECON ROUTER   │
                    └───────┬───────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
          ▼                 ▼                  ▼
      Phrase Cache      Knowledge         Flow Engine
          │                 │                  │
          └─────────────────┼──────────────────┘
                            │
                       MATCH FOUND?
                       /          \
                     YES           NO
                      │             │
                      │             ▼
                      │          HERMES
                      │             │
                      │             ▼
                      │       FLOW COMPILER
                      │             │
                      │             ▼
                      │       KNOWLEDGE DB
                      │             │
                      └──────┬──────┘
                             ▼
                         EXECUTOR
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
              SHELL         HTTP       PROCESS
                │            │            │
                └────────────┼────────────┘
                             ▼
                         RESULT
                             │
                             ▼
                       LEARNING LOOP
```

## La philosophie à garder pendant tout le développement

Le système ne doit **pas** devenir :

> « Un LLM qui sait lancer des programmes. »

Il doit devenir :

> **« Un compilateur qui transforme progressivement le langage naturel en programmes d'automatisation locaux. »**

Hermes est alors essentiellement le **compilateur intelligent** utilisé lorsqu'ECON rencontre quelque chose qu'il ne sait pas encore compiler.

Et c'est ce qui rend le projet beaucoup plus intéressant qu'un simple assistant vocal : **plus tu l'utilises, moins il a besoin d'IA.**

