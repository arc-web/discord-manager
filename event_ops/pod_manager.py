"""Pod assignment and rebalancing for event participants."""

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

AGENT_DIR = Path(__file__).parent.parent
DEFAULT_POD_STATE = AGENT_DIR / ".cache" / "active_pods.json"

EXPERIENCE_ORDER = {"subscription": 0, "experienced": 1, "learning": 2}


@dataclass
class PodAssignment:
    name: str
    letter: str
    leader: Optional[dict] = None
    members: list[dict] = field(default_factory=list)


def _experience_rank(member: dict) -> int:
    """Lower = more experienced."""
    return EXPERIENCE_ORDER.get(member.get("experience_level", "learning"), 2)


def _pick_leader(members: list[dict]) -> dict:
    """Pick pod leader: prefer subscription-level Mac user, then subscription, then first."""
    # subscription + mac
    for m in members:
        if m.get("experience_level") == "subscription" and m.get("os", "").lower() == "mac":
            return m
    # subscription
    for m in members:
        if m.get("experience_level") == "subscription":
            return m
    # first member
    return members[0] if members else {}


def assign_pods(roster: list[dict], pod_config: dict) -> list[PodAssignment]:
    """Distribute roster members across pods, balanced by experience level.

    Algorithm:
    1. Sort members by experience (most experienced first)
    2. Round-robin distribute, alternating top and bottom to balance each pod
    3. Pick a leader for each pod
    """
    pod_names = pod_config.get("names", ["a", "b", "c", "d"])
    pod_count = pod_config.get("count", len(pod_names))

    # Sort by experience (most experienced first)
    sorted_members = sorted(roster, key=_experience_rank)

    # Snake-draft distribution: round-robin forward then backward
    # This ensures each pod gets a mix of experience levels
    pods = [[] for _ in range(pod_count)]
    forward = True
    idx = 0
    for member in sorted_members:
        pods[idx].append(member)
        if forward:
            if idx == pod_count - 1:
                forward = False  # reverse direction next
            else:
                idx += 1
        else:
            if idx == 0:
                forward = True  # reverse direction next
            else:
                idx -= 1

    # Build PodAssignment objects
    assignments = []
    for i, members in enumerate(pods):
        letter = pod_names[i] if i < len(pod_names) else chr(ord("a") + i)
        leader = _pick_leader(members)
        assignments.append(PodAssignment(
            name=f"Pod {letter.upper()}",
            letter=letter,
            leader=leader,
            members=members,
        ))

    return assignments


def rebalance_pods(
    current_pods: list[PodAssignment],
    actual_attendees: list[str],
    pod_count: int = None,
) -> list[PodAssignment]:
    """Rebalance pods using only members who are actually present.

    Filters current pod members to only those in actual_attendees,
    then redistributes using the same balancing algorithm.
    """
    # Collect all members who are present
    attendee_set = {name.lower().strip() for name in actual_attendees}
    present_members = []
    for pod in current_pods:
        for member in pod.members:
            member_name = member.get("name", "").lower().strip()
            if member_name in attendee_set:
                present_members.append(member)

    # Determine pod count
    target_count = pod_count or len(current_pods)
    pod_names = [chr(ord("a") + i) for i in range(target_count)]

    pod_config = {"names": pod_names, "count": target_count}
    return assign_pods(present_members, pod_config)


def format_pod_message(pod: PodAssignment, template: str) -> str:
    """Render a pod assignment into a Discord message using a template."""
    emojis = {"a": "🅰️", "b": "🅱️", "c": "©️", "d": "🇩"}
    emoji = emojis.get(pod.letter.lower(), "📌")

    member_lines = []
    for m in pod.members:
        name = m.get("name", "Unknown")
        level = m.get("experience_level", "")
        is_leader = (pod.leader and m.get("name") == pod.leader.get("name"))
        if is_leader:
            continue  # Leader shown separately
        suffix = f" ({level})" if level else ""
        member_lines.append(f"- {name}{suffix}")

    leader_name = pod.leader.get("name", "TBD") if pod.leader else "TBD"

    variables = {
        "pod_emoji": emoji,
        "pod_letter": pod.letter.upper(),
        "leader_name": leader_name,
        "member_list": "\n".join(member_lines),
        "member_count": str(len(pod.members)),
    }

    result = template
    for key, val in variables.items():
        result = result.replace(f"{{{{{key}}}}}", val)
    return result


def save_pods(pods: list[PodAssignment], path: str = None) -> None:
    """Save pod assignments to JSON."""
    save_path = Path(path) if path else DEFAULT_POD_STATE
    save_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(pod) for pod in pods]
    save_path.write_text(json.dumps(data, indent=2))
    print(f"Saved {len(pods)} pods to {save_path}")


def load_pods(path: str = None) -> list[PodAssignment]:
    """Load pod assignments from JSON."""
    load_path = Path(path) if path else DEFAULT_POD_STATE
    if not load_path.exists():
        raise FileNotFoundError(f"No pod state found at {load_path}")
    data = json.loads(load_path.read_text())
    pods = []
    for d in data:
        pods.append(PodAssignment(
            name=d["name"],
            letter=d["letter"],
            leader=d.get("leader"),
            members=d.get("members", []),
        ))
    return pods
