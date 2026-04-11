"""
Discord Server Audit Module
Collects member profiles, activity scores, channel health, and generates HTML reports.
"""

import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(AGENT_DIR))

from discord_api import DiscordClient, BOT_IDS


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MemberProfile:
    user_id: str
    username: str
    display_name: str
    roles: list
    joined_at: str
    message_count: int = 0
    last_active: str = None
    is_bot: bool = False
    is_lurker: bool = False


@dataclass
class ChannelHealth:
    channel_name: str
    channel_id: str
    message_count: int = 0
    unique_posters: int = 0
    last_activity: str = None
    is_dead: bool = True


@dataclass
class AuditSnapshot:
    server_name: str
    generated_at: str
    total_members: int
    human_members: int
    lurker_count: int
    active_count: int
    channels_scanned: int
    dead_channels: int
    members: list = field(default_factory=list)
    channels: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core data collection
# ---------------------------------------------------------------------------

def _build_snapshot(client: DiscordClient, limit: int = 100) -> AuditSnapshot:
    """Collect all data and return an AuditSnapshot."""

    print(f"  Fetching guild info...")
    guild = client.get_guild_info()
    server_name = guild.get("name", client.server_name)

    # Build role ID -> name map
    role_map = {r["id"]: r["name"] for r in guild.get("roles", [])}

    print(f"  Fetching members...")
    raw_members = client.get_members(limit=10000)

    # Build member profiles
    members = {}
    for m in raw_members:
        user = m.get("user", {})
        uid = user.get("id", "")
        is_bot = user.get("bot", False) or uid in BOT_IDS
        nick = m.get("nick")
        display = nick or user.get("global_name") or user.get("username", "?")
        role_names = [role_map.get(rid, rid) for rid in m.get("roles", []) if rid in role_map]
        members[uid] = MemberProfile(
            user_id=uid,
            username=user.get("username", "?"),
            display_name=display,
            roles=role_names,
            joined_at=m.get("joined_at", ""),
            is_bot=is_bot,
        )

    # Scan all channels for activity
    print(f"  Scanning channels (limit={limit} messages each)...")
    channels_raw = client.discover_channels()
    channel_health = []
    activity = {}  # user_id -> {count, last_active}

    for ch_name, ch_id in channels_raw.items():
        try:
            messages = client.get_messages(ch_id, limit=limit)
            time.sleep(0.3)
        except Exception:
            continue

        posters = set()
        last_ts = None
        msg_count = 0

        for msg in messages:
            author = msg.get("author", {})
            aid = author.get("id", "")
            if author.get("bot") or aid in BOT_IDS:
                continue
            msg_count += 1
            posters.add(aid)
            ts = msg.get("timestamp", "")
            if ts and (last_ts is None or ts > last_ts):
                last_ts = ts
            # Update activity map
            if aid not in activity:
                activity[aid] = {"count": 0, "last_active": None}
            activity[aid]["count"] += 1
            if ts and (activity[aid]["last_active"] is None or ts > activity[aid]["last_active"]):
                activity[aid]["last_active"] = ts

        channel_health.append(ChannelHealth(
            channel_name=ch_name,
            channel_id=ch_id,
            message_count=msg_count,
            unique_posters=len(posters),
            last_activity=last_ts,
            is_dead=(msg_count == 0),
        ))

    # Apply activity scores back to member profiles
    for uid, stats in activity.items():
        if uid in members:
            members[uid].message_count = stats["count"]
            members[uid].last_active = stats["last_active"]

    # Mark lurkers
    for m in members.values():
        if not m.is_bot and m.message_count == 0:
            m.is_lurker = True

    member_list = sorted(members.values(), key=lambda m: m.message_count, reverse=True)
    human_list = [m for m in member_list if not m.is_bot]
    lurkers = [m for m in human_list if m.is_lurker]
    active = [m for m in human_list if not m.is_lurker]
    dead_channels = [c for c in channel_health if c.is_dead]

    return AuditSnapshot(
        server_name=server_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_members=len(member_list),
        human_members=len(human_list),
        lurker_count=len(lurkers),
        active_count=len(active),
        channels_scanned=len(channel_health),
        dead_channels=len(dead_channels),
        members=member_list,
        channels=sorted(channel_health, key=lambda c: c.message_count, reverse=True),
    )


def _days_ago(iso_ts: str) -> str:
    """Return human-readable time since an ISO timestamp."""
    if not iso_ts:
        return "never"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        d = delta.days
        if d == 0:
            return "today"
        if d == 1:
            return "1 day ago"
        return f"{d} days ago"
    except Exception:
        return iso_ts[:10]


# ---------------------------------------------------------------------------
# CLI output commands
# ---------------------------------------------------------------------------

def run_audit_members(client: DiscordClient, limit: int = 100):
    snap = _build_snapshot(client, limit)
    print(f"\n  {snap.server_name} - {snap.total_members} members ({snap.human_members} human, {snap.total_members - snap.human_members} bots)\n")
    print(f"  {'NAME':<28} {'USERNAME':<22} {'ROLES':<25} {'JOINED'}")
    print(f"  {'-'*28} {'-'*22} {'-'*25} {'-'*12}")
    for m in sorted(snap.members, key=lambda x: x.joined_at):
        roles = ", ".join(m.roles) if m.roles else "-"
        bot_tag = " [BOT]" if m.is_bot else ""
        joined = m.joined_at[:10] if m.joined_at else "?"
        print(f"  {(m.display_name + bot_tag):<28} {m.username:<22} {roles:<25} {joined}")
    print()


def run_audit_activity(client: DiscordClient, limit: int = 100):
    snap = _build_snapshot(client, limit)
    print(f"\n  {snap.server_name} - Activity (last {limit} msgs/channel)\n")
    print(f"  {'NAME':<28} {'MSGS':>6}  {'LAST ACTIVE'}")
    print(f"  {'-'*28} {'-'*6}  {'-'*20}")
    humans = [m for m in snap.members if not m.is_bot]
    for m in humans:
        last = _days_ago(m.last_active) if m.last_active else "never"
        bar = "#" * min(m.message_count, 30)
        print(f"  {m.display_name:<28} {m.message_count:>6}  {last}  {bar}")
    print()


def run_audit_channels(client: DiscordClient, limit: int = 100):
    snap = _build_snapshot(client, limit)
    print(f"\n  {snap.server_name} - Channel Health\n")
    print(f"  {'CHANNEL':<30} {'MSGS':>6}  {'POSTERS':>8}  {'LAST ACTIVE':<20} STATUS")
    print(f"  {'-'*30} {'-'*6}  {'-'*8}  {'-'*20} {'-'*6}")
    for c in snap.channels:
        last = _days_ago(c.last_activity) if c.last_activity else "never"
        status = "DEAD" if c.is_dead else "active"
        print(f"  {c.channel_name:<30} {c.message_count:>6}  {c.unique_posters:>8}  {last:<20} {status}")
    print(f"\n  {snap.dead_channels} dead / {snap.channels_scanned} total channels\n")


def run_audit_lurkers(client: DiscordClient, limit: int = 100):
    snap = _build_snapshot(client, limit)
    lurkers = [m for m in snap.members if m.is_lurker]
    print(f"\n  {snap.server_name} - Lurkers ({len(lurkers)} of {snap.human_members} humans)\n")
    if not lurkers:
        print("  No lurkers found - everyone has posted!\n")
        return
    print(f"  {'NAME':<28} {'USERNAME':<22} {'JOINED':<14} SILENT FOR")
    print(f"  {'-'*28} {'-'*22} {'-'*14} {'-'*12}")
    for m in sorted(lurkers, key=lambda x: x.joined_at):
        joined = m.joined_at[:10] if m.joined_at else "?"
        silent = _days_ago(m.joined_at)
        print(f"  {m.display_name:<28} {m.username:<22} {joined:<14} {silent}")
    print()


def run_audit_report(client: DiscordClient, limit: int = 100) -> str:
    """Generate HTML report, save to .cache/, return file path."""
    snap = _build_snapshot(client, limit)
    html = _render_html(snap, limit)

    cache_dir = AGENT_DIR / ".cache"
    cache_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = snap.server_name.lower().replace(" ", "_").replace(".", "")
    out_path = cache_dir / f"audit_{safe_name}_{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# HTML report renderer
# ---------------------------------------------------------------------------

def _render_html(snap: AuditSnapshot, limit: int) -> str:
    gen_dt = snap.generated_at[:19].replace("T", " ") + " UTC"
    active_pct = round(snap.active_count / snap.human_members * 100) if snap.human_members else 0
    lurker_pct = round(snap.lurker_count / snap.human_members * 100) if snap.human_members else 0

    # Member rows
    member_rows = []
    for m in snap.members:
        if m.is_bot:
            continue
        color = "#e8f5e9" if m.message_count >= 10 else ("#fff9c4" if m.message_count > 0 else "#ffebee")
        roles = ", ".join(m.roles) if m.roles else "-"
        joined = m.joined_at[:10] if m.joined_at else "?"
        last = _days_ago(m.last_active) if m.last_active else "never"
        member_rows.append(
            f'<tr style="background:{color}">'
            f'<td>{m.display_name}</td>'
            f'<td style="color:#666">@{m.username}</td>'
            f'<td>{roles}</td>'
            f'<td>{joined}</td>'
            f'<td style="text-align:right;font-weight:bold">{m.message_count}</td>'
            f'<td>{last}</td>'
            f'</tr>'
        )

    # Channel rows
    channel_rows = []
    for c in snap.channels:
        style = "color:#999" if c.is_dead else ""
        last = _days_ago(c.last_activity) if c.last_activity else "never"
        status_badge = '<span style="background:#ffcdd2;color:#c62828;padding:2px 8px;border-radius:12px;font-size:12px">dead</span>' if c.is_dead else '<span style="background:#c8e6c9;color:#2e7d32;padding:2px 8px;border-radius:12px;font-size:12px">active</span>'
        channel_rows.append(
            f'<tr style="{style}">'
            f'<td>#{c.channel_name}</td>'
            f'<td style="text-align:right">{c.message_count}</td>'
            f'<td style="text-align:right">{c.unique_posters}</td>'
            f'<td>{last}</td>'
            f'<td>{status_badge}</td>'
            f'</tr>'
        )

    # Lurker rows
    lurker_rows = []
    for m in sorted([m for m in snap.members if m.is_lurker], key=lambda x: x.joined_at):
        joined = m.joined_at[:10] if m.joined_at else "?"
        silent = _days_ago(m.joined_at)
        lurker_rows.append(
            f'<tr>'
            f'<td>{m.display_name}</td>'
            f'<td style="color:#666">@{m.username}</td>'
            f'<td>{joined}</td>'
            f'<td style="color:#c62828">{silent}</td>'
            f'</tr>'
        )

    lurker_section = ""
    if lurker_rows:
        lurker_section = f"""
        <h2>Lurkers <span style="font-size:16px;font-weight:normal;color:#999">({snap.lurker_count} members - never posted)</span></h2>
        <table>
          <thead><tr><th>Name</th><th>Username</th><th>Joined</th><th>Silent For</th></tr></thead>
          <tbody>{''.join(lurker_rows)}</tbody>
        </table>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{snap.server_name} - Discord Audit</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #222; }}
  .header {{ background: #5865f2; color: white; padding: 32px 40px; }}
  .header h1 {{ font-size: 28px; font-weight: 700; }}
  .header p {{ opacity: 0.8; margin-top: 4px; font-size: 14px; }}
  .stats {{ display: flex; gap: 16px; padding: 24px 40px; flex-wrap: wrap; }}
  .stat {{ background: white; border-radius: 12px; padding: 20px 28px; flex: 1; min-width: 160px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .stat .val {{ font-size: 36px; font-weight: 800; color: #5865f2; }}
  .stat .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .content {{ padding: 0 40px 40px; }}
  h2 {{ font-size: 20px; margin: 32px 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  thead tr {{ background: #f0f0f0; }}
  th {{ padding: 12px 16px; text-align: left; font-size: 13px; color: #555; font-weight: 600; cursor: pointer; user-select: none; white-space: nowrap; }}
  th:hover {{ background: #e0e0e0; }}
  td {{ padding: 10px 16px; font-size: 14px; border-top: 1px solid #f0f0f0; }}
  tr:hover td {{ background: rgba(88,101,242,.04) !important; }}
  .legend {{ font-size: 12px; color: #888; margin-top: 8px; display: flex; gap: 16px; }}
  .dot {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; margin-right: 4px; vertical-align: middle; }}
</style>
</head>
<body>

<div class="header">
  <h1>{snap.server_name}</h1>
  <p>Discord Audit Report - Generated {gen_dt} - Scanned last {limit} messages per channel</p>
</div>

<div class="stats">
  <div class="stat"><div class="val">{snap.total_members}</div><div class="label">Total Members</div></div>
  <div class="stat"><div class="val">{snap.human_members}</div><div class="label">Human Members</div></div>
  <div class="stat"><div class="val" style="color:#2e7d32">{snap.active_count}</div><div class="label">Active ({active_pct}%)</div></div>
  <div class="stat"><div class="val" style="color:#c62828">{snap.lurker_count}</div><div class="label">Lurkers ({lurker_pct}%)</div></div>
  <div class="stat"><div class="val">{snap.channels_scanned}</div><div class="label">Channels Scanned</div></div>
  <div class="stat"><div class="val" style="color:#e65100">{snap.dead_channels}</div><div class="label">Dead Channels</div></div>
</div>

<div class="content">

  <h2>Members <span style="font-size:16px;font-weight:normal;color:#999">({snap.human_members} humans)</span></h2>
  <div class="legend">
    <span><span class="dot" style="background:#e8f5e9"></span>Active (10+ msgs)</span>
    <span><span class="dot" style="background:#fff9c4"></span>Low activity (1-9 msgs)</span>
    <span><span class="dot" style="background:#ffebee"></span>Lurker (0 msgs)</span>
  </div>
  <table id="members-table" style="margin-top:10px">
    <thead><tr>
      <th onclick="sortTable('members-table',0)">Name</th>
      <th onclick="sortTable('members-table',1)">Username</th>
      <th onclick="sortTable('members-table',2)">Roles</th>
      <th onclick="sortTable('members-table',3)">Joined</th>
      <th onclick="sortTable('members-table',4)" style="text-align:right">Messages</th>
      <th onclick="sortTable('members-table',5)">Last Active</th>
    </tr></thead>
    <tbody>{''.join(member_rows)}</tbody>
  </table>

  <h2>Channel Health <span style="font-size:16px;font-weight:normal;color:#999">({snap.channels_scanned} channels)</span></h2>
  <table id="channels-table">
    <thead><tr>
      <th onclick="sortTable('channels-table',0)">Channel</th>
      <th onclick="sortTable('channels-table',1)" style="text-align:right">Messages</th>
      <th onclick="sortTable('channels-table',2)" style="text-align:right">Unique Posters</th>
      <th onclick="sortTable('channels-table',3)">Last Activity</th>
      <th onclick="sortTable('channels-table',4)">Status</th>
    </tr></thead>
    <tbody>{''.join(channel_rows)}</tbody>
  </table>

  {lurker_section}

</div>

<script>
function sortTable(tableId, col) {{
  const table = document.getElementById(tableId);
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const asc = table.dataset.sortCol == col && table.dataset.sortDir == 'asc';
  rows.sort((a, b) => {{
    const av = a.cells[col]?.innerText.trim() || '';
    const bv = b.cells[col]?.innerText.trim() || '';
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return asc ? bn - an : an - bn;
    return asc ? bv.localeCompare(av) : av.localeCompare(bv);
  }});
  rows.forEach(r => tbody.appendChild(r));
  table.dataset.sortCol = col;
  table.dataset.sortDir = asc ? 'desc' : 'asc';
}}
</script>
</body>
</html>"""
