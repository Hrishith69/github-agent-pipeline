from github import Github
import config

g = Github(config.GITHUB_TOKEN)
repo = g.get_repo(config.GITHUB_REPO)

print(f"Connected to repo: {repo.full_name}")
print("Open Issues:")
for issue in repo.get_issues(state="open"):
    print(f"- #{issue.number}: {issue.title}")