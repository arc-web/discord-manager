"""YAML event config loader with env var resolution."""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve ${VAR_NAME} patterns in string values."""
    if isinstance(value, str):
        def replacer(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return re.sub(r'\$\{([^}]+)\}', replacer, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_event(path: str | Path) -> dict:
    """Load and validate an event config YAML file.

    Resolves ${ENV_VAR} references in credential values.
    Returns the full config dict.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Event config not found: {path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError(f"Invalid event config: expected dict, got {type(config).__name__}")

    required = ["server", "name"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required field: {key}")

    # Resolve env vars in credentials
    if "credentials" in config:
        config["credentials"] = _resolve_env_vars(config["credentials"])

    return config


class EventConfig:
    """Convenient accessor for event configuration."""

    def __init__(self, config: dict, source_path: str | Path = None):
        self._config = config
        self.source_path = str(source_path) if source_path else None

    @classmethod
    def from_file(cls, path: str | Path) -> "EventConfig":
        config = load_event(path)
        return cls(config, source_path=path)

    @property
    def server(self) -> str:
        return self._config["server"]

    @property
    def name(self) -> str:
        return self._config["name"]

    @property
    def facilitators(self) -> list[str]:
        return self._config.get("facilitators", [])

    @property
    def roster_path(self) -> str | None:
        roster = self._config.get("roster", {})
        return roster.get("source") if isinstance(roster, dict) else None

    @property
    def pods(self) -> dict:
        return self._config.get("pods", {})

    @property
    def credentials(self) -> dict:
        return self._config.get("credentials", {})

    @property
    def schedule(self) -> list[dict]:
        return self._config.get("schedule", [])

    @property
    def it_support(self) -> dict:
        return self._config.get("it_support", {})

    def to_dict(self) -> dict:
        """Return the full config dict."""
        return self._config

    def summary(self) -> str:
        """Human-readable summary of the event."""
        lines = [
            f"Event: {self.name}",
            f"Server: {self.server}",
            f"Facilitators: {', '.join(self.facilitators) or 'none'}",
        ]
        if self.roster_path:
            lines.append(f"Roster: {self.roster_path}")
        pods = self.pods
        if pods:
            pod_names = pods.get("names", [])
            lines.append(f"Pods: {len(pod_names)} ({', '.join(pod_names)})")
        schedule = self.schedule
        if schedule:
            lines.append(f"Schedule: {len(schedule)} entries")
        if self.source_path:
            lines.append(f"Source: {self.source_path}")
        return "\n".join(lines)
