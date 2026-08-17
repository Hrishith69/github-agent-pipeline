import os
import sqlite3
import requests
import traceback
from github import Github
from dotenv import load_dotenv

# Internal Project Modules
from agent import app  # Compiled LangGraph state machine
from logger import logger
from retries import api_retry

# Force reload environment variables from .env
load_dotenv(override=True)

DB_PATH = "issues.db"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


# ==========================================
# 📡 RETRY-PROTECTED EXTERNAL API HELPERS
# ==========================================

@api_retry
def send_slack_alert(issue_number: int, title: str, category: str, confidence: float, draft: str):
    """Sends a formatted Slack alert with automatic 3x retry exponential backoff."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("⚠️ SLACK_WEBHOOK_URL not found in .env. Skipping Slack alert.")
        return

    message_text = f"""🔔 *New GitHub Issue Drafted for Review*
*Issue #{issue_number}:* {title}
*Category:* `{category}` | *Confidence Score:* `{confidence}`

*Draft Response:*
```{draft}```"""
    
    response = requests.post(SLACK_WEBHOOK_URL, json={"text": message_text}, timeout=10)
    response.raise_for_status()
    logger.info(f"✅ Slack alert sent successfully for Issue #{issue_number}")


@api_retry
def post_github_comment(issue_number: int, comment_body: str) -> bool:
    """Posts response to live GitHub issue with automatic 3x retry exponential backoff."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.error("❌ Missing GITHUB_TOKEN or GITHUB_REPO in environment variables.")
        raise ValueError("GitHub credentials missing.")

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    issue = repo.get_issue(number=issue_number)
    issue.create_comment(comment_body)
    logger.info(f"✅ Successfully posted comment to live GitHub Issue #{issue_number}")
    return True


# ==========================================
# 🗄️ DATABASE HELPERS
# ==========================================

def fetch_pending_issues() -> list[dict]:
    """Fetches all unprocessed issues with status 'NEW' from issues.db."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT issue_number, title, body FROM issues WHERE status = 'NEW'")
    rows = cursor.fetchall()
    conn.close()

    return [{"issue_number": row[0], "title": row[1], "body": row[2]} for row in rows]


def update_issue_status(issue_number: int, new_status: str, error_msg: str = None):
    """
    Updates the lifecycle status of an issue in SQLite.
    Dynamically ensures 'error_message' column exists for DLQ failures.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Safely ensure error_message column exists in schema
    cursor.execute("PRAGMA table_info(issues)")
    columns = [col[1] for col in cursor.fetchall()]
    if "error_message" not in columns:
        cursor.execute("ALTER TABLE issues ADD COLUMN error_message TEXT")
        conn.commit()

    if error_msg:
        cursor.execute(
            "UPDATE issues SET status = ?, error_message = ? WHERE issue_number = ?",
            (new_status, error_msg, issue_number),
        )
    else:
        cursor.execute(
            "UPDATE issues SET status = ? WHERE issue_number = ?",
            (new_status, issue_number),
        )
    
    conn.commit()
    conn.close()


# ==========================================
# 📥 CORE DLQ ISSUE PROCESSOR
# ==========================================

def process_issue_with_dlq(issue: dict):
    """
    Processes a single issue through LangGraph, Slack, and PyGithub.
    If any API call fails max retries, traps error in Dead-Letter Queue (FAILED_DLQ).
    """
    issue_num = issue["issue_number"]

    try:
        logger.info(f"⚙️ Processing Issue #{issue_num}: '{issue['title']}'")

        # 1. Run LangGraph Core Agent Triage
        inputs = {
            "issue_number": issue_num,
            "title": issue["title"],
            "body": issue["body"],
        }
        final_state = app.invoke(inputs)

        category = final_state.get("category", "Unknown")
        confidence = final_state.get("confidence_score", 0.0)
        draft = final_state.get("draft_response", "No response generated.")

        # 2. Terminal Preview & Slack Alert
        print(f"\n📂 Category   : {category}")
        print(f"🎯 Confidence : {confidence}")
        print("\n📝 Draft Response Preview:\n" + "-" * 40)
        print(draft)
        print("-" * 40)

        send_slack_alert(issue_num, issue["title"], category, confidence, draft)

        # 3. Decision Gate (Human-in-the-loop)
        user_choice = (
            input("\n👉 Do you approve posting this response to GitHub? [A]pprove / [R]eject / [S]kip: ")
            .strip()
            .upper()
        )

        if user_choice == "A":
            post_github_comment(issue_num, draft)
            update_issue_status(issue_num, "RESOLVED")
            logger.info(f"💾 SQLite status updated to 'RESOLVED' for Issue #{issue_num}\n")
        elif user_choice == "R":
            update_issue_status(issue_num, "REJECTED")
            logger.info(f"🚫 Draft rejected. SQLite status updated to 'REJECTED' for Issue #{issue_num}\n")
        else:
            logger.info(f"⏭️ Skipped Issue #{issue_num}. Status remains 'NEW'.\n")

    except Exception as e:
        # Traps any failure that exceeded max retries and routes issue to DLQ
        error_trace = traceback.format_exc()
        logger.error(f"❌ Issue #{issue_num} failed after max retries!")
        logger.error(f"Stack Trace:\n{error_trace}")

        update_issue_status(issue_num, "FAILED_DLQ", str(e))
        logger.info(f"📥 Issue #{issue_num} moved to Dead-Letter Queue (FAILED_DLQ).\n")


# ==========================================
# 🚀 MAIN PIPELINE EXECUTION LOOP
# ==========================================

def run_pipeline():
    """Fetches pending issues and processes them sequentially."""
    pending = fetch_pending_issues()
    if not pending:
        logger.info("✨ No pending issues with status 'NEW' found in issues.db.")
        return

    logger.info(f"🚀 Found {len(pending)} pending issue(s) to process.\n")

    for issue in pending:
        process_issue_with_dlq(issue)


if __name__ == "__main__":
    run_pipeline()