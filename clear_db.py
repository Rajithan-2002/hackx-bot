import asyncio
from app.core.config import supabase


async def clear_database():
    print("Clearing database cache and logs...")
    try:
        response_cache = (
            supabase.table("chat_cache")
            .delete()
            .neq("id", "00000000-0000-0000-0000-000000000000")
            .execute()
        )
        print(
            f"  [SUCCESS] Cleared chat_cache. Deleted rows: {len(response_cache.data) if response_cache.data else 0}"
        )
    except Exception as e:
        print(f"  [ERROR] Failed to clear chat_cache: {e}")

    try:
        response_logs = (
            supabase.table("chat_logs")
            .delete()
            .neq("id", "00000000-0000-0000-0000-000000000000")
            .execute()
        )
        print(
            f"  [SUCCESS] Cleared chat_logs. Deleted rows: {len(response_logs.data) if response_logs.data else 0}"
        )
    except Exception as e:
        print(f"  [ERROR] Failed to clear chat_logs: {e}")

    print("Database clear completed!")


if __name__ == "__main__":
    asyncio.run(clear_database())
