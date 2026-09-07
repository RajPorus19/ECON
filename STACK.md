Oui, **Django + DRF + TanStack** me paraît même plus cohérent pour toi que de partir sur FastAPI + Next.js, surtout vu ton expérience Django/DRF et le fait que tu veux avancer vite.

Le point important est de distinguer **ECON Core**, **API**, **frontend** et **local runtime**. Je te conseillerais une stack assez pragmatique, sans mettre 15 technologies juste parce qu'elles existent.

## Stack que je choisirais

| Composant          | Technologie                | Rôle                                |
| ------------------ | -------------------------- | ----------------------------------- |
| Backend            | **Django**                 | Application principale              |
| API                | **Django REST Framework**  | API du frontend + API runtime       |
| DB                 | **PostgreSQL**             | Knowledge graph + historique        |
| Cache              | **Redis**                  | Cache chaud + éventuellement tâches |
| Async jobs         | **Celery**                 | Learning, indexing, maintenance     |
| Frontend           | **TanStack Start**         | Web application                     |
| Data fetching      | **TanStack Query**         | API state/cache                     |
| Routing            | **TanStack Router**        | Routing frontend                    |
| Tables             | **TanStack Table**         | Logs, entities, flows               |
| Graph              | **React Flow / XYFlow**    | Visualisation des flows             |
| UI                 | **Tailwind CSS**           | Styling                             |
| Components         | **shadcn/ui**              | UI rapide                           |
| Forms              | **TanStack Form**          | Configuration / édition             |
| Validation         | **Zod**                    | Validation frontend                 |
| Backend validation | **DRF serializers**        | Validation API                      |
| LLM                | **Ollama**                 | Hermes / DeepSeek local             |
| STT                | **faster-whisper**         | Speech → text                       |
| VAD                | **Silero VAD**             | Détection début/fin parole          |
| Execution          | Python `subprocess`        | Shell/process                       |
| HTTP execution     | `httpx`                    | APIs/plugins                        |
| Realtime           | **Django Channels** ou SSE | Logs/execution live                 |
| Tests backend      | **pytest + pytest-django** | Tests                               |
| Tests frontend     | **Vitest**                 | Unit tests                          |
| E2E                | **Playwright**             | Tests UI                            |
| Lint Python        | **Ruff**                   | Lint + format                       |
| Types Python       | **mypy**                   | Type checking                       |
| JS package manager | **pnpm**                   | Frontend                            |
| Containers         | **Docker Compose**         | Dev environment                     |
| CI                 | **GitHub Actions**         | Tests/lint/build                    |

---

# 1. Backend : Django + DRF

Je partirais sur un **monolithe Django**, au moins au début.

```text
econom/
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── celery.py
│
├── apps/
│   ├── knowledge/
│   ├── execution/
│   ├── flows/
│   ├── llm/
│   ├── requests/
│   ├── plugins/
│   ├── analytics/
│   └── users/
│
└── tests/
```

Ça te permet de garder une architecture propre sans introduire prématurément des microservices.

---

# 2. Je garderais le "Core" indépendant de Django

C'est probablement le point architectural le plus important.

Même si Django est ton application backend, je ne veux pas que ton moteur ressemble à ça :

```python
class RequestView(APIView):
    ...
    Entity.objects...
    Flow.objects...
    Hermes...
    subprocess...
```

Ce serait rapidement un bordel.

Je ferais plutôt :

```text
DRF
 │
 ▼
Application Services
 │
 ▼
ECON Core
 │
 ├── Matcher
 ├── Resolver
 ├── Flow Engine
 ├── Knowledge Engine
 └── Execution Engine
```

Django sert de :

* persistence ;
* API ;
* authentication ;
* admin ;
* configuration ;
* background jobs.

Le **core métier** reste relativement indépendant.

---

# 3. Django Admin : utilise-le énormément

C'est un composant que tu n'avais pas forcément prévu.

Pour le MVP, ton admin Django peut déjà permettre de gérer :

```text
Entities
Aliases
Intents
Flows
Actions
Providers
Executions
LLM calls
Knowledge
```

Avant même de finir ton frontend.

Ça va te faire gagner **énormément de temps**.

Ton frontend sera ensuite consacré aux fonctionnalités vraiment intéressantes :

* graph explorer ;
* flow editor ;
* dashboard ;
* live execution ;
* visualisation du learning.

---

# 4. PostgreSQL

Je resterais sur PostgreSQL.

Et surtout :

### Pas Neo4j au début.

Ton "graph" est un **concept logique**, pas nécessairement une base graph.

Tu peux avoir :

```text
entities
aliases
intents
flows
flow_nodes
flow_edges
actions
providers
```

avec des FK PostgreSQL.

Plus tard, si tu découvres que les requêtes deviennent réellement problématiques, tu pourras reconsidérer Neo4j.

---

# 5. Redis

Redis aura plusieurs rôles.

### Cache

```text
phrase → resolved flow
entity → entity
alias → entity
```

### Hot knowledge

Les flows fréquemment utilisés peuvent rester en RAM/Redis.

### Celery broker

Tu peux également l'utiliser pour Celery.

Donc :

```text
Django
  │
  ├── PostgreSQL → persistence
  │
  └── Redis → cache + Celery
```

---

# 6. Celery

Je pense que c'est utile, mais **pas pour chaque commande vocale**.

Le chemin critique :

```text
STT
 ↓
DRF
 ↓
ECON
 ↓
Executor
```

doit rester synchrone et rapide.

Celery sert plutôt à :

```text
LLM learning
Embedding generation
Knowledge maintenance
Analytics
Cache warming
Plugin discovery
Cleanup
```

Exemple :

```text
Unknown request
      ↓
Hermes
      ↓
Immediate execution
      ↓
Celery
      ↓
Persist / learn / generate aliases
```

---

# 7. Frontend : TanStack est un excellent choix

Oui, je partirais dessus.

Plus précisément :

### TanStack Start

plutôt que de construire une app React complètement from scratch.

Avec :

```text
TanStack Start
├── TanStack Router
├── TanStack Query
├── TanStack Table
└── TanStack Form
```

Tu as une stack très cohérente.

---

# 8. Pourquoi TanStack plutôt que Next.js ?

Pour **ECON**, tu n'as pas réellement besoin des fonctionnalités lourdes d'un framework type Next.

Ton application est essentiellement :

```text
Dashboard
Admin UI
Graph explorer
Flow editor
Logs
Configuration
```

Donc une architecture :

```text
React
 +
TanStack
 +
DRF
```

est parfaitement adaptée.

Et vu que tu connais déjà Python/Django, ça évite de multiplier les concepts backend.

---

# 9. UI

Je ferais :

```text
Tailwind CSS
+
shadcn/ui
```

Tu peux rapidement construire :

* sidebar ;
* cards ;
* dialogs ;
* command palette ;
* tables ;
* forms ;
* settings ;
* badges ;
* logs.

---

# 10. Graph : React Flow / XYFlow

**Indispensable** pour ton projet.

Tu veux pouvoir afficher :

```text
Intent
   ↓
Entity
   ↓
Provider
   ↓
Action
   ↓
Executor
```

et des flows plus complexes :

```text
Resolve media
       ↓
 ┌─────┴─────┐
 ↓           ↓
Search     Provider
 ↓           ↓
 └─────┬─────┘
       ↓
     Play
```

React Flow est fait pour ça.

---

# 11. TanStack Table

Très utile pour :

### Requests

```text
Timestamp | Request | Flow | LLM | Latency | Status
```

### Entities

```text
Name | Type | Usage | Confidence | Last Used
```

### Flows

```text
Flow | Version | Usage | Success | Confidence
```

### LLM calls

```text
Prompt | Tokens | Reason | Result | Duration
```

---

# 12. TanStack Query

Le frontend ne devrait pas gérer manuellement :

```text
loading
error
cache
refetch
stale data
```

Utilise Query.

Par exemple conceptuellement :

```text
GET /api/flows
GET /api/entities
GET /api/executions
GET /api/stats
```

avec TanStack Query côté frontend.

---

# 13. WebSocket / SSE

Autre composant que je rajouterais à tes specs.

Quand tu dis :

> Lance Rick and Morty

le frontend pourrait afficher en live :

```text
Request received
       ↓
Matching...
       ↓
Flow not found
       ↓
Calling Hermes...
       ↓
Creating flow...
       ↓
Executing...
       ↓
SUCCESS
```

Pour ça, je privilégierais **SSE au début**.

Tu n'as pas nécessairement besoin de WebSockets bidirectionnels.

```text
Browser
   │
   │ GET /events
   ▼
Django
   │
   ▼
Event stream
```

WebSockets seulement si tu trouves un vrai besoin.

---

# 14. LLM : Ollama

Dans ton cas :

```text
ECON
 ↓
LLM Adapter
 ↓
Ollama
 ↓
Hermes / DeepSeek
```

Le backend ne doit **jamais dépendre directement d'Ollama**.

Crée une interface :

```python
class LLMProvider:
    def generate(...)
    def generate_structured(...)
```

Puis :

```text
OllamaProvider
OpenAIProvider
AnthropicProvider
...
```

Tu peux ainsi changer de modèle sans toucher au reste.

---

# 15. Structured Outputs

Très important.

Hermes doit communiquer avec ECON via des **schemas Pydantic**.

Exemple :

```python
class IntentProposal(BaseModel):
    name: str
    confidence: float


class EntityProposal(BaseModel):
    name: str
    type: str
    confidence: float


class ActionProposal(BaseModel):
    type: str
    parameters: dict
```

Puis :

```text
Hermes
 ↓
JSON
 ↓
Pydantic
 ↓
ECON
```

Pas :

```text
Hermes
 ↓
"Sure! Here's what I think..."
```

---

# 16. STT

Je mettrais :

```text
faster-whisper
```

comme premier backend.

Mais même principe :

```python
class STTProvider:
    def transcribe(audio)
```

Puis :

```text
FasterWhisperProvider
WhisperCppProvider
...
```

Ainsi ton voice client reste interchangeable.

---

# 17. VAD

C'est un composant que je rajouterais explicitement.

Sans VAD :

```text
".... Lance Sonic Crossworlds ...."
```

Tu dois gérer toi-même quand enregistrer.

Avec Silero VAD :

```text
silence
 ↓
speech detected
 ↓
record
 ↓
speech ended
 ↓
STT
```

Ça rendra ton assistant vocal beaucoup plus naturel.

---

# 18. Voice Client séparé

Je ne mettrais **pas** le microphone dans Django.

Architecture :

```text
econom-voice
│
├── microphone
├── VAD
├── STT
└── ECON API client
```

Il tourne en background sur ton PC.

```text
Micro
 ↓
VAD
 ↓
Whisper
 ↓
POST /api/v1/execute
```

---

# 19. Execution Layer

Je créerais une vraie abstraction.

```text
execution/
├── base.py
├── shell.py
├── process.py
├── http.py
├── filesystem.py
└── registry.py
```

Avec :

```python
class Executor(Protocol):
    def execute(...)
```

---

# 20. Plugin System

**À prévoir dans la stack**, même si tu ne le développes pas immédiatement.

Je ferais des plugins Python :

```text
econom-plugin-steam
econom-plugin-jellyfin
econom-plugin-spotify
econom-plugin-discord
```

Chaque plugin expose :

```text
Entities
Capabilities
Actions
Resolvers
Executors
```

Par exemple :

```text
JellyfinPlugin
├── resolve_media()
├── search_media()
├── play_media()
├── pause()
└── stop()
```

---

# 21. Important : Plugin Registry

ECON doit avoir :

```text
Plugin Registry
```

qui connaît :

```text
plugin
capabilities
actions
version
enabled
permissions
```

Ainsi Hermes sait quelles capacités existent.

---

# 22. Event Bus

Je l'ajouterais aux specs.

Pas besoin de Kafka.

Un système interne simple suffit :

```text
RequestReceived
IntentMatched
FlowMatched
LLMCalled
KnowledgeCreated
ExecutionStarted
ExecutionCompleted
ExecutionFailed
```

Tu peux ensuite utiliser ces events pour :

* analytics ;
* UI realtime ;
* learning ;
* logs.

---

# 23. Audit Log

**Très important** puisque ECON exécute des commandes sur ton PC.

Chaque action doit laisser une trace :

```text
who
what
when
flow
action
parameters
result
duration
```

Exemple :

```text
09:42:13
User request:
"Lance Firefox"

Flow:
launch_application

Action:
process.launch

Command:
firefox

Result:
SUCCESS
```

---

# 24. Permissions

Autre composant à ne surtout pas oublier.

```text
Action
 ↓
Security Policy
 ↓
Allowed?
 ↓
Executor
```

Exemple :

```text
Open Firefox      → ALLOW
Launch Steam      → ALLOW
Delete file       → CONFIRM
Shutdown          → CONFIRM
Format disk       → DENY
```

---

# 25. Secrets management

Jellyfin va probablement nécessiter :

```text
URL
API key
credentials
```

Ne mets jamais ça dans :

```text
flows
entities
logs
LLM prompts
```

Prévois :

```text
Secret Store
```

Pour le MVP, des variables d'environnement peuvent suffire.

Plus tard :

```text
OS Keychain
Vault
```

---

# 26. Configuration

Je rajouterais une vraie configuration ECON :

```yaml
econom:
  llm:
    provider: ollama
    model: hermes

  matching:
    confidence_threshold: 0.90

  execution:
    default_timeout: 30

  security:
    destructive_actions: confirm
```

---

# 27. Packaging

Le projet devrait être installable :

```bash
pip install econom
```

et idéalement :

```bash
econom start
econom run "Lance Firefox"
econom doctor
```

---

# 28. `econom doctor`

Très utile pour un outil local.

```text
ECON Doctor

✓ PostgreSQL
✓ Redis
✓ Ollama
✓ Hermes
✓ STT
✓ Steam
✓ Jellyfin
✓ Shell executor

Everything looks good.
```

---

# 29. Docker

Pour le développement :

```text
docker-compose.yml

services:

  postgres

  redis

  django
```

Je **ne dockeriserais pas nécessairement le voice client**, ni l'exécution locale.

Ton executor doit pouvoir accéder naturellement à :

```text
Steam
Firefox
applications
filesystem
desktop
```

---

# 30. Monitoring

Pas besoin de Prometheus au début.

Mais prévois des métriques internes :

```text
requests_total
llm_calls_total
llm_tokens_total
cache_hits_total
execution_success_total
execution_failure_total
average_latency
```

Plus tard tu pourras exporter vers Prometheus.

---

# 31. Tests

Je ferais quatre catégories.

### Unit

```text
Matcher
Resolver
Confidence
Flow engine
Security
```

### Integration

```text
Django + PostgreSQL
Django + Redis
ECON + Ollama
ECON + executor
```

### E2E

```text
request
 ↓
matching
 ↓
execution
```

### Frontend

```text
Flow editor
Graph
Dashboard
Tables
```

---

# 32. Stack finale

Je mettrais donc ceci dans ton `stack.md` :

```text
# ECON Stack

## Backend

- Python 3.12+
- Django
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Pydantic
- httpx

## Frontend

- TypeScript
- React
- TanStack Start
- TanStack Router
- TanStack Query
- TanStack Table
- TanStack Form
- Zod
- Tailwind CSS
- shadcn/ui
- XYFlow / React Flow

## AI

- Ollama
- Hermes / DeepSeek
- Pydantic structured outputs

## Voice

- faster-whisper
- Silero VAD

## Execution

- Python subprocess
- HTTPX
- Plugin system

## Realtime

- Server-Sent Events
- Django ASGI

## Testing

- pytest
- pytest-django
- Vitest
- Playwright

## Code Quality

- Ruff
- mypy
- Pre-commit

## Infrastructure

- Docker
- Docker Compose
- PostgreSQL
- Redis
- GitHub Actions
```

---

## Et surtout, je rajouterais ces 8 composants à ton `specs.md`

Parce que ce sont ceux qui risquent de manquer quand tu vas réellement coder :

1. **Provider abstraction** — Steam/Jellyfin/etc. ne doivent pas être hardcodés dans le core.
2. **Plugin system** — permet d'ajouter des capacités sans modifier ECON.
3. **Security / permission engine** — indispensable puisque ECON exécute des commandes.
4. **Audit / execution history** — savoir exactement ce qui a été exécuté.
5. **Event system** — indispensable pour le learning + realtime UI.
6. **LLM/STT provider interfaces** — Ollama/Whisper ne doivent pas être des dépendances du core.
7. **Confidence + matching pipeline** — le véritable moteur d'économie de tokens.
8. **Versioning des flows/actions** — un flow appris ne doit jamais être modifié silencieusement.

### Mon choix d'architecture global serait donc :

```text
                    ┌──────────────────┐
                    │   Voice Client   │
                    │ VAD + Whisper    │
                    └────────┬─────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────┐
│                     DJANGO                         │
│                                                    │
│  DRF API                                           │
│     │                                              │
│     ▼                                              │
│  ┌──────────────────────────────────────────────┐  │
│  │              ECON CORE                      │  │
│  │                                              │  │
│  │ Matcher → Resolver → Flow → Security        │  │
│  │                    │                         │  │
│  │                    ▼                         │  │
│  │                 Executor                    │  │
│  └────────────────────┬─────────────────────────┘  │
│                       │                            │
│          ┌────────────┼────────────┐               │
│          ▼            ▼            ▼               │
│       Plugins       Hermes       Events            │
│                     /DeepSeek                      │
│                                                    │
└───────────┬──────────────────────┬─────────────────┘
            │                      │
            ▼                      ▼
       PostgreSQL                Redis
            │
            ▼
       Knowledge Graph

                     ▲
                     │
              ┌──────┴──────┐
              │  TanStack   │
              │     Web     │
              └─────────────┘
```

**C'est cette stack que je prendrais personnellement pour ECON.** Elle reste relativement simple, mais elle prévoit déjà les morceaux qui deviendront pénibles à rajouter après coup : plugins, sécurité, événements, versioning, providers et séparation du core.
