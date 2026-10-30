#!/usr/bin/env python3
"""
Zero-dependency GitHub Repository Creator & Deployment Tool.
Uses GitHub REST Contents API via Python standard library.
No local git installation required.
"""

import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.error
from pathlib import Path

IGNORE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "env", ".idea", ".vscode"
}
IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd"
}
IGNORE_FILES = {
    "monza_report.html", "spa_report.html", "monza_telemetry.csv"
}

def is_ignored(rel_path: Path) -> bool:
    for part in rel_path.parts:
        if part in IGNORE_DIRS:
            return True
    if rel_path.suffix.lower() in IGNORE_EXTENSIONS:
        return True
    if rel_path.name in IGNORE_FILES:
        return True
    return False

def github_request(endpoint: str, token: str, method: str = "GET", payload: dict = None) -> dict:
    url = f"https://api.github.com{endpoint}" if endpoint.startswith("/") else endpoint
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "F1-ERS-Deployment-Script",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
            msg = f"{err_json.get('message', err_body)}"
        except Exception:
            msg = err_body
        raise RuntimeError(f"GitHub API Error [{e.code}]: {msg}")

def deploy(token: str, repo_name: str, private: bool = False):
    print("Connecting to GitHub API...")
    user_info = github_request("/user", token)
    username = user_info["login"]
    print(f"Authenticated as GitHub user: @{username}")

    # Check / Create repository
    repo_payload = {
        "name": repo_name,
        "description": "Formula 1 Energy Recovery System (ERS) Lap Time & Energy Simulation Engine with Tkinter GUI & Telemetry Lab",
        "private": private,
        "auto_init": False
    }
    print(f"Checking / creating repository '{username}/{repo_name}'...")
    try:
        repo_data = github_request("/user/repos", token, method="POST", payload=repo_payload)
        print(f"Repository created: {repo_data['html_url']}")
    except RuntimeError as e:
        if "already exists" in str(e).lower() or "422" in str(e):
            print(f"Repository '{username}/{repo_name}' already exists.")
            repo_data = github_request(f"/repos/{username}/{repo_name}", token)
        else:
            raise

    repo_full_name = repo_data["full_name"]
    html_url = repo_data["html_url"]
    base_dir = Path(__file__).resolve().parent

    # Fetch existing files in repo (if any) to get their SHAs
    existing_files = {}
    try:
        tree_resp = github_request(f"/repos/{repo_full_name}/git/trees/main?recursive=1", token)
        for item in tree_resp.get("tree", []):
            if item.get("type") == "blob":
                existing_files[item["path"]] = item["sha"]
        print(f"Found {len(existing_files)} existing file(s) in repository.")
    except Exception:
        print("Repository is empty; initializing repository...")

    # Collect files to upload
    files_to_upload = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            file_path = Path(root) / f
            rel_path = file_path.relative_to(base_dir)
            if is_ignored(rel_path):
                continue
            files_to_upload.append(rel_path)

    # Sort files so directories and critical root files are uploaded predictably
    files_to_upload.sort()

    print(f"\nUploading {len(files_to_upload)} files to https://github.com/{repo_full_name} ...")
    success_count = 0
    for rel_path in files_to_upload:
        posix_path = str(rel_path).replace("\\", "/")
        file_path = base_dir / rel_path
        content_bytes = file_path.read_bytes()
        b64_content = base64.b64encode(content_bytes).decode("ascii")

        payload = {
            "message": f"feat: add {posix_path}",
            "content": b64_content,
            "branch": "main"
        }
        if posix_path in existing_files:
            payload["sha"] = existing_files[posix_path]
            payload["message"] = f"chore: update {posix_path}"

        try:
            github_request(f"/repos/{repo_full_name}/contents/{posix_path}", token, method="PUT", payload=payload)
            success_count += 1
            print(f"  [OK] {posix_path}")
        except Exception as e:
            print(f"  [ERROR] {posix_path}: {e}")

    print("\n" + "=" * 65)
    print(f"SUCCESS! All {success_count}/{len(files_to_upload)} files deployed to GitHub:")
    print(f"Repository URL: {html_url}")
    print(f"Clone URL:      https://github.com/{repo_full_name}.git")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Deploy F1 ERS Simulator to GitHub repository.")
    parser.add_argument("--token", help="GitHub Personal Access Token")
    parser.add_argument("--repo", default="f1-ers-simulation", help="Repository name (default: f1-ers-simulation)")
    parser.add_argument("--private", action="store_true", help="Make repository private (default: public)")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: No GitHub token provided.")
        sys.exit(1)

    deploy(token, repo_name=args.repo, private=args.private)

if __name__ == "__main__":
    main()
