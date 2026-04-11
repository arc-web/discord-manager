"""Check-ins - emoji status polls and response scanning."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig
from event_ops.announcements import announce_to_pods

# Emoji-to-status mapping matching check_in_emoji.md template
STATUS_MAP = {
    "working": ["green", "check", "rocket", "hammer", "wrench"],
    "waiting": ["yellow", "hourglass", "clock", "pause"],
    "stuck": ["red", "x", "stop", "sos", "warning"],
    "rate_limited": ["snail", "turtle", "slow"],
}


def post_check_in(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post check_in_emoji.md to all pod channels."""
    return announce_to_pods(client, event, "check_in_emoji")


def scan_check_in_responses(
    client: DiscordClient,
    event: EventConfig,
) -> dict[str, dict[str, list[str]]]:
    """Scan pod channels for emoji status responses after a check-in."""
    pod_names = event.pods.get("names", [])
    results = {}

    for pod_name in pod_names:
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)
        messages = client.get_messages(channel_id, limit=30)

        pod_status: dict[str, list[str]] = {
            "working": [], "waiting": [], "stuck": [], "rate_limited": [],
        }

        for msg in messages:
            author = msg.get("author", {})
            if author.get("bot"):
                continue
            content = msg.get("content", "").lower()
            display = author.get("global_name") or author.get("username", "unknown")

            for status, keywords in STATUS_MAP.items():
                if any(kw in content for kw in keywords):
                    pod_status[status].append(display)
                    break

        results[channel_name] = pod_status

    return results
