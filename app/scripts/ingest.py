import asyncio
import os
import sys
from pypdf import PdfReader
from app.core.config import supabase
from app.services.embeddings import get_embedding

def chunk_text(text: str, chunk_size_words: int = 450, overlap_words: int = 75) -> list[str]:
    """Helper to chunk text with overlap based on words."""
    words = text.split()
    chunks = []
    if len(words) <= chunk_size_words:
        return [text]
    
    start = 0
    while start < len(words):
        end = start + chunk_size_words
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start += (chunk_size_words - overlap_words)
    return chunks

def is_useful_chunk(text: str) -> bool:
    import re
    # Remove markdown heading markers
    cleaned = re.sub(r'^#+\s+.*\n?', '', text).strip()
    return len(cleaned) > 5

def extract_markdown(filepath: str) -> list[dict]:
    """Extract and chunk markdown sections."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading Markdown {filepath}: {e}")
        return []

    sections = content.split("\n## ")
    chunks = []

    # Handle intro before any ##
    if sections and not sections[0].startswith("## "):
        intro = sections[0].strip()
        if intro:
            text_chunks = chunk_text(intro)
            for tc in text_chunks:
                if is_useful_chunk(tc):
                    chunks.append({
                        "chunk_text": tc,
                        "metadata": {"source": os.path.basename(filepath), "section": "General"}
                    })
        sections = sections[1:]

    for section in sections:
        lines = section.strip().split("\n")
        if not lines:
            continue
        heading = lines[0].replace("#", "").strip()
        body = "\n".join(lines[1:]).strip()
        if not body:
            continue

        text_chunks = chunk_text(body)
        for tc in text_chunks:
            chunk_full_text = f"### {heading}\n{tc}"
            if is_useful_chunk(chunk_full_text):
                chunks.append({
                    "chunk_text": chunk_full_text,
                    "metadata": {"source": os.path.basename(filepath), "section": heading}
                })

    return chunks

def extract_pdf(filepath: str) -> list[dict]:
    """Extract and chunk PDF contents."""
    try:
        reader = PdfReader(filepath)
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
        return []

    full_text_parts = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text_parts.append(f"[Page {i+1}]\n{text}")

    full_text = "\n\n".join(full_text_parts)
    text_chunks = chunk_text(full_text)
    
    chunks = []
    for i, tc in enumerate(text_chunks):
        chunks.append({
            "chunk_text": tc,
            "metadata": {"source": os.path.basename(filepath), "section": f"Chunk {i+1}"}
        })
    return chunks

async def ingest_file(filepath: str):
    if not supabase:
        print("Error: Supabase client is not configured.")
        return

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".md":
        chunks = extract_markdown(filepath)
    elif ext == ".pdf":
        chunks = extract_pdf(filepath)
    else:
        print(f"Unsupported file format: {ext}")
        return

    print(f"Ingesting {len(chunks)} chunks from {filepath}...")
    for chunk in chunks:
        try:
            embedding = await get_embedding(chunk["chunk_text"])
            supabase.table("document_chunks").insert({
                "chunk_text": chunk["chunk_text"],
                "metadata": chunk["metadata"],
                "embedding": embedding
            }).execute()
            print(f"  [SUCCESS] Ingested chunk for: {chunk['metadata'].get('section')}")
        except Exception as e:
            print(f"  [ERROR] Failed to ingest chunk: {e}")

async def seed_exact_faqs():
    if not supabase:
        return
    exact_faqs = [
        {
            "question": "When does registration open?",
            "answer": "Registration for HackX 11.0 opens on August 15th, 2026. Teams must register through the official website at hackx.lk/register.",
            "aliases": ["registration date", "when registration opens", "registration open date"]
        },
        {
            "question": "What is the team size?",
            "answer": "Teams must consist of 2 to 4 members. Solo participation is not allowed. All team members must be from the same university.",
            "aliases": ["team limit", "min members", "max members", "how many people", "team size limit"]
        },
        {
            "question": "Where is the venue?",
            "answer": "The HackX 11.0 main hackathon event will take place at the Royal College MAS Arena in Colombo, Sri Lanka.",
            "aliases": ["venue location", "hackathon venue", "where is it held"]
        }
    ]
    print(f"Seeding {len(exact_faqs)} exact FAQs...")
    for faq in exact_faqs:
        try:
            supabase.table("faq_exact").insert(faq).execute()
            print(f"  [SUCCESS] FAQ: {faq['question']}")
        except Exception as e:
            print(f"  [ERROR] Failed to insert FAQ: {e}")

async def main():
    if supabase:
        print("Clearing existing entries from Supabase...")
        try:
            supabase.table("document_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            supabase.table("faq_exact").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print("Database cleared successfully.")
        except Exception as e:
            print(f"Error clearing tables: {e}")

    if len(sys.argv) < 2:
        # Default ingestion of sample_faq.md, hackx_faq.md and hackx_jr_faq.md
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'core', 'data')
        sample_file = os.path.join(data_dir, 'sample_faq.md')
        hackx_file = os.path.join(data_dir, 'hackx_faq.md')
        hackx_jr_file = os.path.join(data_dir, 'hackx_jr_faq.md')
        timeline_file = os.path.join(data_dir, 'timeline.md')
        
        if os.path.exists(sample_file):
            await ingest_file(sample_file)
        if os.path.exists(hackx_file):
            await ingest_file(hackx_file)
        if os.path.exists(hackx_jr_file):
            await ingest_file(hackx_jr_file)
        if os.path.exists(timeline_file):
            await ingest_file(timeline_file)
            
        await seed_exact_faqs()
    else:
        await ingest_file(sys.argv[1])

if __name__ == "__main__":
    asyncio.run(main())
