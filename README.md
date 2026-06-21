# HackX Assistant V1.0

A professional, RAG-powered chatbot widget designed for the **HackX 11.0** (main hackathon) and **HackX Jr 9.0** (junior category) landing pages. 

The backend is engineered using an optimized **LLM-last Architecture** to provide instantaneous responses for common queries, maximize local cache efficiency, and minimize OpenAI API cost overheads.

---

## 🚀 Key Features

* **6-Tier Response Pipeline**: Progresses from zero-cost matching (Greetings, local FAQs, vector caches) up to OpenAI vector search and GPT-4o-Mini fallback.
* **Supabase Integration**: Stores vector embeddings, exact match FAQs, caching logs, and conversation audits.
* **Dynamic Widget UI**: A glassmorphic, mascot-guided widget themed to match the `hackx11` landing page colors and TT Hoves Pro typography.
* **Robust Rate Limiting**: Powered by `slowapi` to protect routes from abuse (default 30 requests/minute per client IP).
* **Containerization Ready**: Includes `Dockerfile` and `docker-compose.yml` for instant, isolated deployment.
* **Fully Tested**: Full integration test suite mapping rate limiting, custom configurations, and routing fallbacks.

---

## 📂 Project Directory Structure

```
hackx-bot/
├── api/
│   └── index.py            # Entrypoint for Vercel serverless deployment
├── app/
│   ├── core/
│   │   ├── database/
│   │   │   ├── init_db.sql # Database schema definitions (PostgreSQL + pgvector)
│   │   │   └── schema.sql  # Backup base schema statements
│   │   ├── data/
│   │   │   ├── aliases.json      # Mapping of alternative terms/synonyms
│   │   │   ├── hackx_faq.md      # FAQ document for HackX 11.0
│   │   │   ├── hackx_jr_faq.md   # FAQ document for HackX Jr 9.0
│   │   │   ├── sample_faq.md     # Setup example FAQ document
│   │   │   └── timeline.md       # Timeline and schedules document
│   │   └── config.py       # Configuration loader & client initialization (Supabase, variables)
│   ├── middleware/
│   │   └── rate_limit.py   # SlowAPI limiter instance declaration
│   ├── public/             # Static files served by FastAPI (Widget files & mascot assets)
│   │   ├── assets/         # Mascot PNG images mapping launcher states
│   │   ├── index.html      # Local widget testing/mockup page
│   │   ├── widget.css      # Floating chatbot widget styles (Glassmorphic theme)
│   │   └── widget.js       # Widget injection script and greeting animations
│   ├── services/
│   │   ├── cache.py        # In-database response caching logic (Tier 2)
│   │   ├── domain_guard.py # Input topic filtering & validation logic (Tier 1)
│   │   ├── embeddings.py   # OpenAI vector embedding generator
│   │   ├── llm.py          # Prompt template & OpenAI API interactions
│   │   └── rag.py          # Core 6-tier pipeline router
│   ├── scripts/
│   │   ├── ingest.py       # Vector ingestion and FAQ seeding script
│   │   └── setup_db.py     # Automatic database table and extension creator
│   ├── __init__.py
│   └── main.py             # FastAPI application router, static mounting & exception handlers
├── tests/
│   └── test_bot.py         # Automated pytest test cases (9 unit tests + 1 integration test)
├── Dockerfile              # Deployment Dockerfile (python:3.11-slim)
├── docker-compose.yml      # Orchestration compose file
├── .dockerignore           # Excluded contexts for docker builds
├── .env.example            # Environment variables example reference
├── requirements.txt        # Backend dependencies
└── README.md               # Project documentation
```

---

## 🛠️ The 6-Tier Pipeline Architecture

The chatbot processes every message through the following sequence, returning a response as early as possible to minimize costs:

```
User Query ➔ [Tier 1: Domain Guard] ➔ [Tier 2: Response Cache] ➔ [Tier 3: Synonyms/Aliases] 
            ➔ [Tier 4: Exact FAQ] ➔ [Tier 5: Vector Search] ➔ [Tier 6: LLM / Fallback]
```

1. **Tier 1: Domain Guard & Greetings**: Filters out out-of-scope requests using keyword checking. Matches common greetings (e.g. "hi", "hello") immediately with static, zero-cost greeting answers without hitting OpenAI.
2. **Tier 2: Response Cache (`chat_cache`)**: Searches the database for exact MD5 hashes of prior questions. If hit, returns the cached answer instantly and increments the usage count.
3. **Tier 3: Synonym Expansion (`aliases.json`)**: Expands keywords (e.g. "group size" ➔ "team size") to increase the success of exact FAQ lookups.
4. **Tier 4: Exact FAQ Lookup (`faq_exact`)**: Checks if the query matches predefined FAQ questions or their aliases.
5. **Tier 5: High-Confidence Vector Search (`document_chunks`)**: Generates an embedding of the question and queries the Supabase `match_documents` function. If similarity is `≥ 0.70`, it directly returns the closest text chunk.
6. **Tier 6: LLM Synthesis & Fallback**: 
   * **LLM Synthesis (Active by default)**: Passes the closest retrieved context chunks along with the user's recent **Conversation History** to GPT-4o-Mini to generate a custom response.
   * **Retrieval-Only Fallback**: If OpenAI is unavailable or LLM fallback is toggled off, it returns a formatted summary of the top-retrieved context chunks.

---

## 🗄️ Database Tables Schema

The system initializes 4 primary tables in Supabase:

### `faq_exact`
Stores exact question-answer mappings.
* `id` (UUID, Primary Key)
* `question` (Text)
* `answer` (Text)
* `aliases` (JSONB)
* `created_at` (Timestamp)

### `document_chunks`
Stores segmented source documents and their computed embeddings.
* `id` (UUID, Primary Key)
* `chunk_text` (Text)
* `metadata` (JSONB)
* `embedding` (Vector, 1536 dimensions)
* `created_at` (Timestamp)

### `chat_cache`
Stores successful answers mapped by the question's MD5 hash.
* `id` (UUID, Primary Key)
* `question_hash` (Text, Unique)
* `answer` (Text)
* `source` (Text, default 'cache')
* `usage_count` (Integer)
* `created_at` (Timestamp)
* `updated_at` (Timestamp)
* `last_used` (Timestamp)

### `chat_logs`
Audit logs of all inquiries for analytics.
* `id` (UUID, Primary Key)
* `question` (Text)
* `answer` (Text)
* `route_used` (Text)
* `confidence` (Float)
* `timestamp` (Timestamp)

---

## ⚙️ Environment Configuration

Create a `.env` file in the root directory:

```env
# Supabase HTTP Client Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-service-role-or-anon-key

# Supabase Postgres URL (required for setup_db.py schema initializations)
SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres

# OpenAI Credentials
OPENAI_API_KEY=sk-proj-your-api-key

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
   Run the setup script to construct tables and create the vector matching function:
   ```bash
   python -m app.scripts.setup_db
   ```

3. **Ingest Knowledge base & FAQs**:
   Runs vector parsing and uploads data to Supabase:
   ```bash
   python -m app.scripts.ingest
   ```

4. **Run Server Locally**:
   ```bash
   uvicorn app.main:app --reload
   ```
   Verify local setup by opening [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

---

### 2. Running with Docker

Build and run the entire backend containerized using Docker Compose:

```bash
# Build and run container
docker compose up -d --build

# View container logs
docker compose logs -f
```

---

## 💬 Widget Embedding

To embed the floating assistant on any website, copy and paste this script tag right before the closing `</body>` tag:

```html
<!-- Replace localhost with your production server URL when deploying -->
<script src="http://localhost:8000/widget.js"></script>
```

### Widget UI Customization
The widget colors, buttons, and scrolls can be customized in [app/public/widget.css](file:///d:/HackX/hackx-bot/app/public/widget.css). Custom properties are exposed under `:root` for simple changes:

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
