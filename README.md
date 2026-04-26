# RefugeeConnect AI 🌍
### *Bridging the Information Gap for Migrants and Asylum Seekers in Spain*

<p align="center">
  <img src="https://img.shields.io/badge/Gemma_4-Hackathon-blue?style=for-the-badge&logo=google" alt="Gemma 4 Hackathon"/>
  <img src="https://img.shields.io/badge/Track-Digital_Equity_&_Inclusivity-orange?style=for-the-badge" alt="Impact Track"/>
  <img src="https://img.shields.io/badge/Special_Tech-Ollama-green?style=for-the-badge" alt="Ollama Track"/>
  <img src="https://img.shields.io/badge/Status-Functional_MVP-brightgreen?style=for-the-badge" alt="Status"/>
</p>

---

## 🧭 Origin: A Personal Story

I arrived in Spain as a Cuban political asylum seeker — alone, without family or financial support. Despite speaking Spanish and having an engineering background, everything was new to me: the legal framework, the network of NGOs, the bureaucratic procedures for regularization, healthcare, and social assistance.

Over time, I learned to navigate this system. But I witnessed firsthand how much harder it was for others: people with language barriers, without technical knowledge, traveling with minor children, and vulnerable to misinformation spread through informal channels like social media. I watched people fall into traps — paying for legal procedures that were free, not knowing they could register (*empadronarse*) without a fixed address, or simply not finding the right help because they happened to walk into the wrong NGO office that day.

This fragmentation isn't anyone's fault. Organizations like **Cruz Roja**, **Cáritas**, and **ACCEM** do critical work under severe resource constraints, often relying on well-intentioned volunteers who may not have the information needed to guide people effectively. There is no centralized knowledge layer — and the cost of that gap is paid by the most vulnerable.

**RefugeeConnect AI** is my attempt to build that layer.

---

## 🎯 The Problem: A Fragmented Support Ecosystem

Every year, thousands of people arrive in Spain fleeing conflict or persecution, only to encounter a support ecosystem that is deeply fragmented:

| Challenge | Reality |
|---|---|
| **Information Silos** | Organizations lack coordinated information systems |
| **Geolocation Lottery** | Quality of guidance depends on which branch you visit |
| **Language Barriers** | Most resources exist only in Spanish |
| **Volunteer Dependency** | Guidance hinges on the specific knowledge of an individual |
| **Digital Illiteracy** | Many cannot effectively search for their own rights online |

> **Real example:** Knowing that Cruz Roja helped with my situation, I visited one branch — they couldn't guide me despite genuine effort. I tried another branch in the same city, and got the help I needed. The information existed. The coordination didn't.

---

## 💡 The Solution: A Dual-Inference Architecture

RefugeeConnect AI addresses these barriers through two complementary access modes, designed to be resilient even when one component is under load:

```
┌─────────────────────────────────────────────────────┐
│                  User Interface (Dash)              │
│           Multilingual: ES | EN | AR | FR           │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼                       ▼
┌─────────────┐       ┌─────────────────┐
│  AI Chat    │       │  Resource Map   │
│  Assistant  │       │  (Direct DB)    │
│             │       │                 │
│ Gemma 4 via │       │  OpenStreetMap  │
│ Google ADK  │       │  + SQLite       │
│ cloud/local │       │  (always on)    │
└─────────────┘       └─────────────────┘
       │                       │
       └───────────┬───────────┘
                   ▼
        ┌──────────────────┐
        │  SQLite Database │
        │  (Valencia NGOs) │
        └──────────────────┘
```

**AI Conversational Assistant** — Powered by Gemma 4 via Google ADK, it understands user needs in natural language and provides step-by-step guidance in their native language. An Orchestrator Agent uses a state-based decision tree to handle greetings, incomplete queries, and resource retrieval gracefully.

**Direct Resource Dashboard** — An interactive map (OpenStreetMap via Dash Leaflet) lets users filter and locate services (Legal, Health, Housing, Food, Employment) directly from the database — no AI dependency, always fast.

---

## 🚀 Key Features

- **Multilingual** — Native reasoning in English, Spanish, Arabic, and French
- **Local-First Privacy** — Run Gemma 4 locally via Ollama to protect sensitive user data in offline or privacy-critical environments
- **Hybrid Architecture** — Decoupled FastAPI backend + Plotly Dash frontend for scalability and independent maintenance
- **Safe Tool Design** — Tools return standardized strings (e.g., `NO_RECORDS`) to prevent hallucination loops in smaller local models
- **Resilient by Design** — The map interface works independently of the LLM; users always get *something* useful
- **Dual-Use Potential** — Useful not just for migrants, but also for NGO volunteers who need quick guidance themselves
- **Improved Responsiveness**: Input Blocking: The text input and send button are automatically disabled during AI processing using Dash's running parameter to prevent duplicate messages. Added a chat-status-bar with an "Assistant is thinking..." text to provide clear feedback during latency.
---

## 🏗️ Technology Stack

| Layer | Technology |
|---|---|
| Model (Cloud) | Gemma 4 (31B) via Google AI Studio |
| Model (Local) | Gemma 4 (E2B/E4B) via Ollama & LiteLLM |
| Agent Framework | Google ADK (Agent Development Kit) |
| Backend API | FastAPI (Asynchronous) |
| Frontend | Plotly Dash & Dash Leaflet (OpenStreetMap) |
| Database | SQLite |
| Package Manager | `uv` (reliable dependency resolution) |
| Infrastructure | Docker & Docker Compose |

---

## 🤖 Agent Architecture

The system evolved from an **Orchestrator → Multi-Agent → Tool Specialist** hierarchy to a more streamlined **Orchestrator → Tool** architecture, reducing latency and hallucination risk — especially important for smaller local models.

```
┌──────────────────────────────────────────────┐
│        Orchestrator Agent                    │
│     (State-based Decision Tree)              │
│                                              │
│ GREETING → PROFILE_CHECK → QUERY_PARSE       │
│       → RESOURCE_SEARCH → RESPONSE           │
└──────────────┬───────────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼                     ▼
[get_services]       [get_rigths]
   tool                  tool
```

**Key design decisions:**
- State-based reasoning prevents ambiguous or looping responses
- Tools return normalized strings, not raw objects
- The map bypasses the LLM entirely for resilience and speed
- Error Handling & API Resilience: Robust Retry Logic: The system handles 500 INTERNAL errors from the Google GenAI API by leveraging google-adk's automatic retries.
- State Persistence: The Orchestrator Agent maintains conversational state across API failures, ensuring the "thought process" is not lost even if the backend experiences temporary instability.

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.13+
- [Ollama](https://ollama.com) (for local inference mode)
- Google AI Studio API Key (for cloud mode)
- Docker *(optional, but recommended)*

### Quick Start with Docker

```bash
git clone https://github.com/YOUR_USERNAME/RefugeeConnectAI.git
cd RefugeeConnectAI
docker-compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:8601 |
| API | http://localhost:8000 |

### Manual Setup (using `uv`)

`uv` resolves critical dependency conflicts between `google-adk` and `protobuf`:

```bash
uv sync

# Start the backend
uv run python api_app/IA_api.py

# In a separate terminal, start the frontend
uv run python dash_app/app_code.py
```

---

## 📂 Project Structure

```
refugeeconnect-ai/
│
├── common/                         # Shared resources between containers
│   ├── data/
│   │   ├── schema.sql              # Database schema
│   │   ├── refugeeconnect.db       # SQLite database (Valencia NGOs)
│   │   └── logs/
│   │       └── logs.log
│   └── utils/
│       ├── tools.py                # Shared utilities
│       └── logger.py               # Logging configuration
│
├── api_app/                        # FastAPI Backend Container
│   ├── IA_api.py                   # FastAPI entry point
│   ├── agents/
│   │   ├── agent_manager.py        # AI architecture configuration
│   │   ├── agent.py                # Agent setup
│   │   └── tracing_plugin.py       # AI trace configuration
│   ├── config.py                   # Model & inference mode config
│   ├── Dockerfile.api
│   └── requirements.txt
│
├── dash_app/                       # Dash Frontend Container
│   ├── app.py                      # Dash application entry point
│   ├── TRANSLATION.json            # i18n configuration (ES/EN/AR/FR)
│   ├── Dockerfile.dash
│   └── requirements.txt
│
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

---

## 🌐 Scope & Honest Limitations

This project is a **functional proof of concept**, not a finished product. These constraints are deliberate:

- **Geographic scope:** Limited to Valencia (where I live and have personal experience)
- **Database coverage:** A representative sample of local NGOs — not exhaustive
- **Translation:** The AI translates responses dynamically, but static dashboard labels returned from database are not yet translated (a known technical debt)
- **Local model testing:** Hardware limitations prevented testing with Gemma 4 locally; development used `qwen` as a proxy model via Ollama
- **Session Management:** Currently lacks adequate session handling; interactions are treated in a volatile context suitable for demo purposes
- **Memory Optimization:** Relies on InMemoryService for session memory, which carries risks of data loss and high RAM consumption under load
- **Flow Optimization:** Further testing is required to optimize how the system handles deep LLM data flow errors to prevent frontend freezes during catastrophic API failures

The goal is to demonstrate **viability and impact** — to show what's possible, and invite the organizations, institutions, and developers who have the resources to take it further.

---

## 🔭 Vision: Beyond the Prototype

The concept is extensible in multiple directions:

- **Geographic expansion** — Beyond Valencia to all of Spain, or other countries
- **Population scope** — The same architecture serves homeless individuals, people with addictions, elderly without support, and children at risk (most NGOs already serve these groups)
- **Dual use** — A tool not just for people in need, but for NGO volunteers who need quick answers when helping others
- **Data partnerships** — Formal collaboration with organizations to keep the database current and comprehensive
- **Vector Database Integration (RAG):** Transitioning from pure SQLite queries to a Retrieval-Augmented Generation (RAG) architecture using vector databases to handle complex legal texts more efficiently in resource-constrained environments

---

## 🎯 Hackathon Tracks

This project is submitted to the **Gemma 4 Good Hackathon** under:

1. **Impact Track — Digital Equity & Inclusivity:** Breaking language and bureaucratic barriers for one of the most underserved populations in Europe.
2. **Special Technology Track — Ollama:** Showcasing Gemma 4 running locally for privacy-centric humanitarian use cases, where sensitive personal data must never leave the user's environment.

---

## 👤 Author

**[Jorge Israel Frometa Moya]** 

This project was built from personal necessity, with a personal computer and personal experience. It is submitted with the hope that it reaches people who can give it the resources it deserves.

- **Kaggle:** [@jorgefrometa]
- **LinkedIn:** [www.linkedin.com/in/jorge-israel-frometa-moya]

---

## 🙏 Acknowledgments

- **Google DeepMind** — for the Gemma 4 models and the hackathon opportunity
- **Google** — for the Agent Development Kit (ADK)
- **Cruz Roja, Cáritas, ACCEM, and all NGOs in Spain** — for the work they do every day under difficult conditions.
- **Everyone who shared their story** — the people I met navigating the same system, whose experiences shaped every design decision here