import os
import sqlite3
import requests
from github import Github
from dotenv import load_dotenv
from agent import app  # Imports compiled LangGraph core agent

# Force load environment variables
load_dotenv(override=True)

DB_PATH = "issues.db"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def fetch_pending_issues() -> list[dict]:
    """Fetches all issues from SQLite with status 'NEW'."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT issue_number, title, body FROM issues WHERE status = 'NEW'"
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {"issue_number": row[0], "title": row[1], "body": row[2]}
        for row in rows
    ]


def update_issue_status(issue_number: int, new_status: str):
    """Updates issue status in SQLite (e.g., RESOLVED, REJECTED)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE issues SET status = ? WHERE issue_number = ?",
        (new_status, issue_number),
    )
    conn.commit()
    conn.close()


def post_github_comment(issue_number: int, comment_body: str) -> bool:
    """Posts the approved draft response as a comment on the live GitHub issue."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        issue = repo.get_issue(number=issue_number)
        issue.create_comment(comment_body)
        print(f"✅ Successfully posted response to GitHub Issue #{issue_number}")
        return True
    except Exception as e:
        print(f"❌ Failed to post to GitHub: {e}")
        return False


def send_slack_alert(issue_number: int, title: str, category: str, confidence: float, draft: str):
    """Sends a formatted notification message to Slack via Webhook."""
    if not SLACK_WEBHOOK_URL:
        print("⚠️ SLACK_WEBHOOK_URL not found in .env. Skipping Slack alert.")
        return

    message_text = f"""🔔 *New GitHub Issue Drafted for Review*
*Issue #{issue_number}:* {title}
*Category:* `{category}` | *Confidence Score:* `{confidence}`

*Draft Response:*
```
{draft}
```"""
    
    payload = {"text": message_text}
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"✅ Slack alert sent for Issue #{issue_number}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send Slack alert: {e}")


def run_pipeline():
    """Main execution loop for Phase 3."""
    pending = fetch_pending_issues()
    if not pending:
        print("✨ No pending issues with status 'NEW' found in issues.db.")
        return

    print(f"🚀 Found {len(pending)} pending issue(s) to process.\n")

    for issue in pending:
        issue_num = issue["issue_number"]
        print("=" * 60)
        print(f"📌 Processing Issue #{issue_num}: {issue['title']}")
        print("=" * 60)

        # 1. Pass issue into LangGraph Core Agent
        inputs = {
            "issue_number": issue_num,
            "title": issue["title"],
            "body": issue["body"],
        }
        final_state = app.invoke(inputs)

        category = final_state.get("category", "Unknown")
        confidence = final_state.get("confidence_score", 0.0)
        draft = final_state.get("draft_response", "No response generated.")

        # 2. Present to Human Reviewer (CLI Gate)
        print(f"\n📂 Category   : {category}")
        print(f"🎯 Confidence : {confidence}")
        print("\n📝 Draft Response Preview:\n" + "-" * 40)
        print(draft)
        print("-" * 40)
        
        # Send Slack Alert before prompting user
        send_slack_alert(issue_num, issue["title"], category, confidence, draft)

        # 3. Decision Prompt
        user_choice = (
            input("\n👉 Do you approve posting this response? [A]pprove / [R]eject / [S]kip: ")
            .strip()
            .upper()
        )

        if user_choice == "A":
            success = post_github_comment(issue_num, draft)
            if success:
                update_issue_status(issue_num, "RESOLVED")
                print(f"💾 SQLite status updated to 'RESOLVED' for Issue #{issue_num}\n")
        elif user_choice == "R":
            update_issue_status(issue_num, "REJECTED")
            print(f"🚫 Draft rejected. SQLite status updated to 'REJECTED' for Issue #{issue_num}\n")
        else:
            print(f"⏭️ Skipped Issue #{issue_num}. Status remains 'NEW'.\n")


if __name__ == "__main__":
    run_pipeline()