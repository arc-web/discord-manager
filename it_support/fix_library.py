"""Known-fix lookup system for common IT issues."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

DEFAULT_FIXES_PATH = str(Path(__file__).parent.parent / "fix_db" / "known_fixes.yaml")


def load_fixes(path: str = None) -> list[dict]:
    """Load known fixes from YAML file."""
    path = path or DEFAULT_FIXES_PATH
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("fixes", [])


def match_fix(error_text: str, platform: str = "all") -> dict | None:
    """Match an error message against known fix patterns.

    Returns the first matching fix entry or None.
    Platform "all" matches everything.
    """
    fixes = load_fixes()
    for fix in fixes:
        # Filter by platform
        fix_platform = fix.get("platform", "all")
        if platform != "all" and fix_platform != "all" and fix_platform != platform:
            continue
        pattern = fix.get("error_pattern", "")
        if re.search(pattern, error_text, re.IGNORECASE):
            return fix
    return None


def render_fix(fix: dict, variables: dict = None) -> str:
    """Render a fix template with variable substitution.

    Replaces {{VAR_NAME}} placeholders in the fix_template.
    """
    template = fix.get("fix_template", "")
    if variables:
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
    return template.strip()


def list_fixes(platform: str = None) -> list[dict]:
    """Return all fixes, optionally filtered by platform."""
    fixes = load_fixes()
    if platform is None:
        return fixes
    return [
        f for f in fixes
        if f.get("platform", "all") in (platform, "all")
    ]
