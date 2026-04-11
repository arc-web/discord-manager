"""Presentation prep - summaries, NotebookLM guides, countdowns."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig
from event_ops.announcements import (
    load_template, render_template, announce_to_pods, announce_everywhere,
)


def post_summary_prompt(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post project_summary.md to all pods."""
    return announce_to_pods(client, event, "project_summary")


def post_notebooklm_guide(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post notebooklm_prompts.md to all pods."""
    return announce_to_pods(client, event, "notebooklm_prompts")


def post_countdown(
    client: DiscordClient,
    event: EventConfig,
    minutes: int,
) -> dict[str, bool]:
    """Post five_minute_warning.md to all pods + general with minutes substituted."""
    return announce_everywhere(client, event, "five_minute_warning", {
        "minutes": str(minutes),
    })


def post_presentation_package(
    client: DiscordClient,
    event: EventConfig,
) -> dict[str, bool]:
    """Post summary + notebooklm guide in sequence to all pods."""
    results = {}
    print("Posting project summary prompts...")
    summary_results = post_summary_prompt(client, event)
    results.update({f"summary:{k}": v for k, v in summary_results.items()})

    print("Posting NotebookLM guide...")
    nlm_results = post_notebooklm_guide(client, event)
    results.update({f"notebooklm:{k}": v for k, v in nlm_results.items()})

    return results
