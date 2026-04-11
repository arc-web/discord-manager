#!/usr/bin/env python3
"""
Discord Channel Report Tool
Scans all channels, analyzes with LLM, presents draft responses for approval.

Usage: python3 discord_report.py
No manual API key setup needed - auto-discovers everything.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from discord_api import DiscordClient, BOT_IDS
from llm_analyzer import LLMAnalyzer


def format_messages(messages: list[dict]) -> str:
    """Format Discord API message objects into readable text.
    Includes ALL messages (bots too) for context. Uses full display names."""
    if not messages:
        return ""
    lines = []
    for m in messages:
        author_obj = m.get("author", {})
        # Use global_name (display name) first, fall back to username
        name = author_obj.get("global_name") or author_obj.get("username", "?")
        content = m.get("content", "")[:200]
        ts = m.get("timestamp", "")[:19]
        if content:
            lines.append(f"[{ts}] {name}: {content}")
    return "\n".join(lines)


def has_human_activity(messages: list[dict]) -> bool:
    """Check if any messages are from humans (not bots)."""
    for m in messages:
        author = m.get("author", {})
        if author.get("id") not in BOT_IDS and not author.get("bot", False):
            return True
    return False


def format_report(channel_analyses: list[dict]) -> tuple[str, list]:
    """Format LLM analysis into a numbered approval list."""
    items = []
    for analysis in channel_analyses:
        channel = analysis.get("channel", "?")
        for item in analysis.get("items", []):
            items.append({
                "channel": channel,
                "channel_id": channel,  # resolved at send time
                "from": item.get("from", "?"),
                "message": item.get("message", ""),
                "draft": item.get("draft", ""),
                "priority": item.get("priority", "medium"),
                "action": item.get("action_needed", ""),
            })

    # Sort by priority
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: order.get(x["priority"], 3))

    # Build display
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  DISCORD CHANNEL REPORT - {date_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"  {len(items)} items need your response",
        "",
    ]

    emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for idx, item in enumerate(items, 1):
        e = emoji.get(item["priority"], "⚪")
        lines.append(f"  [{idx}] {e} #{item['channel']} - {item['from']}")
        msg = item["message"][:80]
        lines.append(f"      MSG:   \"{msg}{'...' if len(item['message']) > 80 else ''}\"")
        draft = item["draft"][:80]
        lines.append(f"      DRAFT: \"{draft}{'...' if len(item['draft']) > 80 else ''}\"")
        if item["action"]:
            lines.append(f"      ACTION: {item['action']}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines), items


def parse_approval_input(user_input: str, total: int) -> Optional[list[int]]:
    """Parse approval input. Returns list of indices, [] for none, None for invalid."""
    text = user_input.strip().lower()
    if text == "none":
        return []
    if text == "all":
        return list(range(1, total + 1))
    try:
        indices = [int(x.strip()) for x in text.split(",")]
        if all(1 <= x <= total for x in indices):
            return indices
    except ValueError:
        pass
    return None


def main():
    # Support --server / -s flag
    server_name = None
    args = sys.argv[1:]
    if args and args[0] in ("-s", "--server") and len(args) > 1:
        server_name = args[1]

    print("Discord Channel Report")
    print("======================\n")

    # Init Discord client
    discord = DiscordClient(server_name=server_name)
    print(f"  Server: {discord.server_name}")
    print(f"  Bot: {discord.bot_id}")

    # Init LLM
    analyzer = LLMAnalyzer()
    if not analyzer.backend:
        print("\n  ERROR: No LLM available.")
        print("  - Start Ollama: open /Applications/Ollama.app (or brew install ollama)")
        print("  - Or set ANTHROPIC_API_KEY in env")
        sys.exit(1)
    print(f"  LLM: {analyzer.backend}" + (f" ({analyzer.ollama_model})" if analyzer.backend == "ollama" else ""))
    channel_map = discord.get_channel_map()
    print(f"\n  Scanning {len(channel_map)} channels...\n")

    # Fetch all channel messages
    all_messages = discord.fetch_all_channels(limit=20, delay=0.3)

    # Filter to channels with human activity, format for LLM
    active_channels = {}
    quiet_channels = []
    for name, messages in all_messages.items():
        if has_human_activity(messages):
            formatted = format_messages(messages)
            if formatted:
                active_channels[name] = formatted
                print(f"    {name}: {len(messages)} msgs (human activity)")
            else:
                quiet_channels.append(name)
        else:
            quiet_channels.append(name)

    if not active_channels:
        print("\n  All channels quiet. Nothing needs your attention.")
        return

    print(f"\n    {len(quiet_channels)} channels quiet, {len(active_channels)} with activity")
    print(f"\n  Analyzing with {analyzer.backend}...")

    # Batch analyze all active channels in one LLM call
    channel_analyses = analyzer.analyze(active_channels)

    if not channel_analyses:
        print("\n  No items need your response. All clear.")
        return

    # Format and display
    report, items = format_report(channel_analyses)
    print(report)

    if not items:
        print("  No items need your response. All clear.")
        return

    # Approval loop
    while True:
        try:
            user_input = input("  Send which drafts? (1,3 / all / none): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return

        approved = parse_approval_input(user_input, len(items))
        if approved is not None:
            break
        print(f"  Invalid. Enter numbers 1-{len(items)}, 'all', or 'none'.")

    if not approved:
        print("  No drafts sent.")
        return

    # Send approved drafts
    for idx in approved:
        item = items[idx - 1]
        channel_id = discord.resolve_channel(item["channel_id"])
        draft = item["draft"]
        print(f"\n  Sending to #{item['channel']}...", end=" ")
        if discord.send_message(channel_id, draft):
            print("sent")
        else:
            print("FAILED")

    print("\n  Done.")


if __name__ == "__main__":
    main()
