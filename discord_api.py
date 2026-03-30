# discord_agent/discord_api.py
"""Thin Discord REST API client. No subprocess, no shell."""

import json
import time
from pathlib import Path
from typing import Optional

import requests

API_BASE = "https://discord.com/api/v10"

# All text channels to scan, grouped by category
CHANNELS = {
    # Agents
    "agents": "1475741313956843643",
    "agents-ops": "1485448423225167892",
    "agents-integrations": "1485448423175098398",
    "agents-team": "1485448423401459893",
    "agents-business": "1485448423527419964",
    # Clients
    "sfbayareamoving": "1478284209423384657",
    "fdlxibalba": "1478284208052113509",
    "proximahire": "1478284208764882965",
    "collabmedspa": "1478284207498334228",
    # Co-managed
    "co-bpm-awainsurance": "1478284242927620247",
    "co-bpm-napleton": "1486062798311133364",
    "co-moonraker-brainbasedemdr": "1478284243615354982",
    "co-moonraker-nkpsych": "1478284244114739313",
    "co-moonraker-pittsburghcit": "1478284245150597133",
    "co-moonraker-fulltiltautobody": "1483024489326579752",
    "co-drivenstack-myexpertresume": "1483024533156794428",
    "co-moonraker-skytherapies": "1484057668472799384",
    "co-moonraker-mccancemethod": "1485636234872357055",
    # Team ops
    "general": "1264976266084352205",
    "alert": "1477586864926883961",
    "ai-openclaw": "1478284164993388726",
    "team-ppc": "1483024901265952830",
    "n8n-general": "1478284171972575275",
}

BOT_IDS = {"1475745144912220311", "1476934805458259980"}  # OpenClaw, ZeroClaw


class DiscordClient:
    def __init__(self, env_path: Optional[str] = None):
        self.token, self.guild_id, self.bot_id = self._load_env(env_path)
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

    def _load_env(self, env_path: Optional[str] = None) -> tuple:
        """Load token from bot.env. Checks script dir, then ~/.config/discord/."""
        paths_to_try = []
        if env_path:
            paths_to_try.append(Path(env_path))
        paths_to_try.append(Path(__file__).parent / "bot.env")
        paths_to_try.append(Path.home() / ".config" / "discord" / "bot.env")

        for p in paths_to_try:
            if p.exists():
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

        raise FileNotFoundError("bot.env not found")

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
        # API returns newest first, reverse to chronological
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

    def fetch_all_channels(self, limit: int = 20, delay: float = 0.3) -> dict:
        """Fetch messages from all configured channels with rate limiting.
        Returns {channel_name: [messages]}."""
        results = {}
        for name, channel_id in CHANNELS.items():
            messages = self.get_messages(channel_id, limit)
            results[name] = messages
            time.sleep(delay)  # rate limit
        return results
