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
Run the SQL scripts in your Supabase dashboard's SQL Editor:
1. First, run the contents of [sql/schema.sql](file:///d:/Projects/hackx-chatbot/sql/schema.sql) to create the tables.
2. Next, run [sql/pgvector.sql](file:///d:/Projects/hackx-chatbot/sql/pgvector.sql) to enable the vector extension and create the matching function.

### 5. Ingestion of Knowledge base
Run the ingestion script to process the sample FAQ and seed exact FAQs:
```bash
python -m backend.ingest
```

### 6. Local Development Running
Start the FastAPI server:
```bash
uvicorn backend.main:app --reload
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
