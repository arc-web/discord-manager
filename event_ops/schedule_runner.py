"""Schedule runner - executes timed event actions."""

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig
from event_ops import announcements, roster_tracker


def load_schedule(event: EventConfig) -> list[dict]:
    """Return schedule entries sorted by time."""
    entries = event.schedule
    return sorted(entries, key=lambda e: e.get("time", ""))


def execute_action(client: DiscordClient, event: EventConfig, action: dict) -> None:
    """Dispatch an action based on its type."""
    action_type = action.get("action", "")
    message = action.get("message", "")

    if action_type == "announce":
        # Send message to general channel
        channel_id = client.resolve_channel("general")
        client.send_message(channel_id, message)
        print(f"    Announced: {message[:60]}...")

    elif action_type == "it_scan":
        print(f"    IT scan: {message}")
        # Roster check as a basic scan
        roster_path = event.roster_path
        if roster_path:
            roster = roster_tracker.load_roster(roster_path)
            result = roster_tracker.check_roster(client, roster)
            print(roster_tracker.format_roster_report(result))

    elif action_type == "countdown":
        minutes = action.get("minutes", 5)
        channel_id = client.resolve_channel("general")
        client.send_message(channel_id, f"**{minutes} minutes remaining!** {message}")
        print(f"    Countdown: {minutes}min")

    else:
        print(f"    Unknown action type: {action_type}")


def run_schedule(client: DiscordClient, event: EventConfig) -> None:
    """Interactive loop that executes schedule actions when their time arrives.

    Checks current time against schedule entries. Prints upcoming items.
    Runs until all items are executed or user exits with Ctrl+C.
    """
    schedule = load_schedule(event)
    if not schedule:
        print("No schedule entries found.")
        return

    executed = set()
    print(f"Schedule runner started with {len(schedule)} entries.")
    print("Press Ctrl+C to exit.\n")

    # Show upcoming
    for i, entry in enumerate(schedule):
        print(f"  [{entry['time']}] {entry.get('action', '?')}: {entry.get('message', '')[:50]}")
    print()

    try:
        while len(executed) < len(schedule):
            now = datetime.now().strftime("%H:%M")
            for i, entry in enumerate(schedule):
                if i in executed:
                    continue
                entry_time = entry.get("time", "")
                if entry_time <= now:
                    print(f"[{now}] Executing: {entry.get('action', '?')}")
                    execute_action(client, event, entry)
                    executed.add(i)

            if len(executed) < len(schedule):
                time.sleep(10)

    except KeyboardInterrupt:
        print(f"\nSchedule runner stopped. {len(executed)}/{len(schedule)} actions executed.")
