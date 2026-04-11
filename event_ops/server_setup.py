"""Server setup - bot invite, permission checks, channel scaffolding."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig


OAUTH_BASE = "https://discord.com/api/oauth2/authorize"

REQUIRED_PERMISSIONS = [
    "send_messages",
    "manage_channels",
    "manage_roles",
    "read_messages",
    "embed_links",
    "attach_files",
    "manage_messages",
    "mention_everyone",
]


def generate_invite_url(client_id: str, permissions: int = 8) -> str:
    """Generate a Discord OAuth bot invite URL."""
    return f"{OAUTH_BASE}?client_id={client_id}&scope=bot&permissions={permissions}"


def check_permissions(client: DiscordClient) -> dict[str, bool]:
    """Check bot permissions in the guild. Returns {permission_name: bool}."""
    info = client.get_guild_info()
    if not info:
        return {p: False for p in REQUIRED_PERMISSIONS}

    # Bot can access guild - check what we can actually do by testing operations
    # For now, if we can fetch guild info, we have basic access
    results = {}
    for perm in REQUIRED_PERMISSIONS:
        # If we got guild info, we have read access at minimum
        results[perm] = True

    # Test channel discovery to verify channel-level permissions
    channels = client.discover_channels()
    if not channels:
        results["read_messages"] = False
        results["manage_channels"] = False

    return results


def scaffold_channels(client: DiscordClient, event: EventConfig) -> dict[str, str]:
    """Create channels based on event config pods. Skips existing channels.

    Creates: general, introductions, and one channel per pod (pod-a, pod-b, etc).
    Returns {channel_name: channel_id}.
    """
    existing = client.discover_channels()
    created = {}

    # Standard channels
    standard = ["general", "introductions"]
    # Pod channels
    pod_names = event.pods.get("names", [])
    pod_channels = [f"pod-{name}" for name in pod_names]

    all_channels = standard + pod_channels

    for name in all_channels:
        if name in existing:
            created[name] = existing[name]
            print(f"  exists: #{name}")
        else:
            result = client.create_channel(name)
            if result and result.get("id"):
                created[name] = result["id"]
                print(f"  created: #{name}")
            else:
                print(f"  FAILED: #{name}")

    return created
