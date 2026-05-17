#!/usr/bin/env python3
"""Build GEOREPOSITORIO data from MAGI//ARCHIVE public metadata."""
from __future__ import annotations

import csv
import json
import os
import re
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"
MAGI_INDEX_URL = "https://tom-doerr.github.io/repo_posts/assets/search-index.json"
GITHUB_API = "https://api.github.com/repos/{owner}/{repo}"
OUT_JSON = DATA / "magi_repos.json"
OUT_CSV = DATA / "magi_repos.csv"


CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("AI agents", ["agent", "agents", "claude code", "autonomous", "multi-agent", "mcp"]),
    ("LLM / GenAI", ["llm", "gpt", "rag", "embedding", "diffusion", "whisper", "text prompts"]),
    ("Geospatial", ["geo", "gis", "map", "maps", "satellite", "lidar", "drone", "terrain"]),
    ("Data / ETL", ["data", "database", "warehouse", "etl", "pipeline", "postgres", "vector"]),
    ("Research", ["research", "paper", "academic", "benchmark", "modeling", "simulation"]),
    ("Security", ["security", "forensic", "pentest", "vulnerability", "malware", "audit"]),
    ("Dashboard / UI", ["dashboard", "visualiz", "viewer", "web ui", "interface", "frontend"]),
    ("Dev tools", ["cli", "editor", "developer", "code", "git", "terminal", "server"]),
]


def fetch_json(url: str, token: str = "") -> Any:
    headers = {
        "User-Agent": "georepositorio/1.0",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    context = None
    if os.getenv("GEOREPOSITORIO_INSECURE_SSL", "").strip().lower() in {"1", "true", "yes", "si"}:
        context = ssl._create_unverified_context()
    with urlopen(req, timeout=30, context=context) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_title(value: str) -> str:
    value = re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", value or "").strip()
    return value


def extract_repo(title: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/\]\)]+)/([^/\]\)#\s]+)", title or "", re.I)
    if match:
        return match.group(1), match.group(2).replace(".git", "")
    plain = clean_title(title)
    if "/" in plain and not plain.startswith("20"):
        owner, repo = plain.split("/", 1)
        return owner.strip(), repo.strip()
    return "", ""


def classify(text: str) -> str:
    haystack = text.casefold()
    for category, terms in CATEGORY_RULES:
        if any(term in haystack for term in terms):
            return category
    return "Other"


def github_repo(owner: str, repo: str, token: str) -> dict[str, Any]:
    if not owner or not repo:
        return {}
    url = GITHUB_API.format(owner=owner, repo=repo)
    try:
        data = fetch_json(url, token=token)
        time.sleep(0.15 if token else 0.6)
        return data if isinstance(data, dict) else {}
    except (HTTPError, URLError, TimeoutError):
        return {}


def normalize_row(item: dict[str, Any], gh: dict[str, Any]) -> dict[str, Any]:
    title_raw = str(item.get("title", ""))
    owner, repo = extract_repo(title_raw)
    repo_full = f"{owner}/{repo}" if owner and repo else clean_title(title_raw)
    description = str(item.get("s") or gh.get("description") or "").strip()
    text = " ".join([
        repo_full,
        description,
        " ".join(gh.get("topics") or []),
        str(gh.get("language") or ""),
    ])
    html_url = gh.get("html_url") or (f"https://github.com/{repo_full}" if "/" in repo_full else "")
    avatar = ""
    owner_info = gh.get("owner") if isinstance(gh.get("owner"), dict) else {}
    if owner_info:
        avatar = owner_info.get("avatar_url") or ""
    return {
        "repo": repo_full,
        "owner": owner,
        "name": repo,
        "description": description,
        "category": classify(text),
        "language": gh.get("language") or "",
        "stars": int(gh.get("stargazers_count") or 0),
        "forks": int(gh.get("forks_count") or 0),
        "open_issues": int(gh.get("open_issues_count") or 0),
        "license": ((gh.get("license") or {}).get("spdx_id") if isinstance(gh.get("license"), dict) else "") or "",
        "topics": gh.get("topics") or [],
        "created_at": gh.get("created_at") or "",
        "updated_at": gh.get("updated_at") or "",
        "pushed_at": gh.get("pushed_at") or "",
        "magi_date": item.get("d") or "",
        "magi_url": "https://tom-doerr.github.io/repo_posts" + str(item.get("u") or ""),
        "github_url": html_url,
        "avatar_url": avatar,
        "score": int(gh.get("stargazers_count") or 0) + int(gh.get("forks_count") or 0) * 3,
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "repo", "description", "category", "language", "stars", "forks",
        "open_issues", "license", "topics", "created_at", "updated_at",
        "pushed_at", "magi_date", "magi_url", "github_url", "score",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["topics"] = "; ".join(out.get("topics") or [])
            writer.writerow({field: out.get(field, "") for field in fields})


def main() -> None:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    limit = int(os.getenv("MAGI_LIMIT", "250"))
    raw = fetch_json(MAGI_INDEX_URL)
    if not isinstance(raw, list):
        raise SystemExit("MAGI index did not return a list")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw[-limit:][::-1]:
        owner, repo = extract_repo(str(item.get("title", "")))
        key = f"{owner}/{repo}".casefold() if owner and repo else str(item.get("u", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        gh = github_repo(owner, repo, token)
        rows.append(normalize_row(item, gh))
    rows.sort(key=lambda r: (r["magi_date"], r["score"]), reverse=True)
    DATA.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": MAGI_INDEX_URL,
        "count": len(rows),
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(rows)
    print(f"Wrote {OUT_JSON} with {len(rows)} repositories")


if __name__ == "__main__":
    main()
