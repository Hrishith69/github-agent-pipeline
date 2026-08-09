import os
from dotenv import load_dotenv

# Load key-value pairs from .env file
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./issues.db")

# Safety check
if not GITHUB_TOKEN or not GITHUB_REPO:
    raise ValueError("Missing GITHUB_TOKEN or GITHUB_REPO in your .env file!")