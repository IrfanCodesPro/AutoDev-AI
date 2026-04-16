# ⚡ AutoDev AI — Autonomous Software Developer

> A multi-agent AI system that builds complete software projects from a single prompt.

![AutoDev AI](https://img.shields.io/badge/AutoDev-AI-blue?style=for-the-badge)
![Claude](https://img.shields.io/badge/Powered%20by-Claude%20Sonnet-purple?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green?style=for-the-badge)

---

## 🏗️ Architecture

AutoDev AI runs a **6-agent pipeline** that sequentially plans, designs, codes, tests, debugs, and packages your software:

```
User Prompt
    │
    ▼
🧠 Planner Agent      → Analyzes intent, creates structured project plan
    │
    ▼
🏗️ Architect Agent    → Designs file structure & component layout
    │
    ▼
💻 Coding Agent       → Generates complete source code for every file
    │
    ▼
🧪 Testing Agent      → Static analysis (AST), quality scoring
    │
    ▼
🔧 Debugging Agent    → Auto-fixes issues, improves code quality
    │
    ▼
📦 Packaging Agent    → Adds README, .gitignore, requirements.txt → ZIP
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Or enter it directly in the UI.

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Open the dashboard

Navigate to: **http://localhost:8000**

---

## 📁 Project Structure

```
AutoDevAI/
├── backend/
│   ├── main.py                  # FastAPI server & API routes
│   ├── orchestrator.py          # Agent pipeline coordinator
│   └── agents/
│       ├── __init__.py          # BaseAgent (Claude API wrapper)
│       ├── planner_agent.py     # Intent analysis
│       ├── architect_agent.py   # System design
│       ├── coding_agent.py      # Code generation
│       ├── testing_agent.py     # QA & validation
│       ├── debugging_agent.py   # Auto-fix
│       └── packaging_agent.py   # Final assembly
├── frontend/
│   └── index.html               # Full dashboard (single-file)
├── database/
│   └── autodev.db               # SQLite (auto-created)
├── generated_projects/          # Output ZIPs (auto-created)
├── requirements.txt
└── README.md
```

---

## 🎨 GUI Features

- **Dark luxury developer theme** with glassmorphism
- **Real-time agent status** via Server-Sent Events (SSE)
- **Live log console** with color-coded agent messages
- **Agent pipeline visualization** with progress animations
- **Generated file tree** with code preview
- **One-click ZIP download**
- **Project history** with re-download support

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude Sonnet 4 (Anthropic) |
| Backend | Python + FastAPI |
| Database | SQLite |
| Frontend | HTML + Tailwind CSS + Vanilla JS |
| Real-time | Server-Sent Events (SSE) |
| Packaging | Python zipfile |

---

## 📝 Example Prompts

- `"Build a Python Flask blog with login, SQLite, and markdown posts"`
- `"Create a FastAPI REST API with JWT auth and CRUD operations"`
- `"Build a Django e-commerce site with cart and Stripe payments"`
- `"Create a Python CLI password manager with AES encryption"`

---

## ⚙️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Start generation pipeline |
| `GET` | `/api/stream/{id}` | SSE stream for real-time updates |
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/{id}/files` | Get generated files |
| `GET` | `/api/projects/{id}/download` | Download project ZIP |
| `GET` | `/api/stats` | System statistics |

---

## 📄 License

MIT © AutoDev AI
