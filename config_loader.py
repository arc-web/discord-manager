# discord_agent/config_loader.py
"""Load multi-server config from servers.json.

Credentials come from 1Password via the shared op_loader helper:
    7_tools/credentials/op_loader.py

Resolution order for DISCORD_BOT_TOKEN (first hit wins):
    1. DISCORD_BOT_TOKEN env var (set when launched via `op run --env-file=.env.1p.<server>`)
    2. `op read op://ARC/Discord Bot Token - <name>/credential` (direct CLI call)

Either launch path works — the wrapper is nice but not required.
"""

import sys
import json
from pathlib import Path
from typing import Optional

# Import shared credential helper
_CREDS_DIR = Path(__file__).parent.parent.parent / "7_tools" / "credentials"
sys.path.insert(0, str(_CREDS_DIR))
from op_loader import load as _op_load  # noqa: E402


AGENT_DIR = Path(__file__).parent

# Map server name → 1Password reference
_OP_REFS = {
    "arc": "op://ARC/Discord Bot Token - OpenClaw/credential",
    "conference": "op://ARC/Discord Bot Token - claudeconference/credential",
    "stackpack": "op://ARC/Discord Bot Token - StackPack.app/credential",
}


def load_server_config(server_name: Optional[str] = None) -> dict:
    """Load server config from servers.json. Token resolves via op_loader."""
    servers_file = AGENT_DIR / "servers.json"
    if not servers_file.exists():
        raise FileNotFoundError(f"servers.json missing at {servers_file}")

    with open(servers_file) as f:
        config = json.load(f)
    name = server_name or config.get("default", "arc")
    server = config["servers"].get(name)
    if not server:
        available = ", ".join(config["servers"].keys())
        raise ValueError(f"Unknown server '{name}'. Available: {available}")

    op_ref = _OP_REFS.get(name)
    if not op_ref:
        raise ValueError(f"No 1Password reference mapped for server '{name}'")

    token = _op_load("DISCORD_BOT_TOKEN", op_ref)

    return {
        "name": name,
        "token": token,
        "guild_id": server.get("guild_id", ""),
        "bot_id": server.get("bot_id", ""),
        "aliases": server.get("aliases", {}),
        "env_file": str(AGENT_DIR / f".env.1p.{name}"),
    }


def list_servers() -> list[str]:
    """List available server names."""
    servers_file = AGENT_DIR / "servers.json"
    if servers_file.exists():
        with open(servers_file) as f:
            config = json.load(f)
        return list(config["servers"].keys())
    return ["default"]


