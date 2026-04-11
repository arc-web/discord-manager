"""Fun engagement - challenges, GIFs, philosophy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig


def post_challenge(
    client: DiscordClient,
    event: EventConfig,
    challenge_text: str,
) -> dict[str, bool]:
    """Post a fun challenge to general + all pod channels."""
    content = f"# Challenge Time!\n\n{challenge_text}\n\nWho's in?"
    pod_names = event.pods.get("names", [])
    channels = ["general"] + [f"pod-{p}" for p in pod_names]
    results = {}

    for ch in channels:
        channel_id = client.resolve_channel(ch)
        success = client.send_message(channel_id, content)
        results[ch] = success
        status = "sent" if success else "FAILED"
        print(f"  #{ch}: {status}")

    return results


def post_gif(
    client: DiscordClient,
    channel_id: str,
    gif_url: str,
    caption: str = "",
) -> bool:
    """Post a GIF with optional caption to a channel."""
    content = f"{caption}\n{gif_url}" if caption else gif_url
    success = client.send_message(channel_id, content.strip())
    return success


def post_philosophy(
    client: DiscordClient,
    event: EventConfig,
    message: str,
) -> bool:
    """Post an inspirational message about learning together to general."""
    content = f"> {message}"
    channel_id = client.resolve_channel("general")
    success = client.send_message(channel_id, content)
    status = "sent" if success else "FAILED"
    print(f"  #general: {status}")
    return success
