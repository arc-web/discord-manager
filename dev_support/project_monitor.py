"""Project monitoring - blocker detection, repo activity checks."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from discord_api import DiscordClient
from event_config import EventConfig

BLOCKER_PATTERNS = [
    r"\bhelp\b",
    r"\bstuck\b",
    r"\berror\b",
    r"\bfail(ed|ing|s)?\b",
    r"\bbroken\b",
    r"\bcrash(ed|ing|es)?\b",
    r"\bcan'?t\b",
    r"\bdoesn'?t work\b",
    r"\bhow do i\b",
    r"\?$",
]


def scan_for_blockers(
    client: DiscordClient,
    event: EventConfig,
) -> list[dict]:
    """Scan pod channels for help requests, errors, questions."""
    pod_names = event.pods.get("names", [])
    blockers = []

    for pod_name in pod_names:
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)
        messages = client.get_messages(channel_id, limit=50)

        for msg in messages:
            author = msg.get("author", {})
            if author.get("bot"):
                continue
            content = msg.get("content", "")
            if any(re.search(p, content, re.IGNORECASE) for p in BLOCKER_PATTERNS):
                blockers.append({
                    "channel": channel_name,
                    "author": author.get("global_name") or author.get("username", "unknown"),
                    "content": content,
                    "timestamp": msg.get("timestamp", ""),
                })

    return blockers


def format_blocker_report(blockers: list[dict]) -> str:
    """Format blockers into a readable report grouped by pod."""
    if not blockers:
        return "No blockers detected."

    by_channel: dict[str, list[dict]] = {}
    for b in blockers:
        by_channel.setdefault(b["channel"], []).append(b)

    lines = [f"Blocker Report - {len(blockers)} potential issues\n"]
    for channel, items in sorted(by_channel.items()):
        lines.append(f"## #{channel} ({len(items)} items)")
        for item in items:
            preview = item["content"][:120].replace("\n", " ")
            lines.append(f"  - {item['author']}: {preview}")
        lines.append("")

    return "\n".join(lines)


def check_repo_activity(event: EventConfig) -> dict[str, dict]:
    """Check GitHub API for latest commit info per pod repo."""
    repos = event.credentials.get("github_repos", {})
    pats = event.credentials.get("github_pats", {})
    results = {}

    for pod_name, repo in repos.items():
        pat = pats.get(pod_name, "")
        if not repo:
            continue
        headers = {"Authorization": f"token {pat}"} if pat else {}
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/commits",
                headers=headers,
                params={"per_page": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                commits = resp.json()
                if commits:
                    latest = commits[0]
                    results[pod_name] = {
                        "last_commit": latest["commit"]["author"]["date"],
                        "message": latest["commit"]["message"][:80],
                        "sha": latest["sha"][:7],
                    }
                else:
                    results[pod_name] = {"last_commit": None, "message": "no commits"}
            else:
                results[pod_name] = {"last_commit": None, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            results[pod_name] = {"last_commit": None, "message": str(e)}

    return results
