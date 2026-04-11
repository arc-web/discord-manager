# discord_agent/config_loader.py
"""Load multi-server config from servers.json with bot.env fallback."""

import json
from pathlib import Path
from typing import Optional


AGENT_DIR = Path(__file__).parent


def load_server_config(server_name: Optional[str] = None) -> dict:
    """Load config for a named server. Falls back to bot.env if no servers.json."""
    servers_file = AGENT_DIR / "servers.json"

    if servers_file.exists():
        with open(servers_file) as f:
            config = json.load(f)
        name = server_name or config.get("default", "arc")
        server = config["servers"].get(name)
        if not server:
            available = ", ".join(config["servers"].keys())
            raise ValueError(f"Unknown server '{name}'. Available: {available}")

        env_file = AGENT_DIR / server["env_file"]
        env = _parse_env(env_file)
        return {
            "name": name,
            "token": env.get("DISCORD_BOT_TOKEN", ""),
            "guild_id": server.get("guild_id") or env.get("DISCORD_GUILD_ID", ""),
            "bot_id": server.get("bot_id") or env.get("DISCORD_BOT_ID", ""),
            "aliases": server.get("aliases", {}),
            "env_file": str(env_file),
        }

    # Fallback: legacy bot.env
    env_file = AGENT_DIR / "bot.env"
    if not env_file.exists():
        env_file = Path.home() / ".config" / "discord" / "bot.env"
    env = _parse_env(env_file)
    return {
        "name": "default",
        "token": env.get("DISCORD_BOT_TOKEN", ""),
        "guild_id": env.get("DISCORD_GUILD_ID", ""),
        "bot_id": env.get("DISCORD_BOT_ID", ""),
        "aliases": {},
        "env_file": str(env_file),
    }


def list_servers() -> list[str]:
    """List available server names."""
    servers_file = AGENT_DIR / "servers.json"
    if servers_file.exists():
        with open(servers_file) as f:
            config = json.load(f)
        return list(config["servers"].keys())
    return ["default"]


def _parse_env(path: Path) -> dict:
    """Parse a key=value env file."""
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {path}")
    env = {}
    for line in path.read_text().strip().split("\n"):
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env
