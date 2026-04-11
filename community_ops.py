#!/usr/bin/env python3
"""Community Operations Platform CLI.

Routes subcommands to event_ops, it_support, dev_support, and engagement modules.
"""

import argparse
import json
import sys
import yaml
from pathlib import Path

from event_config import EventConfig
from discord_api import DiscordClient
from event_ops import pod_manager, roster_tracker, announcements, schedule_runner
from it_support.setup_prompts import post_setup_prompts
from it_support.credential_distributor import distribute_all
from it_support.issue_detector import scan_channels_for_issues, classify_issues, auto_respond
from dev_support.github_ops import post_push_prompts, post_test_access_prompts, post_clone_all_prompts
from dev_support.prompt_library import post_qa_audit
from dev_support.presentation_prep import post_presentation_package, post_countdown
from engagement.shoutouts import post_shoutout_everywhere
from engagement.check_ins import post_check_in
from engagement.nudges import nudge_silent
from audit.audit import run_audit_members, run_audit_activity, run_audit_channels, run_audit_lurkers, run_audit_report

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / ".cache" / "active_event.json"


def _save_active_event(event: EventConfig) -> None:
    """Persist active event to state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "source_path": event.source_path,
        "server": event.server,
        "name": event.name,
        "config": event.to_dict(),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _load_active_event() -> dict | None:
    """Load active event from state file."""
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())


def _placeholder(name: str):
    """Return a handler that prints a not-yet-implemented message."""
    def handler(args):
        print(f"Not yet implemented: {name}")
    return handler


# -- Event commands --

def cmd_event_load(args):
    path = Path(args.yaml)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    try:
        event = EventConfig.from_file(path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    _save_active_event(event)
    print(f"Loaded event: {event.name}")
    print(event.summary())


def cmd_event_status(args):
    state = _load_active_event()
    if not state:
        print("No active event. Use: community_ops event load <yaml>")
        return
    event = EventConfig(state["config"], source_path=state.get("source_path"))
    print(event.summary())


def _require_active_event() -> tuple[EventConfig, DiscordClient]:
    """Load active event and create a Discord client. Exits on failure."""
    state = _load_active_event()
    if not state:
        print("No active event. Use: community_ops event load <yaml>", file=sys.stderr)
        sys.exit(1)
    event = EventConfig(state["config"], source_path=state.get("source_path"))
    client = DiscordClient(server_name=event.server)
    return event, client


# -- Pod commands --

def cmd_pods_assign(args):
    event, _ = _require_active_event()
    roster_path = event.roster_path
    if not roster_path:
        print("No roster path in event config.", file=sys.stderr)
        sys.exit(1)
    rp = Path(roster_path)
    if not rp.is_absolute():
        rp = SCRIPT_DIR / rp
    roster = roster_tracker.load_roster(str(rp))
    pods = pod_manager.assign_pods(roster, event.pods)
    pod_manager.save_pods(pods)
    for pod in pods:
        leader = pod.leader.get("name", "TBD") if pod.leader else "TBD"
        print(f"{pod.name}: {len(pod.members)} members, leader: {leader}")


def cmd_pods_rebalance(args):
    event, client = _require_active_event()
    current_pods = pod_manager.load_pods()
    members = client.get_members()
    attendee_names = []
    for m in members:
        u = m["user"]
        if not u.get("bot"):
            display = m.get("nick") or u.get("global_name") or u["username"]
            attendee_names.append(display)
    new_pods = pod_manager.rebalance_pods(current_pods, attendee_names, pod_count=args.count)
    pod_manager.save_pods(new_pods)
    for pod in new_pods:
        leader = pod.leader.get("name", "TBD") if pod.leader else "TBD"
        print(f"{pod.name}: {len(pod.members)} members, leader: {leader}")


def cmd_pods_announce(args):
    event, client = _require_active_event()
    pods = pod_manager.load_pods()
    template = announcements.load_template("pod_assignment")
    for pod in pods:
        channel_name = f"pod-{pod.letter}"
        channel_id = client.resolve_channel(channel_name)
        content = pod_manager.format_pod_message(pod, template)
        success = client.send_message(channel_id, content)
        status = "sent" if success else "FAILED"
        print(f"  #{channel_name}: {status}")


def cmd_pods_musical_chairs(args):
    event, client = _require_active_event()
    pods = pod_manager.load_pods()
    lines = []
    for pod in pods:
        lines.append(f"**{pod.name}:**")
        for m in pod.members:
            lines.append(f"- {m.get('name', 'Unknown')}")
        lines.append("")
    extra_vars = {"pod_assignments": "\n".join(lines)}
    announcements.announce_everywhere(client, event, "musical_chairs", extra_vars)


# -- Roster commands --

def cmd_roster_check(args):
    event, client = _require_active_event()
    roster_path = event.roster_path
    if not roster_path:
        print("No roster path in event config.", file=sys.stderr)
        sys.exit(1)
    rp = Path(roster_path)
    if not rp.is_absolute():
        rp = SCRIPT_DIR / rp
    roster = roster_tracker.load_roster(str(rp))
    result = roster_tracker.check_roster(client, roster)
    print(roster_tracker.format_roster_report(result))


def cmd_roster_nudge_missing(args):
    event, client = _require_active_event()
    roster_path = event.roster_path
    if not roster_path:
        print("No roster path in event config.", file=sys.stderr)
        sys.exit(1)
    rp = Path(roster_path)
    if not rp.is_absolute():
        rp = SCRIPT_DIR / rp
    roster = roster_tracker.load_roster(str(rp))
    result = roster_tracker.check_roster(client, roster)
    if not result["missing"]:
        print("No missing members to nudge.")
        return
    msg = f"Please confirm your identity for the {event.name} event."
    roster_tracker.nudge_missing(client, result["missing"], msg)


def cmd_roster_match(args):
    event, client = _require_active_event()
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = SCRIPT_DIR / file_path
    roster = roster_tracker.load_roster(str(file_path))
    result = roster_tracker.check_roster(client, roster)
    print(roster_tracker.format_roster_report(result))


# -- Schedule commands --

def cmd_schedule_run(args):
    event, client = _require_active_event()
    schedule_runner.run_schedule(client, event)


# -- IT commands --

def cmd_it_setup_prompts(args):
    event, client = _require_active_event()
    post_setup_prompts(client, event)
    print("Done - setup prompts posted to all pod channels.")


def cmd_it_distribute_keys(args):
    event, client = _require_active_event()
    distribute_all(client, event)
    print("Done - credentials distributed to all pod channels.")


def cmd_it_scan_issues(args):
    event, client = _require_active_event()
    pod_names = event.pods.get("names", [])
    if not pod_names:
        print("No pods configured in active event.")
        return
    print(f"Scanning {len(pod_names)} pod channels...")
    issues = scan_channels_for_issues(client, pod_names)
    if not issues:
        print("No issues detected.")
        return
    classified = classify_issues(issues)
    print(f"\nFound {len(classified)} potential issues:\n")
    for i, issue in enumerate(classified, 1):
        fix_status = f"FIX: {issue['fix']['id']}" if issue.get("fix") else "NO FIX"
        print(f"  {i}. [{issue['platform']}] #{issue['channel']} - {issue['author']}")
        print(f"     {issue['content'][:100]}")
        print(f"     -> {fix_status}")
        print()


def cmd_it_respond(args):
    event, client = _require_active_event()
    pod_names = event.pods.get("names", [])
    if not pod_names:
        print("No pods configured in active event.")
        return
    print(f"Scanning {len(pod_names)} pod channels...")
    issues = scan_channels_for_issues(client, pod_names)
    if not issues:
        print("No issues detected.")
        return
    classified = classify_issues(issues)
    fixable = [c for c in classified if c.get("fix")]
    if not fixable:
        print(f"Found {len(classified)} issues but none have known fixes.")
        return
    print(f"\nFound {len(fixable)} issues with known fixes:\n")
    for i, issue in enumerate(fixable, 1):
        print(f"  {i}. [{issue['platform']}] #{issue['channel']} - {issue['author']}")
        print(f"     Fix: {issue['fix']['id']} - {issue['fix'].get('description', '')}")
        print()
    confirm = input(f"Post {len(fixable)} fixes? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return
    responses = auto_respond(client, fixable)
    print(f"Posted {len(responses)} fixes.")


# -- Dev commands --

def cmd_dev_push_prompts(args):
    event, client = _require_active_event()
    post_push_prompts(client, event)
    print("Done - push prompts posted to all pod channels.")


def cmd_dev_test_access(args):
    event, client = _require_active_event()
    post_test_access_prompts(client, event)
    print("Done - test access prompts posted to all pod channels.")


def cmd_dev_presentation_prep(args):
    event, client = _require_active_event()
    post_presentation_package(client, event)
    print("Done - presentation package posted to all pod channels.")


def cmd_dev_clone_all(args):
    event, client = _require_active_event()
    post_clone_all_prompts(client, event)
    print("Done - clone prompts posted to general.")


def cmd_dev_audit(args):
    event, client = _require_active_event()
    post_qa_audit(client, event)
    print("Done - QA audit prompts posted to all pod channels.")


# -- Engage commands --

def cmd_engage_shoutout(args):
    event, client = _require_active_event()
    post_shoutout_everywhere(client, event, args.user, args.msg)
    print(f"Done - shoutout for {args.user} posted everywhere.")


def cmd_engage_check_in(args):
    event, client = _require_active_event()
    post_check_in(client, event)
    print("Done - check-in posted to all pod channels.")


def cmd_engage_nudge_silent(args):
    event, client = _require_active_event()
    results = nudge_silent(client, event)
    print(f"Done - nudged {len(results)} silent members.")


def cmd_engage_countdown(args):
    event, client = _require_active_event()
    post_countdown(client, event, args.minutes)
    print(f"Done - {args.minutes}-minute countdown posted everywhere.")


# -- Channel commands --

def cmd_channels_list(args):
    client = _audit_client(args)
    print(f"\n  Fetching channels...")
    raw = client.discover_channels()
    categories = client.get_categories()
    cat_ids = {v: k for k, v in categories.items()}

    # Enrich with full channel objects
    rows = []
    for name, ch_id in raw.items():
        ch = client.get_channel(ch_id)
        ch_type = {0: "text", 2: "voice", 4: "category", 5: "news"}.get(ch.get("type", 0), "?")
        if ch_type == "category":
            continue
        cat_name = cat_ids.get(ch.get("parent_id", ""), "-")
        topic = (ch.get("topic") or "")[:50]
        rows.append((cat_name, name, ch_type, topic))

    rows.sort(key=lambda r: (r[0], r[1]))
    print(f"\n  {'CATEGORY':<22} {'CHANNEL':<28} {'TYPE':<8} TOPIC")
    print(f"  {'-'*22} {'-'*28} {'-'*8} {'-'*40}")
    for cat_name, name, ch_type, topic in rows:
        print(f"  {cat_name:<22} {name:<28} {ch_type:<8} {topic}")
    print()


def cmd_channels_rename(args):
    client = _audit_client(args)
    ch_id = client.resolve_channel(args.old_name)
    result = client.edit_channel(ch_id, name=args.new_name)
    if result.get("id"):
        print(f"  Renamed #{args.old_name} -> #{args.new_name}")
        client._channels_cache = None  # bust cache
    else:
        print(f"  FAILED to rename #{args.old_name}")


def cmd_channels_topic(args):
    client = _audit_client(args)
    ch_id = client.resolve_channel(args.channel)
    result = client.edit_channel(ch_id, topic=args.topic)
    if result.get("id"):
        print(f"  Topic set on #{args.channel}: {args.topic}")
    else:
        print(f"  FAILED to set topic on #{args.channel}")


def cmd_channels_move(args):
    client = _audit_client(args)
    categories = client.get_categories()
    cat_id = categories.get(args.category)
    if not cat_id:
        print(f"  Category '{args.category}' not found. Available: {', '.join(categories.keys())}")
        return
    ch_id = client.resolve_channel(args.channel)
    result = client.edit_channel(ch_id, parent_id=cat_id)
    if result.get("id"):
        print(f"  Moved #{args.channel} to {args.category}")
    else:
        print(f"  FAILED to move #{args.channel}")


def cmd_channels_delete(args):
    client = _audit_client(args)
    ch_id = client.resolve_channel(args.channel)
    try:
        confirm = input(f"  Permanently delete #{args.channel}? This cannot be undone. [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted.")
        return
    if confirm != "y":
        print("  Aborted.")
        return
    ok = client.delete_channel(ch_id)
    print(f"  {'Deleted' if ok else 'FAILED'}: #{args.channel}")
    if ok:
        client._channels_cache = None


def cmd_channels_scaffold(args):
    client = _audit_client(args)
    path = Path(args.yaml)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    if not path.exists():
        print(f"  File not found: {path}", file=sys.stderr)
        sys.exit(1)
    structure = yaml.safe_load(path.read_text())
    print(f"  Scaffolding channels from {path.name}...")
    results = client.scaffold_channels(structure)
    for name, status in results.items():
        print(f"  {status:>8}: #{name}")
    created = sum(1 for s in results.values() if s == "created")
    updated = sum(1 for s in results.values() if s == "updated")
    print(f"\n  Done - {created} created, {updated} updated\n")


def cmd_channels_permissions(args):
    client = _audit_client(args)
    ch_id = client.resolve_channel(args.channel)
    ch = client.get_channel(ch_id)
    overwrites = ch.get("permission_overwrites", [])
    guild = client.get_guild_info()
    role_map = {r["id"]: r["name"] for r in guild.get("roles", [])}

    if not overwrites:
        print(f"  #{args.channel} has no permission overrides (uses server defaults)")
        return

    print(f"\n  #{args.channel} - Permission Overrides\n")
    print(f"  {'TYPE':<8} {'NAME':<24} {'ALLOW':<20} DENY")
    print(f"  {'-'*8} {'-'*24} {'-'*20} {'-'*20}")
    for ow in overwrites:
        ptype = "role" if ow.get("type") == 0 else "member"
        name = role_map.get(ow["id"], ow["id"])
        print(f"  {ptype:<8} {name:<24} {ow.get('allow','0'):<20} {ow.get('deny','0')}")
    print()


# -- Audit commands --

def _audit_client(args) -> DiscordClient:
    """Get a Discord client for audit commands. Uses --server if provided, else active event server, else default."""
    server = getattr(args, "server", None)
    if not server:
        state = _load_active_event()
        server = state.get("server") if state else None
    return DiscordClient(server_name=server)


def cmd_audit_members(args):
    client = _audit_client(args)
    run_audit_members(client, limit=args.limit)


def cmd_audit_activity(args):
    client = _audit_client(args)
    run_audit_activity(client, limit=args.limit)


def cmd_audit_channels(args):
    client = _audit_client(args)
    run_audit_channels(client, limit=args.limit)


def cmd_audit_lurkers(args):
    client = _audit_client(args)
    run_audit_lurkers(client, limit=args.limit)


def cmd_audit_report(args):
    client = _audit_client(args)
    path = run_audit_report(client, limit=args.limit)
    print(f"\n  Report saved: {path}")
    import subprocess
    subprocess.Popen(["open", path])
    print("  Opening in browser...")


# -- Build parser --

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="community_ops",
        description="Community Operations Platform for Discord events",
    )
    sub = parser.add_subparsers(dest="command")

    # event
    event_parser = sub.add_parser("event", help="Event configuration")
    event_sub = event_parser.add_subparsers(dest="event_action")
    load_p = event_sub.add_parser("load", help="Load event config from YAML")
    load_p.add_argument("yaml", help="Path to event YAML file")
    load_p.set_defaults(func=cmd_event_load)
    status_p = event_sub.add_parser("status", help="Show active event info")
    status_p.set_defaults(func=cmd_event_status)

    # pods
    pods_parser = sub.add_parser("pods", help="Pod management")
    pods_sub = pods_parser.add_subparsers(dest="pods_action")
    pods_sub.add_parser("assign", help="Assign roster to pods").set_defaults(func=cmd_pods_assign)
    rb = pods_sub.add_parser("rebalance", help="Rebalance pods with present members")
    rb.add_argument("--count", "-n", type=int, help="Target pod count")
    rb.set_defaults(func=cmd_pods_rebalance)
    pods_sub.add_parser("announce", help="Post pod assignments to channels").set_defaults(func=cmd_pods_announce)
    pods_sub.add_parser("musical-chairs", help="Announce pod shuffle everywhere").set_defaults(func=cmd_pods_musical_chairs)

    # roster
    roster_parser = sub.add_parser("roster", help="Roster management")
    roster_sub = roster_parser.add_subparsers(dest="roster_action")
    roster_sub.add_parser("check", help="Check roster against Discord members").set_defaults(func=cmd_roster_check)
    roster_sub.add_parser("nudge-missing", help="DM members not matched on roster").set_defaults(func=cmd_roster_nudge_missing)
    match_p = roster_sub.add_parser("match", help="Match a names file against Discord")
    match_p.add_argument("file", help="Names file to match")
    match_p.set_defaults(func=cmd_roster_match)

    # it
    it_parser = sub.add_parser("it", help="IT support")
    it_sub = it_parser.add_subparsers(dest="it_action")
    it_sub.add_parser("setup-prompts", help="Post setup instructions to pod channels").set_defaults(func=cmd_it_setup_prompts)
    it_sub.add_parser("distribute-keys", help="Distribute API keys and GitHub PATs").set_defaults(func=cmd_it_distribute_keys)
    it_sub.add_parser("scan-issues", help="Scan pod channels for error messages").set_defaults(func=cmd_it_scan_issues)
    it_sub.add_parser("respond", help="Post known fixes for detected issues").set_defaults(func=cmd_it_respond)

    # dev
    dev_parser = sub.add_parser("dev", help="Developer support")
    dev_sub = dev_parser.add_subparsers(dest="dev_action")
    dev_sub.add_parser("push-prompts").set_defaults(func=cmd_dev_push_prompts)
    dev_sub.add_parser("test-access").set_defaults(func=cmd_dev_test_access)
    dev_sub.add_parser("presentation-prep").set_defaults(func=cmd_dev_presentation_prep)
    dev_sub.add_parser("clone-all").set_defaults(func=cmd_dev_clone_all)
    dev_sub.add_parser("audit").set_defaults(func=cmd_dev_audit)

    # engage
    engage_parser = sub.add_parser("engage", help="Engagement tools")
    engage_sub = engage_parser.add_subparsers(dest="engage_action")
    shout_p = engage_sub.add_parser("shoutout")
    shout_p.add_argument("user", help="User to shout out")
    shout_p.add_argument("msg", help="Shoutout message")
    shout_p.set_defaults(func=cmd_engage_shoutout)
    engage_sub.add_parser("check-in").set_defaults(func=cmd_engage_check_in)
    engage_sub.add_parser("nudge-silent").set_defaults(func=cmd_engage_nudge_silent)
    cd_p = engage_sub.add_parser("countdown")
    cd_p.add_argument("minutes", type=int, help="Countdown minutes")
    cd_p.set_defaults(func=cmd_engage_countdown)

    # channels
    ch_parser = sub.add_parser("channels", help="Channel management")
    ch_sub = ch_parser.add_subparsers(dest="channels_action")

    ch_list = ch_sub.add_parser("list", help="List all channels with categories and topics")
    ch_list.add_argument("--server", "-s")
    ch_list.set_defaults(func=cmd_channels_list)

    ch_rename = ch_sub.add_parser("rename", help="Rename a channel")
    ch_rename.add_argument("old_name", help="Current channel name")
    ch_rename.add_argument("new_name", help="New channel name")
    ch_rename.add_argument("--server", "-s")
    ch_rename.set_defaults(func=cmd_channels_rename)

    ch_topic = ch_sub.add_parser("topic", help="Set channel topic")
    ch_topic.add_argument("channel", help="Channel name")
    ch_topic.add_argument("topic", help="Topic text")
    ch_topic.add_argument("--server", "-s")
    ch_topic.set_defaults(func=cmd_channels_topic)

    ch_move = ch_sub.add_parser("move", help="Move channel to a category")
    ch_move.add_argument("channel", help="Channel name")
    ch_move.add_argument("category", help="Category name")
    ch_move.add_argument("--server", "-s")
    ch_move.set_defaults(func=cmd_channels_move)

    ch_del = ch_sub.add_parser("delete", help="Delete a channel (with confirmation)")
    ch_del.add_argument("channel", help="Channel name")
    ch_del.add_argument("--server", "-s")
    ch_del.set_defaults(func=cmd_channels_delete)

    ch_scaffold = ch_sub.add_parser("scaffold", help="Create/update channel structure from YAML")
    ch_scaffold.add_argument("yaml", help="Path to scaffold YAML file")
    ch_scaffold.add_argument("--server", "-s")
    ch_scaffold.set_defaults(func=cmd_channels_scaffold)

    ch_perms = ch_sub.add_parser("permissions", help="Show permission overrides for a channel")
    ch_perms.add_argument("channel", help="Channel name")
    ch_perms.add_argument("--server", "-s")
    ch_perms.set_defaults(func=cmd_channels_permissions)

    # audit
    audit_parser = sub.add_parser("audit", help="Server audit tools")
    audit_sub = audit_parser.add_subparsers(dest="audit_action")
    for cmd_name, handler, help_text in [
        ("members",  cmd_audit_members,  "Full member roster with roles and join dates"),
        ("activity", cmd_audit_activity, "Per-member message count and last active date"),
        ("channels", cmd_audit_channels, "Channel health - message volume and dead/alive status"),
        ("lurkers",  cmd_audit_lurkers,  "Members who have never posted"),
        ("report",   cmd_audit_report,   "Generate full HTML report and open in browser"),
    ]:
        p = audit_sub.add_parser(cmd_name, help=help_text)
        p.add_argument("--server", "-s", help="Target server (e.g. stackpack, arc, conference)")
        p.add_argument("--limit", "-l", type=int, default=100, help="Messages per channel to scan (default: 100)")
        p.set_defaults(func=handler)

    # schedule
    sched_parser = sub.add_parser("schedule", help="Schedule runner")
    sched_sub = sched_parser.add_subparsers(dest="schedule_action")
    sched_sub.add_parser("run", help="Run the event schedule").set_defaults(func=cmd_schedule_run)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        # Subcommand group entered without action
        # Find the right sub-parser to print help for
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                if args.command in action.choices:
                    action.choices[args.command].print_help()
                    break
        sys.exit(0)


if __name__ == "__main__":
    main()
