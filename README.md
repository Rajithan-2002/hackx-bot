# HackX Assistant V1.0

A professional, high-performance virtual assistant chatbot widget designed for the **HackX 11.0** (main category) and **HackX Jr 9.0** (junior category) landing pages. 

The backend is built around a streamlined **3-Tier Groq Context Stuffing Architecture** that bypasses complex vector similarity index computations. It provides fast, contextually grounded answers directly utilizing local rulebook documents while caching common queries in Supabase to minimize API overhead and latency.

---

## 🚀 Key Features

* **3-Tier Response Pipeline**: Progresses from static zero-cost greetings, through a database-backed response cache, up to direct Groq context-stuffing generation.
* **Groq Integration & Context Stuffing**: Feeds the complete markdown rulebooks directly into Groq's high-speed API (e.g., Llama 3) for accurate synthesis without embedding retrieval.
* **API Key Rotation**: Automatically cycles through a comma-separated list of Groq/OpenAI keys to prevent rate limit bottlenecks.
* **Multi-Competition Isolation**: Uses `competition_id` (e.g., `hackx` or `hackxjr`) to isolate system prompts, rulebooks, and response caches.
* **Supabase Integration**: Manages response caching (`chat_cache`) and analytical logs (`chat_logs`) to monitor performance.
* **Dynamic Widget UI**: A glassmorphic, mascot-guided widget themed to match the `hackx11` landing page colors and typography.
* **Robust Rate Limiting**: Powered by `slowapi` to protect routes from abuse (default 30 requests/minute per client IP).
* **Containerization Ready**: Includes `Dockerfile` and `docker-compose.yml` for instant, isolated deployment.

---

## 📂 Project Directory Structure

```
hackx-bot/
├── api/
│   └── index.py            # Entrypoint for Vercel serverless deployment
├── app/
│   ├── core/
│   │   ├── database/
│   │   │   ├── init_db.sql # Idempotent schema setup (PostgreSQL + pgvector)
│   │   │   └── schema.sql  # Backup base schema statements
│   │   ├── data/
│   │   │   ├── hackx_faq.md      # FAQ document for HackX 11.0
│   │   │   ├── hackx_jr_faq.md   # FAQ document for HackX Jr 9.0
│   │   │   ├── sample_faq.md     # Setup example FAQ document
│   │   │   └── timeline.md       # Timeline and schedules document
│   │   └── config.py       # Config loader & client initialization (Supabase, rotation keys)
│   ├── middleware/
│   │   └── rate_limit.py   # SlowAPI limiter instance declaration
│   ├── services/
│   │   ├── cache.py        # In-database response caching logic (Tier 1)
│   │   ├── llm.py          # Prompt template, local doc loading, & Groq client rotation
│   │   └── rag.py          # Core 3-tier pipeline router
│   ├── scripts/
│   │   ├── ingest.py       # [Deprecated] Ingestion print placeholder
│   │   └── setup_db.py     # Idempotent database table creator
│   ├── __init__.py
│   └── main.py             # FastAPI app, static routes mounting & exception handlers
├── public/                 # Static files (Served by FastAPI)
│   ├── assets/             # Mascot PNG images mapping launcher states
│   ├── index.html          # Local widget testing/mockup page
│   ├── widget.css          # Floating chatbot widget styles (Glassmorphic theme)
│   └── widget.js           # Widget injection script, markdown parsing, and greetings
├── tests/
│   └── test_bot.py         # Automated pytest test cases (5 unit and integration tests)
├── Dockerfile              # Deployment Dockerfile (python:3.11-slim, two-stage build)
├── docker-compose.yml      # Orchestration compose file
├── .dockerignore           # Excluded contexts for docker builds
├── .env.example            # Environment variables example reference
├── requirements.txt        # Backend dependencies
└── README.md               # Project documentation
```

---

## 🛠️ The 3-Tier Pipeline Architecture

Every incoming question is routed through the following pipeline to balance response speed and API cost:

```
User Query ➔ [Tier 0: Greeting Detection] ➔ [Tier 1: Response Cache] ➔ [Tier 2: Groq Context Stuffing]
```

1. **Tier 0: Greeting Detection (Zero Cost)**: Matches common greetings statically (e.g. "hi", "hello") without calling any external LLM APIs.
2. **Tier 1: Response Cache (`chat_cache`)**: Searches the database for exact hashes of prior questions (scoped to the specific `competition_id`). If hit, returns the cached answer instantly.
3. **Tier 2: Groq Context Stuffing**: 
   * Loads the competition-specific Markdown file directly from `app/core/data/` (e.g., combining FAQ and timeline files).
   * Passes the full rulebook, the conversation history, and the new question directly into Groq's high-speed completion API.
   * Caches the output in the database and logs the audit entry.

---

## 🗄️ Database Tables Schema

The system initializes the following tables in Supabase:

### `chat_cache`
Stores successful answers mapped by the question's MD5 hash (incorporating the `competition_id`).
* `id` (UUID, Primary Key)
* `question_hash` (Text, Unique)
* `answer` (Text)
* `source` (Text, default 'cache')
* `usage_count` (Integer)
* `created_at` (Timestamp)
* `updated_at` (Timestamp)
* `last_used` (Timestamp)

### `chat_logs`
Audit logs of all chatbot inquiries for analytics.
* `id` (UUID, Primary Key)
* `question` (Text)
* `answer` (Text)
* `route_used` (Text)
* `confidence` (Float)
* `timestamp` (Timestamp)

*Note: The `document_chunks` and `faq_exact` tables remain in the schema setup for backward compatibility but are not used at runtime by the new Groq Context Stuffing pipeline.*

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory:

```env
# Supabase HTTP Client Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-service-role-or-anon-key

# Supabase Postgres URL (required for setup_db.py schema initializations)
SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres

# Groq / OpenAI Configuration
# Use OPENAI_API_KEYS with comma-separated keys for API round-robin rotation,
# or OPENAI_API_KEY for a single key.
OPENAI_API_KEY=gsk_your-single-groq-api-key
OPENAI_API_KEYS=gsk_key1,gsk_key2,gsk_key3

# Testing & Cost Optimization Flags
ENABLE_LLM_FALLBACK=True
ENABLE_RETRIEVAL_ONLY_MODE=True
```

---

## 📦 Setup & Deployment Instructions

### 1. Local Python Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database Schema**:
   Run the setup script to construct tables on Supabase:
   ```bash
   python -m app.scripts.setup_db
   ```

3. **Running Database Clears**:
   To purge caches and query logs (useful for staging resets):
   ```bash
   python clear_db.py
   ```

4. **Run Server Locally**:
   ```bash
   uvicorn app.main:app --reload
   ```
   Verify local setup by opening [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

---

### 2. Running with Docker

Build and run the entire backend containerized:

```bash
# Build and run containers
docker compose up -d --build

# View container logs
docker compose logs -f
```

---

## 💬 Widget Embedding

To embed the floating assistant widget on any website, copy and paste this script tag right before the closing `</body>` tag:

```html
<!-- Replace localhost with your production server URL when deploying -->
<script src="http://localhost:8000/widget.js"></script>
```

### Widget UI Customization
Colors, buttons, and scrolls can be customized in [public/widget.css](file:///d:/HackX/hackx-bot/public/widget.css). Custom properties are exposed under `:root`:

```css
:root {
    --hackx-bg: #010814;          /* Landing page background */
    --hackx-card: #041A3A;        /* Widget cards background */
    --hackx-primary: #1A6FD4;     /* Primary button / user message */
    --hackx-cyan: #5BB8FF;        /* High-confidence highlights / glows */
    --hackx-border: rgba(91, 184, 255, 0.15); /* Glassmorphic border overlay */
}
```

---

## 🧪 Testing and Code Quality

### Running Tests
Execute the pytest suite:
```bash
python -m pytest tests/test_bot.py
```

### Code Formatting and Linting
To check and auto-format your Python files to ensure strict code standards, run:

```bash
# Audit files for warnings
ruff check .

# Format code files (PEP 8)
ruff format .
```
