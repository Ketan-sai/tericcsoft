# Sales Lead Qualification Assistant

An intelligent full-stack B2B sales lead qualification application built for **Nimbus Software**. The assistant analyzes inbound customer requirements, performs keyword and semantic retrieval against a local product knowledge base using TF-IDF and cosine similarity, and synthesizes structured qualification notes via Groq's high-speed Llama 3.3 70B model.

---

## What It Does
- **Inbound Requirement Intake:** Sales reps or SDRs paste customer requirements, inquiries, or RFP snippets along with optional company and contact details.
- **Local Knowledge Base Retrieval:** Fast in-memory TF-IDF vector search matches the top 3 most relevant Nimbus Software products from a 12-product catalog.
- **Structured Qualification via Groq LLM:** Prompts Groq's `llama-3.3-70b-versatile` with grounded context to produce structured JSON containing:
  - Executive lead summary (2–3 sentences)
  - Matched products with justification of fit
  - Identified customer pain points & needs
  - Actionable recommended next step
  - High-value follow-up questions
  - Lead qualification score (0–100) and priority level (`High`, `Medium`, `Low`)
- **Persistence & History:** Automatically stores all submissions and qualification analyses in an embedded SQLite database (`leads.db`) and displays recent leads history.
- **Product Catalog Explorer:** Allows sales reps to inspect the full Nimbus product catalog directly from the UI.

---

## Tech Stack
- **Python 3.11**
- **Backend:** FastAPI, Uvicorn, SQLAlchemy 2.x (SQLite `leads.db`)
- **Validation:** Pydantic v2
- **LLM Engine:** Groq Python SDK (`llama-3.3-70b-versatile` in JSON mode)
- **Retrieval Engine:** Scikit-learn (`TfidfVectorizer` + `cosine_similarity`)
- **Configuration:** Python-dotenv
- **Frontend:** Vanilla HTML5, CSS3, and modern JavaScript (ES6 `fetch()`, zero build step, no npm/node dependency)
- **Testing:** Pytest + HTTPX (`TestClient`)

---

## Setup
### 1. Prerequisites
- Python 3.11+ installed on your system.

### 2. Create Virtual Environment and Install Dependencies
From the `sales-lead-qualifier` directory:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

*(Alternatively, if using `uv`: `uv venv --python 3.11 .venv && uv pip install -r requirements.txt`)*

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and set your Groq API key (get a free API key at [console.groq.com](https://console.groq.com)):

```env
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_URL=sqlite:///./leads.db
```

---

## Run
Start the application with Uvicorn:

```bash
uvicorn app.main:app --reload
```

Open your browser at:
**[http://localhost:8000](http://localhost:8000)**

The single Uvicorn server serves both the REST API endpoints under `/api` and the static single-page frontend from the root `/`.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check returning status, indexed KB count, and active model |
| `GET` | `/api/knowledge-base` | Complete list of all 12 Nimbus Software products |
| `POST` | `/api/leads` | Qualifies a lead requirement, executes retrieval & LLM, and persists result |
| `GET` | `/api/leads` | Returns recent qualified leads (newest first, supports `?limit=20`) |
| `GET` | `/api/leads/{lead_id}` | Retrieves a single lead by its ID (404 if not found) |

---

## How Retrieval Works
1. **Startup Indexing:** On application startup, `app/data/knowledge_base.json` (12 products) is loaded into memory.
2. **Feature Text Preparation:** For each product, a unified text representation is formed combining `name`, `category`, `description`, `features`, `keywords`, and `ideal_for`.
3. **TF-IDF Vectorization:** A `TfidfVectorizer(stop_words="english", ngram_range=(1, 2))` is fitted once over the corpus to capture single words and key phrases (e.g. "single sign-on", "lead scoring").
4. **Cosine Similarity Matching:** At query time, the incoming lead requirement is transformed into the fitted vector space, and cosine similarities are calculated against the matrix.
5. **Relevance Thresholding & Fallback:** Results are ranked descending. Matches with a relevance score below `0.02` are dropped. If no product clears the threshold, the top 2 products are retained as fallback context so the LLM always receives grounding material.

---

## Prompting Strategy
- **Strict Persona & Domain Grounding:** The system prompt establishes the LLM as a B2B sales qualification analyst for Nimbus Software with strict negative constraints ("Only reference products that appear in the PRODUCT CONTEXT provided. Never invent products, pricing, or features.").
- **Numbered Context Injection:** Retrieved products are formatted as numbered blocks specifying product name, category, description, and feature lists.
- **Enforced JSON Schema:** Uses Groq's native `response_format={"type": "json_object"}` along with explicit JSON schema instructions.
- **Deterministic Temperature:** Uses `temperature=0.3` for consistent, factual qualification scoring and grounding.
- **Automatic Self-Correction & Single Retry:** All model responses are validated against the Pydantic `LLMLeadAnalysis` schema. If JSON decoding or Pydantic validation fails, the assistant appends the exact validation error as feedback and retries the Groq API call once.
- **Graceful Error Handling:** Catches API and validation errors cleanly and returns HTTP 502 with a user-friendly message rather than exposing internal stack traces.

---

## Project Structure
```text
sales-lead-qualifier/
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusions (.env, *.db, venv, caches)
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── app/
│   ├── __init__.py           # Package marker
│   ├── main.py               # FastAPI app, routes, CORS, StaticFiles mount, lifespan hooks
│   ├── config.py             # Loads .env, exposes settings
│   ├── database.py           # SQLite engine, SessionLocal, Base, get_db()
│   ├── models.py             # SQLAlchemy Lead model
│   ├── schemas.py            # Pydantic request/response/validation schemas
│   ├── retrieval.py          # Knowledge base loader + TF-IDF retriever
│   ├── llm.py                # Groq client, prompt engineering, validation & retry logic
│   └── data/
│       └── knowledge_base.json # 12 Nimbus Software products
├── static/
│   ├── index.html            # Responsive single-page UI
│   ├── style.css             # Vanilla CSS styling & responsive layout
│   └── app.js                # Frontend logic, fetch API, validation & UI states
└── tests/
    └── test_api.py           # Pytest suite verifying health and API validation
```

---

## Tests
Run tests with:

```bash
pytest tests/test_api.py
```

The test suite validates:
1. `test_health_and_kb`: `/api/health` returns HTTP 200 and the KB has $\ge$ 10 entries.
2. `test_create_lead_validation`: `POST /api/leads` with a sub-15 character requirement returns HTTP 422.

---

## What I'd Add With More Time
- **Dense Hybrid Search:** Combine sparse TF-IDF with dense embeddings (e.g., FastEmbed or BGE-small) with reciprocal rank fusion (RRF) for better semantic synonym matching.
- **CRM Webhook Integrations:** Automatically sync qualified leads into HubSpot, Salesforce, or NimbusCRM pipelines upon submission.
- **Streaming Response:** Stream the LLM qualification reasoning and follow-up questions to the UI via Server-Sent Events (SSE).
- **Export & Share:** One-click PDF or Slack export for sales reps to share qualification summaries with account executives.
- **Conversation Threading:** Allow sales reps to ask iterative follow-up questions to the LLM about a specific lead.
