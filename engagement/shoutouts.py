"""Shoutouts - public recognition for participants."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig
from event_ops.announcements import load_template, render_template, announce_everywhere


def post_shoutout(
    client: DiscordClient,
    event: EventConfig,
    user_name: str,
    message: str,
    channel: str = "general",
) -> bool:
    """Post a shoutout to a specific channel."""
    template = load_template("shoutout")
    content = render_template(template, {
        "user_name": user_name,
        "shoutout_message": message,
        "event_name": event.name,
    })
    channel_id = client.resolve_channel(channel)
    success = client.send_message(channel_id, content)
    status = "sent" if success else "FAILED"
    print(f"  #{channel}: {status}")
    return success


def post_shoutout_everywhere(
    client: DiscordClient,
    event: EventConfig,
    user_name: str,
    message: str,
) -> dict[str, bool]:
    """Post shoutout to general + all pod channels."""
    return announce_everywhere(client, event, "shoutout", {
        "user_name": user_name,
        "shoutout_message": message,
    })
