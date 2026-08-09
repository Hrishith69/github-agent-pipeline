import os
import sqlite3
from dotenv import load_dotenv
from github import Auth, Github

# 1. Load Environment Variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
DB_NAME = "issues.db"

if not GITHUB_TOKEN or not GITHUB_REPO:
    raise ValueError("Missing GITHUB_TOKEN or GITHUB_REPO in .env file.")


# 2. Initialize SQLite Database
def init_db():
    """Creates the issues table if it does not already exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS issues (
            issue_number INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT,
            author TEXT,
            status TEXT DEFAULT 'NEW',
            created_at TEXT
        )
    """
    )
    conn.commit()
    conn.close()


# 3. Main Ingestion Logic
def fetch_and_store_issues():
    init_db()

    # Connect to GitHub using the updated Auth pattern
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(GITHUB_REPO)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"🔍 Fetching open issues from {repo.full_name}...\n")

    open_issues = repo.get_issues(state="open")
    new_count = 0
    skipped_count = 0

    for issue in open_issues:
        # Check if issue already exists in SQLite
        cursor.execute(
            "SELECT issue_number FROM issues WHERE issue_number = ?",
            (issue.number,),
        )
        existing = cursor.fetchone()

        if existing:
            print(f"⏭️  Issue #{issue.number} already tracked. Skipping.")
            skipped_count += 1
        else:
            # Insert new issue into SQLite
            cursor.execute(
                """
                INSERT INTO issues (issue_number, title, body, author, status, created_at)
                VALUES (?, ?, ?, ?, 'NEW', ?)
            """,
                (
                    issue.number,
                    issue.title,
                    issue.body or "",
                    issue.user.login,
                    str(issue.created_at),
                ),
            )
            conn.commit()
            print(f"✅ Stored NEW Issue #{issue.number}: '{issue.title}'")
            new_count += 1

    conn.close()
    print(
        f"\n✨ Ingestion complete. Stored: {new_count} new | Skipped: {skipped_count} existing."
    )


if __name__ == "__main__":
    fetch_and_store_issues()