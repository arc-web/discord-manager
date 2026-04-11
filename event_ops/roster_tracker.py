"""Roster loading, checking, and nudge-missing for event attendees."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient


def load_roster(path: str) -> list[dict]:
    """Load roster from CSV or text file.

    CSV expected columns: name, pod, experience_level, os, email
    Text file: one name per line.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Roster file not found: {path}")

    text = p.read_text().strip()
    if not text:
        return []

    # Detect CSV by checking for commas in first line or .csv extension
    lines = text.split("\n")
    is_csv = p.suffix.lower() == ".csv" or "," in lines[0]

    if is_csv:
        roster = []
        reader = csv.DictReader(lines)
        for row in reader:
            # Normalize keys to lowercase
            entry = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            if entry.get("name"):
                roster.append(entry)
        return roster
    else:
        # Plain text - one name per line
        return [{"name": line.strip()} for line in lines if line.strip()]


def check_roster(client: DiscordClient, roster: list[dict]) -> dict:
    """Match roster against Discord members.

    Returns {matched: [...], missing: [...], extra: [...]}
    where extra = Discord members not on the roster.
    """
    names = [entry.get("name", "") for entry in roster if entry.get("name")]
    result = client.roster_match(names)

    # Get all non-bot Discord members to find extras
    members = client.get_members()
    matched_ids = {m["id"] for m in result["matched"]}
    roster_names_lower = {n.lower() for n in names}

    extra = []
    for m in members:
        u = m["user"]
        if u.get("bot"):
            continue
        if u["id"] in matched_ids:
            continue
        display = m.get("nick") or u.get("global_name") or u["username"]
        if display.lower() not in roster_names_lower:
            extra.append({
                "id": u["id"],
                "username": u["username"],
                "display_name": display,
            })

    return {
        "matched": result["matched"],
        "missing": result["unmatched"],
        "suggestions": result.get("suggestions", {}),
        "extra": extra,
    }


def format_roster_report(result: dict) -> str:
    """Human-readable report of roster check results."""
    lines = []

    matched = result["matched"]
    missing = result["missing"]
    extra = result["extra"]
    suggestions = result.get("suggestions", {})

    lines.append(f"Roster Check: {len(matched)} matched, {len(missing)} missing, {len(extra)} extra")
    lines.append("")

    if matched:
        lines.append("MATCHED:")
        for m in matched:
            fuzzy = " (fuzzy)" if m.get("fuzzy") else ""
            lines.append(f"  {m['roster_name']} -> {m['display_name']}{fuzzy}")

    if missing:
        lines.append("")
        lines.append("MISSING (not found in Discord):")
        for name in missing:
            hint = ""
            if name in suggestions:
                hint = f" - did you mean: {', '.join(suggestions[name])}?"
            lines.append(f"  {name}{hint}")

    if extra:
        lines.append("")
        lines.append("EXTRA (in Discord but not on roster):")
        for m in extra:
            lines.append(f"  {m['display_name']} (@{m['username']})")

    return "\n".join(lines)


def nudge_missing(client: DiscordClient, missing_names: list[str], message: str) -> None:
    """DM members who might match missing roster names, asking them to confirm identity.

    For each missing name, searches Discord for close matches. If found with
    reasonable confidence, sends them a DM. Otherwise logs that they're not found.
    """
    for name in missing_names:
        results = client.search_members(name, limit=1)
        if results:
            member = results[0]
            user = member["user"]
            display = member.get("nick") or user.get("global_name") or user["username"]
            dm_text = (
                f"Hi {display}! We have '{name}' on our roster but couldn't "
                f"auto-match you. Are you '{name}'?\n\n{message}"
            )
            success = client.send_dm(user["id"], dm_text)
            status = "sent DM" if success else "DM failed"
            print(f"  {name} -> {display}: {status}")
        else:
            print(f"  {name}: no Discord match found")
