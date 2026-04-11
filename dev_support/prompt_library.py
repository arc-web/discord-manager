"""Prompt library - UI improvement, QA audit, custom prompts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig
from event_ops.announcements import load_template, render_template, announce_to_pods


def post_ui_improvement(
    client: DiscordClient,
    event: EventConfig,
    brand_ref: dict[str, str] | None = None,
) -> dict[str, bool]:
    """Post ui_improvement.md to all pods. Optionally substitute brand_ref per pod."""
    template = load_template("ui_improvement")
    pod_names = event.pods.get("names", [])
    results = {}

    for pod_name in pod_names:
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)
        extra = {}
        if brand_ref and pod_name in brand_ref:
            extra["brand_ref"] = brand_ref[pod_name]
        content = render_template(template, {
            "pod_name": pod_name,
            "pod_letter": pod_name.upper(),
            "event_name": event.name,
            **extra,
        })
        success = client.send_message(channel_id, content)
        results[channel_name] = success
        status = "sent" if success else "FAILED"
        print(f"  #{channel_name}: {status}")

    return results


def post_qa_audit(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post qa_stress_test.md to all pods."""
    return announce_to_pods(client, event, "qa_stress_test")


def post_custom_audit(
    client: DiscordClient,
    channel_name: str,
    audit_points: list[str],
) -> bool:
    """Post a custom audit prompt to a specific channel."""
    points_text = "\n".join(f"- {point}" for point in audit_points)
    content = (
        "# Custom Audit\n\n"
        "Paste this into Claude Code:\n\n"
        "```\n"
        "Review the current project and check these specific items:\n\n"
        f"{points_text}\n\n"
        "For each item, report: pass/fail, what you found, and how to fix any issues.\n"
        "```"
    )
    channel_id = client.resolve_channel(channel_name)
    success = client.send_message(channel_id, content)
    status = "sent" if success else "FAILED"
    print(f"  #{channel_name}: {status}")
    return success


def get_prompt(prompt_type: str) -> str:
    """Return raw prompt string for common types."""
    type_to_template = {
        "ui_improvement": "ui_improvement",
        "qa_stress_test": "qa_stress_test",
        "project_summary": "project_summary",
    }
    template_name = type_to_template.get(prompt_type)
    if not template_name:
        raise ValueError(f"Unknown prompt type: {prompt_type}. Available: {list(type_to_template.keys())}")
    return load_template(template_name)
