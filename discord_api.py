# discord_agent/discord_api.py
"""Multi-server Discord REST API client.

DiscordClient - method reference
---------------------------------
Channel resolution:
  discover_channels()                          GET /guilds/{id}/channels -> {name: id}
  resolve_channel(name_or_id)                  alias -> name -> id passthrough
  match_channels(pattern)                      glob match -> [channel_ids]
  get_channel_map()                            aliases + discovered -> {name: id}

Messages:
  get_messages(channel_id, limit=20)           GET /channels/{id}/messages -> [msg]
  send_message(channel_id, content)            POST /channels/{id}/messages -> bool
  broadcast(channels, content, delay=0.3)      send to many -> {name: bool}
  broadcast_template(channels, template, vars) rendered send to many -> {name: bool}
  fetch_all_channels(limit=20, delay=0.3)      all configured channels -> {name: [msg]}

Members:
  get_members(limit=1000)                      GET /guilds/{id}/members (paginated) -> [member]
  search_members(query, limit=10)              fuzzy search -> [member]
  roster_match(names)                          match name list -> {matched, unmatched, suggestions}

Guild:
  get_guild_info()                             GET /guilds/{id}?with_counts=true -> dict

Channel management:
  get_channel(channel_id)                      GET /channels/{id} -> dict
  edit_channel(channel_id, **kwargs)           PATCH /channels/{id} -> dict
  delete_channel(channel_id)                   DELETE /channels/{id} -> bool
  set_channel_permissions(ch_id, ow_id, ...)   PUT /channels/{id}/permissions/{ow_id} -> bool
  delete_channel_permissions(ch_id, ow_id)     DELETE /channels/{id}/permissions/{ow_id} -> bool
  get_categories()                             -> {category_name: category_id}
  scaffold_channels(structure)                 create/update from YAML structure -> {name: status}

DMs and reactions:
  send_dm(user_id, content)                    POST /users/@me/channels + send -> bool
  create_channel(name, channel_type, cat_id)   POST /guilds/{id}/channels -> dict
  get_reactions(channel_id, message_id, emoji) GET /channels/{id}/messages/{id}/reactions/{e} -> [user]
"""

import difflib
import fnmatch
import json
import time
from pathlib import Path
from typing import Optional

import requests

from config_loader import load_server_config

API_BASE = "https://discord.com/api/v10"

# Legacy constants for backward compat (discord_report.py imports these)
CHANNELS = {
    "agents": "1475741313956843643",
    "agents-ops": "1485448423225167892",
    "agents-integrations": "1485448423175098398",
    "agents-team": "1485448423401459893",
    "agents-business": "1485448423527419964",
    "sfbayareamoving": "1478284209423384657",
    "fdlxibalba": "1478284208052113509",
    "proximahire": "1478284208764882965",
    "collabmedspa": "1478284207498334228",
    "co-bpm-awainsurance": "1478284242927620247",
    "co-bpm-napleton": "1486062798311133364",
    "co-moonraker-brainbasedemdr": "1478284243615354982",
    "co-moonraker-nkpsych": "1478284244114739313",
    "co-moonraker-pittsburghcit": "1478284245150597133",
    "co-moonraker-fulltiltautobody": "1483024489326579752",
    "co-drivenstack-myexpertresume": "1483024533156794428",
    "co-moonraker-skytherapies": "1484057668472799384",
    "co-moonraker-mccancemethod": "1485636234872357055",
    "general": "1264976266084352205",
    "alert": "1477586864926883961",
    "ai-openclaw": "1478284164993388726",
    "team-ppc": "1483024901265952830",
    "n8n-general": "1478284171972575275",
}

BOT_IDS = {"1475745144912220311", "1476934805458259980"}


class DiscordClient:
    def __init__(self, server_name: Optional[str] = None, env_path: Optional[str] = None):
        if env_path:
            # Legacy path: load from specific env file
            self.token, self.guild_id, self.bot_id = self._load_env_legacy(env_path)
            self.aliases = {}
            self.server_name = "default"
        else:
            config = load_server_config(server_name)
            self.token = config["token"]
            self.guild_id = config["guild_id"]
            self.bot_id = config["bot_id"]
            self.aliases = config["aliases"]
            self.server_name = config["name"]

        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }
        self._channels_cache = None

    def _load_env_legacy(self, env_path: str) -> tuple:
        """Legacy env loading for backward compat."""
        p = Path(env_path)
        if not p.exists():
            raise FileNotFoundError(f"Env file not found: {env_path}")
        env = {}
        for line in p.read_text().strip().split("\n"):
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
        return (
            env.get("DISCORD_BOT_TOKEN", ""),
            env.get("DISCORD_GUILD_ID", ""),
            env.get("DISCORD_BOT_ID", ""),
        )

    # -- Channel resolution --

    def discover_channels(self) -> dict[str, str]:
        """Fetch all channels from the API. Returns {name: id}."""
        resp = requests.get(
            f"{API_BASE}/guilds/{self.guild_id}/channels",
            headers=self.headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        channels = {}
        for c in resp.json():
            if isinstance(c, dict) and c.get("name"):
                channels[c["name"]] = c["id"]
        self._channels_cache = channels
        return channels

    def resolve_channel(self, name_or_id: str) -> str:
        """Resolve alias -> discovered name -> passthrough ID."""
        if name_or_id in self.aliases:
            return self.aliases[name_or_id]
        if name_or_id.isdigit() and len(name_or_id) > 15:
            return name_or_id
        if self._channels_cache is None:
            self.discover_channels()
        return (self._channels_cache or {}).get(name_or_id, name_or_id)

    def match_channels(self, pattern: str) -> list[str]:
        """Match channel names by glob pattern (e.g. 'pod-*'). Returns channel IDs."""
        if self._channels_cache is None:
            self.discover_channels()
        all_names = list(self.aliases.keys()) + list((self._channels_cache or {}).keys())
        matched = set()
        for name in all_names:
            if fnmatch.fnmatch(name, pattern):
                matched.add(self.resolve_channel(name))
        return list(matched)

    def get_channel_map(self) -> dict[str, str]:
        """Get combined alias + discovered channel map."""
        if self._channels_cache is None:
            self.discover_channels()
        merged = dict(self._channels_cache or {})
        merged.update(self.aliases)
        return merged

    # -- Messages --

    def get_messages(self, channel_id: str, limit: int = 20) -> list[dict]:
        """Fetch recent messages from a channel. Returns newest-last."""
        resp = requests.get(
            f"{API_BASE}/channels/{channel_id}/messages",
            headers=self.headers,
            params={"limit": limit},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        messages = resp.json()
        if not isinstance(messages, list):
            return []
        return list(reversed(messages))

    def send_message(self, channel_id: str, content: str) -> bool:
        """Send a message to a channel. Returns True on success."""
        resp = requests.post(
            f"{API_BASE}/channels/{channel_id}/messages",
            headers=self.headers,
            json={"content": content},
            timeout=10,
        )
        return resp.status_code == 200

    def broadcast(self, channels: list[str], content: str, delay: float = 0.3) -> dict[str, bool]:
        """Send the same message to multiple channels. Returns {channel: success}."""
        results = {}
        for ch in channels:
            channel_id = self.resolve_channel(ch)
            results[ch] = self.send_message(channel_id, content)
            if delay and ch != channels[-1]:
                time.sleep(delay)
        return results

    def broadcast_template(self, channels: list[str], template: str,
                           variables: dict, delay: float = 0.3) -> dict[str, bool]:
        """Send a templated message to multiple channels.
        {{channel}} is auto-populated with the channel name."""
        results = {}
        for ch in channels:
            channel_id = self.resolve_channel(ch)
            vars_with_channel = {**variables, "channel": ch}
            content = template
            for key, val in vars_with_channel.items():
                content = content.replace(f"{{{{{key}}}}}", str(val))
            results[ch] = self.send_message(channel_id, content)
            if delay and ch != channels[-1]:
                time.sleep(delay)
        return results

    # -- Members --

    def get_members(self, limit: int = 1000) -> list[dict]:
        """Fetch guild members (paginated for large servers)."""
        all_members = []
        after = "0"
        per_page = min(limit, 1000)
        while len(all_members) < limit:
            resp = requests.get(
                f"{API_BASE}/guilds/{self.guild_id}/members",
                headers=self.headers,
                params={"limit": per_page, "after": after},
                timeout=10,
            )
            if resp.status_code != 200:
                break
            batch = resp.json()
            if not batch:
                break
            all_members.extend(batch)
            after = batch[-1]["user"]["id"]
            if len(batch) < per_page:
                break
            time.sleep(0.3)
        return all_members[:limit]

    def search_members(self, query: str, limit: int = 10) -> list[dict]:
        """Fuzzy search members by display name or username."""
        members = self.get_members()
        names_map = {}
        for m in members:
            u = m["user"]
            display = m.get("nick") or u.get("global_name") or u["username"]
            names_map[display.lower()] = m
            names_map[u["username"].lower()] = m

        matches = difflib.get_close_matches(query.lower(), names_map.keys(), n=limit, cutoff=0.4)
        seen_ids = set()
        results = []
        for match in matches:
            member = names_map[match]
            uid = member["user"]["id"]
            if uid not in seen_ids:
                seen_ids.add(uid)
                results.append(member)
        return results

    def roster_match(self, names: list[str]) -> dict:
        """Match a list of external names against server members.
        Returns {matched: [...], unmatched: [...], suggestions: {name: [closest]}}."""
        members = self.get_members()
        member_names = {}
        for m in members:
            u = m["user"]
            if u.get("bot"):
                continue
            display = m.get("nick") or u.get("global_name") or u["username"]
            member_names[display] = {
                "id": u["id"],
                "username": u["username"],
                "display_name": display,
            }

        all_display = list(member_names.keys())
        matched = []
        unmatched = []
        suggestions = {}

        for name in names:
            name = name.strip()
            if not name:
                continue
            # Exact match (case-insensitive)
            exact = next((d for d in all_display if d.lower() == name.lower()), None)
            if exact:
                matched.append({"roster_name": name, **member_names[exact]})
                continue
            # Fuzzy match
            close = difflib.get_close_matches(name, all_display, n=3, cutoff=0.4)
            if close:
                # If top match is very close, auto-match
                ratio = difflib.SequenceMatcher(None, name.lower(), close[0].lower()).ratio()
                if ratio >= 0.7:
                    matched.append({"roster_name": name, **member_names[close[0]], "fuzzy": True})
                else:
                    unmatched.append(name)
                    suggestions[name] = close
            else:
                unmatched.append(name)

        return {"matched": matched, "unmatched": unmatched, "suggestions": suggestions}

    # -- Guild info --

    def get_guild_info(self) -> dict:
        """Get basic guild metadata."""
        resp = requests.get(
            f"{API_BASE}/guilds/{self.guild_id}",
            headers=self.headers,
            params={"with_counts": "true"},
            timeout=10,
        )
        if resp.status_code != 200:
            return {}
        return resp.json()

    # -- DMs, channels, reactions --

    def send_dm(self, user_id: str, content: str) -> bool:
        """Send a DM to a user. Creates DM channel first."""
        # Create DM channel
        resp = requests.post(
            f"{API_BASE}/users/@me/channels",
            headers=self.headers,
            json={"recipient_id": user_id},
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            return False
        dm_channel_id = resp.json()["id"]
        # Send message
        return self.send_message(dm_channel_id, content)

    def create_channel(self, name: str, channel_type: int = 0,
                       category_id: str = None) -> dict:
        """Create a guild channel. type 0=text, 2=voice, 4=category."""
        payload = {"name": name, "type": channel_type}
        if category_id:
            payload["parent_id"] = category_id
        resp = requests.post(
            f"{API_BASE}/guilds/{self.guild_id}/channels",
            headers=self.headers,
            json=payload,
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            return {}
        return resp.json()

    def get_reactions(self, channel_id: str, message_id: str, emoji: str) -> list[dict]:
        """Get users who reacted with a specific emoji."""
        import urllib.parse
        encoded = urllib.parse.quote(emoji)
        resp = requests.get(
            f"{API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded}",
            headers=self.headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        return resp.json()

    # -- Channel management --

    def get_channel(self, channel_id: str) -> dict:
        """Get full channel object - name, topic, category, position, type."""
        resp = requests.get(f"{API_BASE}/channels/{channel_id}", headers=self.headers, timeout=10)
        return resp.json() if resp.status_code == 200 else {}

    def edit_channel(self, channel_id: str, **kwargs) -> dict:
        """Edit a channel. Accepts: name, topic, parent_id, position, nsfw, etc."""
        resp = requests.patch(f"{API_BASE}/channels/{channel_id}", headers=self.headers, json=kwargs, timeout=10)
        return resp.json() if resp.status_code == 200 else {}

    def delete_channel(self, channel_id: str) -> bool:
        """Permanently delete a channel."""
        resp = requests.delete(f"{API_BASE}/channels/{channel_id}", headers=self.headers, timeout=10)
        return resp.status_code == 200

    def set_channel_permissions(self, channel_id: str, overwrite_id: str,
                                 allow: str = "0", deny: str = "0", perm_type: int = 0) -> bool:
        """Set permission overwrite for a role (type=0) or member (type=1).
        allow/deny are permission bit strings."""
        resp = requests.put(
            f"{API_BASE}/channels/{channel_id}/permissions/{overwrite_id}",
            headers=self.headers,
            json={"allow": allow, "deny": deny, "type": perm_type},
            timeout=10,
        )
        return resp.status_code == 204

    def delete_channel_permissions(self, channel_id: str, overwrite_id: str) -> bool:
        """Remove a permission overwrite from a channel."""
        resp = requests.delete(
            f"{API_BASE}/channels/{channel_id}/permissions/{overwrite_id}",
            headers=self.headers,
            timeout=10,
        )
        return resp.status_code == 204

    def get_categories(self) -> dict:
        """Return {category_name: category_id} for all category channels."""
        resp = requests.get(f"{API_BASE}/guilds/{self.guild_id}/channels", headers=self.headers, timeout=10)
        if resp.status_code != 200:
            return {}
        return {c["name"]: c["id"] for c in resp.json() if c.get("type") == 4}

    def scaffold_channels(self, structure: dict) -> dict:
        """Create/update channel structure from a dict.
        structure: {"categories": [{"name": str, "channels": [{"name": str, "topic": str}]}]}
        Returns {channel_name: "created"|"updated"}.
        Non-destructive - never deletes existing channels."""
        results = {}
        existing = self.discover_channels()
        existing_categories = self.get_categories()

        for cat in structure.get("categories", []):
            cat_name = cat["name"]
            if cat_name not in existing_categories:
                created = self.create_channel(cat_name, channel_type=4)
                cat_id = created.get("id")
                existing_categories[cat_name] = cat_id
                time.sleep(0.3)
            else:
                cat_id = existing_categories[cat_name]

            if not cat_id:
                continue

            for ch in cat.get("channels", []):
                ch_name = ch["name"]
                topic = ch.get("topic", "")
                if ch_name in existing:
                    self.edit_channel(existing[ch_name], parent_id=cat_id, topic=topic)
                    results[ch_name] = "updated"
                else:
                    created = self.create_channel(ch_name, channel_type=0, category_id=cat_id)
                    if topic and created.get("id"):
                        self.edit_channel(created["id"], topic=topic)
                    results[ch_name] = "created"
                time.sleep(0.3)

        return results

    # -- Batch operations (legacy compat) --

    def fetch_all_channels(self, limit: int = 20, delay: float = 0.3) -> dict:
        """Fetch messages from all configured channels with rate limiting.
        Uses aliases for the current server, or CHANNELS for legacy arc."""
        channel_map = self.aliases if self.aliases else CHANNELS
        results = {}
        for name, channel_id in channel_map.items():
            messages = self.get_messages(channel_id, limit)
            results[name] = messages
            time.sleep(delay)
        return results
