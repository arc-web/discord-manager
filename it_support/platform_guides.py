"""Mac vs Windows instruction variants for common operations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_env_set_command(platform: str, var_name: str, var_value: str) -> str:
    """Return the platform-specific command to set an environment variable."""
    if platform == "windows":
        return f'$env:{var_name}="{var_value}"'
    return f'export {var_name}={var_value}'


def get_env_unset_command(platform: str, var_name: str) -> str:
    """Return the platform-specific command to unset an environment variable."""
    if platform == "windows":
        return f"Remove-Item Env:{var_name}"
    return f"unset {var_name}"


def get_install_claude_command(platform: str) -> str:
    """Return the install command for Claude Code on the given platform."""
    if platform == "windows":
        return "irm https://claude.ai/install.ps1 | iex"
    return "curl -fsSL https://claude.ai/install.sh | sh"


def get_path_fix_command(platform: str) -> str:
    """Return the PATH fix command for Claude Code on the given platform."""
    if platform == "windows":
        return '$env:Path += ";$env:USERPROFILE\\.local\\bin"'
    return 'export PATH="$HOME/.local/bin:$PATH"'
