"""Generates and posts platform-specific setup instructions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _load_template(name: str) -> str:
    """Load a template file by name."""
    path = TEMPLATES_DIR / name
    return path.read_text()


def generate_setup_prompt(platform: str, api_key: str, pod_letter: str) -> str:
    """Load the appropriate setup template and substitute variables."""
    if platform == "windows":
        template = _load_template("setup_windows.md")
    else:
        template = _load_template("setup_mac.md")

    return (
        template
        .replace("{{api_key}}", api_key)
        .replace("{{pod_letter}}", pod_letter)
    )


def post_setup_prompts(client: DiscordClient, event: EventConfig) -> None:
    """Post Mac and Windows setup instructions to each pod channel.

    Uses the pod's specific API key from event credentials.
    """
    api_keys = event.credentials.get("api_keys", {})
    pod_names = event.pods.get("names", [])

    for pod in pod_names:
        # Find the API key - try exact match, then pod_{name}
        key = api_keys.get(pod) or api_keys.get(f"pod_{pod}", "API_KEY_NOT_SET")

        # Resolve the pod channel
        channel_id = client.resolve_channel(pod)

        # Post Mac setup
        mac_prompt = generate_setup_prompt("mac", key, pod)
        client.send_message(channel_id, mac_prompt)

        # Post Windows setup
        win_prompt = generate_setup_prompt("windows", key, pod)
        client.send_message(channel_id, win_prompt)

        print(f"Posted setup prompts to pod {pod}")
