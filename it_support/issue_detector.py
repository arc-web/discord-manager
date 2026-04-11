"""Scans Discord channels for error messages and matches them to known fixes."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from it_support.fix_library import match_fix, render_fix

# Keywords that suggest a message contains an error
ERROR_KEYWORDS = [
    "error", "not recognized", "failed", "denied", "cannot",
    "not found", "permission", "traceback", "exception",
    "fatal", "refused", "unable", "no such file",
    "is not a cmdlet", "is disabled", "not installed",
]

ERROR_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in ERROR_KEYWORDS),
    re.IGNORECASE,
)


def detect_platform(text: str) -> str:
    """Guess platform from error text content."""
    if re.search(r'PS C:\\|PowerShell|powershell|\$env:', text):
        return "windows"
    if re.search(r'zsh|bash|/Users/|%\s', text):
        return "mac"
    return "unknown"


def scan_channels_for_issues(
    client: DiscordClient,
    channels: list[str],
    limit: int = 20,
) -> list[dict]:
    """Fetch recent messages from channels and identify error messages.

    Returns list of issue dicts with channel, author, content, etc.
    """
    issues = []
    for channel_name in channels:
        channel_id = client.resolve_channel(channel_name)
        messages = client.get_messages(channel_id, limit=limit)
        for msg in messages:
            content = msg.get("content", "")
            if not content:
                continue
            if ERROR_PATTERN.search(content):
                author = msg.get("author", {})
                issues.append({
                    "channel": channel_name,
                    "channel_id": channel_id,
                    "author": author.get("username", "unknown"),
                    "author_id": author.get("id", ""),
                    "content": content,
                    "message_id": msg.get("id", ""),
                    "timestamp": msg.get("timestamp", ""),
                })
    return issues


def classify_issues(issues: list[dict]) -> list[dict]:
    """Enrich detected issues with fix matches and platform guesses."""
    classified = []
    for issue in issues:
        platform = detect_platform(issue["content"])
        fix = match_fix(issue["content"], platform=platform if platform != "unknown" else "all")
        classified.append({
            **issue,
            "platform": platform,
            "fix": fix,
        })
    return classified


def auto_respond(
    client: DiscordClient,
    classified_issues: list[dict],
    dry_run: bool = False,
) -> list[dict]:
    """Post rendered fixes as replies for issues that have a known fix.

    If dry_run is True, prints what would be posted but does not send.
    Returns list of response dicts.
    """
    responses = []
    for issue in classified_issues:
        fix = issue.get("fix")
        if not fix:
            continue
        rendered = render_fix(fix)
        mention = f"<@{issue['author_id']}>" if issue["author_id"] else issue["author"]
        message = f"{mention} {rendered}"

        if dry_run:
            print(f"[DRY RUN] #{issue['channel']} -> {issue['author']}")
            print(f"  Fix: {fix.get('id', 'unknown')}")
            print(f"  Message: {message[:120]}...")
            print()
        else:
            client.send_message(issue["channel_id"], message)

        responses.append({
            "channel": issue["channel"],
            "author": issue["author"],
            "fix_id": fix.get("id", "unknown"),
            "message": message,
            "sent": not dry_run,
        })
    return responses
