"""Nudges - find and ping silent members."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig

DEFAULT_NUDGE = (
    "Hey! Just checking in - your pod is building something cool right now. "
    "Head over to your pod channel and let the team know how you're doing!"
)


def find_silent_members(
    client: DiscordClient,
    event: EventConfig,
    skip_ids: set[str] | None = None,
) -> list[dict]:
    """Find members who haven't posted in any pod channel."""
    pod_names = event.pods.get("names", [])
    skip_ids = skip_ids or set()

    # Collect all user IDs who have posted in pod channels
    active_ids = set()
    for pod_name in pod_names:
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)
        messages = client.get_messages(channel_id, limit=100)
        for msg in messages:
            author = msg.get("author", {})
            if not author.get("bot"):
                active_ids.add(author.get("id", ""))

    # Get all server members, find who hasn't posted
    members = client.get_members()
    silent = []
    for m in members:
        user = m["user"]
        if user.get("bot"):
            continue
        uid = user["id"]
        if uid in active_ids or uid in skip_ids:
            continue
        silent.append({
            "id": uid,
            "name": m.get("nick") or user.get("global_name") or user["username"],
            "username": user["username"],
        })

    return silent


def nudge_silent(
    client: DiscordClient,
    event: EventConfig,
    message: str | None = None,
) -> list[dict]:
    """DM silent members asking them to post in their pod channel."""
    silent = find_silent_members(client, event)
    msg = message or DEFAULT_NUDGE
    results = []

    for member in silent:
        success = client.send_dm(member["id"], msg)
        status = "sent" if success else "FAILED"
        print(f"  DM to {member['name']}: {status}")
        results.append({**member, "sent": success})

    return results


def ping_non_responders(
    client: DiscordClient,
    event: EventConfig,
    channel: str | None = None,
) -> list[dict]:
    """Post an @mention for each silent member in their pod channel (or specified channel)."""
    silent = find_silent_members(client, event)
    results = []

    if channel:
        # Post all mentions in one channel
        channel_id = client.resolve_channel(channel)
        for member in silent:
            content = f"<@{member['id']}> - We haven't heard from you yet! Let us know how you're doing."
            success = client.send_message(channel_id, content)
            results.append({**member, "sent": success})
    else:
        # Post in general
        general_id = client.resolve_channel("general")
        for member in silent:
            content = f"<@{member['id']}> - We haven't heard from you yet! Let us know how you're doing."
            success = client.send_message(general_id, content)
            results.append({**member, "sent": success})

    return results
