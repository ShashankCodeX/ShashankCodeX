#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = "https://api.github.com/repos/"
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def github_json(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ShashankCodeX-profile-projects",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def fetch(project, token):
    repo = project.get("repo", "").strip()
    if not REPO_NAME.fullmatch(repo):
        raise ValueError(f"Invalid owner/repository in projects.json: {repo!r}")
    merged = dict(project)
    try:
        info = github_json(API_ROOT + repo, token)
        languages = github_json(API_ROOT + repo + "/languages", token)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        print(f"warning: GitHub data unavailable for {repo}: {error}", file=sys.stderr)
        merged.setdefault("stars", 0)
        merged.setdefault("pushed_at", None)
        merged.setdefault("languages", {})
        return merged
    merged["stars"] = info.get("stargazers_count", 0)
    merged["pushed_at"] = info.get("pushed_at")
    merged["description"] = project.get("description") or info.get("description") or ""
    merged["languages"] = languages
    return merged


def main():
    projects = json.loads((ROOT / "projects.json").read_text(encoding="utf-8"))
    if not isinstance(projects, list) or not projects:
        raise ValueError("projects.json must contain at least one project")
    token = os.environ.get("GITHUB_TOKEN", "")
    merged = [fetch(project, token) for project in projects]
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "merged-projects.json"
    if not destination.is_absolute():
        destination = ROOT / destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    print(f"Updated GitHub metadata for {len(merged)} public projects.")


if __name__ == "__main__":
    main()
