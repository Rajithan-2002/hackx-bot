import os
import sys
from dotenv import load_dotenv


def main():
    # Load .env file from the root workspace directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env_path = os.path.join(root_dir, ".env")
    load_dotenv(env_path)

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print(
            "\n[ERROR] SUPABASE_DB_URL environment variable is not set in your .env file."
        )
        print("Please configure SUPABASE_DB_URL in your .env file.")
        print(
            "Format: postgresql://postgres:[your-password]@db.[your-project-id].supabase.co:5432/postgres"
        )
        print(
            "\nYou can retrieve this database connection URL from the Supabase Dashboard:"
        )
        print("  Settings (Gear Icon) -> Database -> Connection string -> URI\n")
        sys.exit(1)

    sql_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "core", "database", "init_db.sql")
    )
    if not os.path.exists(sql_path):
        print(f"\n[ERROR] SQL initialization file not found at: {sql_path}\n")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("\n[INFO] psycopg2 is not installed. Installing psycopg2-binary...")
        import subprocess

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True
            )
            import psycopg2

            print("[SUCCESS] psycopg2-binary installed successfully!\n")
        except Exception as e:
            print(f"[ERROR] Failed to install psycopg2-binary: {e}")
            print("Please run: pip install psycopg2-binary")
            sys.exit(1)

    print(f"Reading SQL schema from: {sql_path}...")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("Connecting to Supabase PostgreSQL database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Executing SQL schema initialization...")
        cursor.execute(sql_content)

        print("\n[SUCCESS] Database schema successfully initialized!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Failed to execute database setup script: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
