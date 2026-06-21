# HackX Assistant V1.0

A lightweight, RAG-powered chatbot widget for the HackX 11.0 and HackX Jr 9.0 websites. Engineered using an **LLM-last Architecture** to minimize OpenAI costs and respond instantly to common questions.

## Setup Instructions

### 1. Pre-requisites
- Python 3.10+
- A Supabase Project with `pgvector` enabled.
- An OpenAI API Key.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Environment
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

### 4. Database Schema Setup
You can set up the tables, extensions, and functions automatically or manually:

*   **Option A: Automatic Setup**
    Ensure `SUPABASE_DB_URL` is configured in your `.env` file, then run:
    ```bash
    python -m app.scripts.setup_db
    ```

*   **Option B: Manual Setup**
    Copy the SQL contents from [app/core/database/init_db.sql](file:///d:/HackX/hackx-bot/app/core/database/init_db.sql) and run them in your Supabase project's **SQL Editor**.

### 5. Ingestion of Knowledge base
Run the ingestion script to process the sample FAQ and seed exact FAQs:
```bash
python -m app.scripts.ingest
```

### 6. Local Development Running
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000/health](http://localhost:8000/health) to verify connectivity.

---

## Testing the Widget
To test the floating widget, add the script to any HTML page before the closing `</body>` tag:
```html
<script src="http://localhost:8000/widget.js"></script>
```

---

## Testing
Run the automated test suite:
```bash
pytest tests/test_bot.py
```
