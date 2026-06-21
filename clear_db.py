import asyncio
import os
from backend.config import supabase

async def clear_database():
    print("Clearing database...")
    # Since we can't delete without a filter, we delete where id is not null (which is all rows)
    response = supabase.table("document_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Database cleared!")
    print("Deleted rows:", len(response.data) if response.data else 0)

if __name__ == "__main__":
    asyncio.run(clear_database())
