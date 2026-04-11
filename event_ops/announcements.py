"""Template-based announcements to pod channels and general."""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def load_template(template_name: str) -> str:
    """Load a template file from the templates/ directory."""
    # Try with and without .md extension
    path = TEMPLATES_DIR / template_name
    if not path.exists():
        path = TEMPLATES_DIR / f"{template_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_name} (searched {TEMPLATES_DIR})")
    return path.read_text()


def render_template(template: str, variables: dict) -> str:
    """Replace {{var}} placeholders in template with variable values."""
    result = template
    for key, val in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(val))
    return result


def announce_to_pods(
    client: DiscordClient,
    event: EventConfig,
    template_name: str,
    extra_vars: Optional[dict] = None,
) -> dict[str, bool]:
    """Load template, render with pod-specific variables, send to each pod channel."""
    template = load_template(template_name)
    pod_names = event.pods.get("names", [])
    results = {}

    for pod_name in pod_names:
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)

        variables = {
            "pod_name": pod_name,
            "pod_letter": pod_name.upper(),
            "channel": channel_name,
            "event_name": event.name,
        }
        if extra_vars:
            variables.update(extra_vars)

        content = render_template(template, variables)
        success = client.send_message(channel_id, content)
        results[channel_name] = success
        status = "sent" if success else "FAILED"
        print(f"  #{channel_name}: {status}")

    return results


def announce_to_general(
    client: DiscordClient,
    event: EventConfig,
    template_name: str,
    extra_vars: Optional[dict] = None,
) -> bool:
    """Send rendered template to the general channel."""
    template = load_template(template_name)

    variables = {
        "event_name": event.name,
        "channel": "general",
    }
    if extra_vars:
        variables.update(extra_vars)

    content = render_template(template, variables)
    channel_id = client.resolve_channel("general")
    success = client.send_message(channel_id, content)
    status = "sent" if success else "FAILED"
    print(f"  #general: {status}")
    return success


def announce_everywhere(
    client: DiscordClient,
    event: EventConfig,
    template_name: str,
    extra_vars: Optional[dict] = None,
) -> dict[str, bool]:
    """Send to general + all pod channels."""
    results = {}
    results["general"] = announce_to_general(client, event, template_name, extra_vars)
    pod_results = announce_to_pods(client, event, template_name, extra_vars)
    results.update(pod_results)
    return results
