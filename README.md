# ZAI

**Executive Humanitarian Intelligence Platform** for Erth Zayed Philanthropies.

Bilingual voice-driven dashboard with a 3D digital human avatar, interactive world map, and conversational portfolio analytics over 210 humanitarian projects across 24 countries.

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build -d
```

Open **http://localhost:8080**

No API keys required — runs fully offline with the deterministic planner, browser speech, and local avatar.

---

## Tech Stack

### Frontend

| Technology | Purpose |
|---|---|
| React 18 + TypeScript | Component architecture, type safety |
| Vite | Build tool, dev server, HMR |
| three.js + GLTFLoader | 3D avatar rendering (Avaturn GLB) |
| React Leaflet | Interactive world map |
| React Chart.js 2 | Budget and status charts |
| Web Speech API | Browser STT/TTS |

### Backend

| Technology | Purpose |
|---|---|
| FastAPI + Uvicorn | REST API, session management |
| nginx | Reverse proxy, static files |
| Ollama / Azure OpenAI | LLM planning and document Q&A |
| Azure AI Speech | Neural TTS + STT (optional) |
| Docker Compose | Container orchestration |

---

## Frontend Development

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000 with hot reload + API proxy
npm run build      # TypeScript check + production build
```

---

## Features

- **Voice Q&A** — speak in Arabic or English, get instant visual + spoken answers
- **3D Avatar** — Avaturn GLB model with 15 Oculus viseme lip sync
- **Interactive Map** — Leaflet with risk-coloured markers, fly-to animations
- **Executive Brief** — pre-computed daily summary at session open
- **Insight Cards** — contextual recommendations based on current filter state
- **Document Intelligence** — upload PDF reports, get LLM summaries and Q&A
- **Bilingual RTL** — full Arabic interface with one-click language switch
- **Demo Mode** — scripted executive walkthrough

---

## Configuration

All settings via `.env`. Each provider can be switched independently:

| Service | Default (free) | Upgrade |
|---|---|---|
| LLM | `mock` (keyword planner) | `ollama` · `azure` · `anthropic` |
| STT | `browser` (Web Speech API) | `azure` (Azure AI Speech) |
| TTS | `browser` (speechSynthesis) | `azure` (Neural TTS + lip sync) |
| Avatar | `static` (3D model / SVG) | `heygen` · `azure` (streaming) |
| Documents | `local` (pdfplumber) | `azure` (Document Intelligence) |

### Azure OpenAI

```env
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments
AZURE_OPENAI_MODEL=gpt-4o
AZURE_OPENAI_API_VERSION=2023-05-15
```

### Ollama (self-hosted LLM)

```bash
ollama pull qwen3.5:latest && ollama pull llama3.3:70b
OLLAMA_HOST=0.0.0.0 ollama serve
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_PLANNER_MODEL=qwen3.5:latest
OLLAMA_WRITER_MODEL=llama3.3:70b
```

### Azure TTS (real lip sync)

```env
TTS_PROVIDER=azure
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=uaenorth
```

---

## Architecture

```
Browser (React + three.js avatar, Leaflet map, Chart.js)
    │
    ▼
nginx :8080 ─── static files + /api proxy
    │
    ▼
FastAPI :8000
    ├── core/state.py         delta engine (filter state)
    ├── core/aggregates.py    all figures computed here
    ├── core/engine.py        turn orchestration
    └── providers/            llm · speech · avatar · documents
```

**Two rules:**
1. The LLM emits filter deltas, never figures — all numbers from `aggregates.py`
2. Every provider has a fallback — the demo cannot fail

---

## Project Structure

```
frontend/
  src/
    App.tsx                       root component — boot, query, speech
    main.tsx                      React entry point
    styles.css                    design system
    components/
      TopBar.tsx                  header, providers, demo, language
      Avatar3D.tsx                3D avatar (forwardRef + imperative API)
      SvgAvatar.tsx               2D fallback
      KpiBar.tsx                  headline figures
      WorldMap.tsx                react-leaflet + risk markers
      InsightCard.tsx             recommendation + follow-ups
      Charts.tsx                  bar + doughnut (react-chartjs-2)
      ExecutiveBrief.tsx          daily brief
      DocumentPanel.tsx           upload, summary, Q&A
      Toast.tsx                   notifications
    hooks/
      useVoice.ts                 speech recognition
      useSpeech.ts                TTS (browser + Azure)
      useDemo.ts                  demo mode
    lib/
      api.ts                      typed API client
      i18n.ts                     translations + formatters
      store.tsx                   React Context state
      avatar3d.js                 DigitalHuman (viseme engine)
    types/
      api.ts                      TypeScript interfaces
      global.d.ts                 Web Speech API types
  public/assets/                  avatar.glb

backend/
  app/
    config.py                     environment configuration
    main.py                       app factory
    api/routes.py                 REST endpoints
    core/
      state.py                    delta validation
      aggregates.py               all figures computed here
      engine.py                   session + turn orchestration
    providers/
      llm.py                      MockLLM, OllamaLLM, AzureOpenAILLM, AnthropicLLM
      speech.py                   BrowserSTT, AzureSTT, BrowserTTS, AzureTTS
      avatar.py                   StaticAvatar, HeyGenAvatar, AzureAvatar
      documents.py                local + Azure Document Intelligence
  tests/
    test_core.py                  delta semantics, validation
```

---

## Data

210 projects · 181 active · 24 countries · 67 partners · AED 539M · 1,201,100 beneficiaries

All data is fictional and illustrative.

---

## License

Confidential — Erth Zayed Philanthropies. Not for redistribution.