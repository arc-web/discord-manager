# Discord Report Tool Rewrite

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite discord_report.py to call Discord API directly, use Ollama (with Anthropic fallback), auto-discover all credentials, and fix the broken author parsing / channel sending bugs.

**Architecture:** Single Python script that reads bot.env for Discord token, calls Discord REST API via `requests`, batches channel messages into 3 Ollama calls (clients, agents, team/co-managed), formats a numbered approval list, and sends approved drafts directly via Discord API. No subprocess calls. No manual API key exports.

**Tech Stack:** Python 3, requests, Ollama REST API (localhost:11434), Anthropic SDK (fallback)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `discord_agent/discord_report.py` | Rewrite | Main report tool - fetch, analyze, display, send |
| `discord_agent/discord_api.py` | Create | Thin Discord REST API client (shared by discord_report.py and future tools) |
| `discord_agent/bot.env` | Read-only | Token source |
| `discord_agent/discord.sh` | No change | Stays as-is for manual CLI use |
| `discord_agent/discord.sh` | Fix | Remove dead code on line 76 |

---

### Task 1: Discord API Client

**Files:**
- Create: `discord_agent/discord_api.py`

- [ ] **Step 1: Write the failing test**

Create a test that verifies the client loads the token and constructs proper headers.

```python
# discord_agent/test_discord_api.py
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from discord_api import DiscordClient

def test_client_loads_token(tmp_path):
    env_file = tmp_path / "bot.env"
    env_file.write_text("DISCORD_BOT_TOKEN=test_token_123\nDISCORD_GUILD_ID=999\nDISCORD_BOT_ID=111\n")
    client = DiscordClient(env_path=str(env_file))
    assert client.token == "test_token_123"
    assert client.guild_id == "999"
    assert "Bot test_token_123" in client.headers["Authorization"]

def test_client_auto_discovers_env():
    """Should find bot.env in same directory as discord_api.py"""
    client = DiscordClient()
    assert client.token  # should load from discord_agent/bot.env
    assert len(client.token) > 20

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        from pathlib import Path
        test_client_loads_token(Path(td))
    test_client_auto_discovers_env()
    print("PASS: discord_api tests")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/aimacpro/4_agents/discord_agent && python3 test_discord_api.py`
Expected: `ModuleNotFoundError: No module named 'discord_api'`

- [ ] **Step 3: Write the Discord API client**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/aimacpro/4_agents/discord_agent && python3 test_discord_api.py`
Expected: `PASS: discord_api tests`

- [ ] **Step 5: Commit**

```bash
cd ~/aimacpro/4_agents/discord_agent
git add discord_api.py test_discord_api.py
git commit -m "feat: add direct Discord API client"
```

---

### Task 2: LLM Analyzer with Ollama + Anthropic Fallback

**Files:**
- Create: `discord_agent/llm_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# discord_agent/test_llm_analyzer.py
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from llm_analyzer import LLMAnalyzer, parse_analysis_json

def test_parse_analysis_json_valid():
    raw = '{"needs_attention": true, "summary": "test", "items": [{"from": "Erfan", "message": "help", "action_needed": "respond", "draft": "On it", "priority": "high"}]}'
    result = parse_analysis_json(raw)
    assert result["needs_attention"] is True
    assert len(result["items"]) == 1
    assert result["items"][0]["from"] == "Erfan"

def test_parse_analysis_json_wrapped_in_markdown():
    raw = '```json\n{"needs_attention": false, "summary": "quiet", "items": []}\n```'
    result = parse_analysis_json(raw)
    assert result["needs_attention"] is False

def test_parse_analysis_json_garbage():
    result = parse_analysis_json("this is not json at all")
    assert result["needs_attention"] is False
    assert result["items"] == []

def test_analyzer_detects_backend():
    analyzer = LLMAnalyzer()
    assert analyzer.backend in ("ollama", "anthropic", None)
    print(f"  Backend detected: {analyzer.backend}")

if __name__ == "__main__":
    test_parse_analysis_json_valid()
    test_parse_analysis_json_wrapped_in_markdown()
    test_parse_analysis_json_garbage()
    test_analyzer_detects_backend()
    print("PASS: llm_analyzer tests")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/aimacpro/4_agents/discord_agent && python3 test_llm_analyzer.py`
Expected: `ModuleNotFoundError: No module named 'llm_analyzer'`

- [ ] **Step 3: Write the LLM analyzer**

```python
# discord_agent/llm_analyzer.py
"""LLM analysis layer. Ollama first, Anthropic fallback."""

import json
import os
import re
from pathlib import Path
from typing import Optional

import requests

ANALYSIS_PROMPT = """You are analyzing Discord messages for Mike, the founder of Advertising Report Card (an ads agency).

CHANNELS AND MESSAGES:
{channel_blocks}

TEAM MEMBERS:
- Mike (advertisingreportcard) - owner, the person reading this report
- Johan_l (johannnn_0l) - operator, configures AI agents
- Erfan (erfanalisiam_00984) - PPC/ads team
- Shakil, DNCesar, OllyUp, tim - team members
- OpenClaw, ZeroClaw - AI bots (ignore their automated posts unless they flag a real issue)

Return a JSON array. One object per channel that needs Mike's attention. If a channel has no actionable items, skip it entirely.

[
  {{
    "channel": "channel-name",
    "summary": "one-sentence summary",
    "items": [
      {{
        "from": "author display name",
        "message": "key quote or description (under 100 chars)",
        "action_needed": "what Mike should do",
        "draft": "ready-to-send response in Mike's voice (direct, no corporate tone)",
        "priority": "high/medium/low"
      }}
    ]
  }}
]

Rules:
- Only include channels where a human needs a response, decision, or acknowledgment from Mike
- high = blocking someone or client-facing, medium = needs input soon, low = FYI/acknowledge
- Draft responses: direct, concise, Mike's natural voice. Not formal.
- Return valid JSON array only. No markdown wrapping. No explanation text."""


def parse_analysis_json(raw: str) -> dict:
    """Parse LLM response into structured data. Handles markdown wrapping."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        # Could be array (batch) or single object
        if isinstance(parsed, list):
            return {"channels": parsed}
        if isinstance(parsed, dict):
            if "channels" in parsed:
                return parsed
            if "needs_attention" in parsed:
                return parsed  # single-channel format
            return {"channels": [parsed]}
    except json.JSONDecodeError:
        # Try to extract JSON from surrounding text
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                return {"channels": json.loads(match.group())}
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    return {"needs_attention": False, "items": [], "channels": []}


class LLMAnalyzer:
    def __init__(self):
        self.backend = self._detect_backend()

    def _detect_backend(self) -> Optional[str]:
        """Check Ollama first, then Anthropic."""
        # Try Ollama
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                # Prefer qwen2.5:14b, fall back to any available
                for preferred in ["qwen2.5:14b", "qwen2.5:7b", "llama3.2"]:
                    if any(preferred in m for m in models):
                        self.ollama_model = preferred
                        return "ollama"
                if models:
                    self.ollama_model = models[0]
                    return "ollama"
        except (requests.ConnectionError, requests.Timeout):
            pass

        # Try Anthropic
        api_key = self._find_anthropic_key()
        if api_key:
            self.anthropic_key = api_key
            return "anthropic"

        return None

    def _find_anthropic_key(self) -> Optional[str]:
        """Auto-discover Anthropic API key. No manual export needed."""
        # Check env first
        key = os.getenv("ANTHROPIC_API_KEY")
        if key:
            return key

        # Check credentials.env
        creds_path = Path.home() / "aimacpro" / "4_agents" / "authentication_agent" / "admin" / "credentials.env"
        if creds_path.exists():
            for line in creds_path.read_text().split("\n"):
                if "sk-ant-api03" in line:
                    match = re.search(r"(sk-ant-api03-\S+)", line)
                    if match:
                        return match.group(1)

        return None

    def analyze(self, channel_messages: dict) -> list[dict]:
        """Analyze messages from multiple channels in one call.
        channel_messages: {channel_name: formatted_message_string}
        Returns list of channel analysis dicts."""
        if not self.backend:
            print("Error: No LLM available (Ollama not running, no Anthropic key found)")
            return []

        # Build the batched prompt
        channel_blocks = ""
        for name, msgs in channel_messages.items():
            if msgs.strip():
                channel_blocks += f"\n--- #{name} ---\n{msgs}\n"

        if not channel_blocks.strip():
            return []

        prompt = ANALYSIS_PROMPT.format(channel_blocks=channel_blocks)

        if self.backend == "ollama":
            return self._call_ollama(prompt)
        else:
            return self._call_anthropic(prompt)

    def _call_ollama(self, prompt: str) -> list[dict]:
        """Call Ollama REST API."""
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048},
                },
                timeout=120,
            )
            if resp.status_code == 200:
                result = parse_analysis_json(resp.json().get("response", ""))
                return result.get("channels", [])
        except Exception as e:
            print(f"Ollama error: {e}")
        return []

    def _call_anthropic(self, prompt: str) -> list[dict]:
        """Call Anthropic API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            result = parse_analysis_json(msg.content[0].text)
            return result.get("channels", [])
        except Exception as e:
            print(f"Anthropic error: {e}")
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/aimacpro/4_agents/discord_agent && python3 test_llm_analyzer.py`
Expected: `PASS: llm_analyzer tests`

- [ ] **Step 5: Commit**

```bash
cd ~/aimacpro/4_agents/discord_agent
git add llm_analyzer.py test_llm_analyzer.py
git commit -m "feat: add LLM analyzer with Ollama/Anthropic fallback"
```

---

### Task 3: Rewrite discord_report.py

**Files:**
- Rewrite: `discord_agent/discord_report.py`

- [ ] **Step 1: Write the failing test**

```python
# discord_agent/test_discord_report.py
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from discord_report import format_messages, format_report, parse_approval_input

def test_format_messages_includes_bots_as_context():
    messages = [
        {"author": {"username": "OpenClaw", "id": "1475745144912220311", "bot": True}, "content": "Daily report posted", "timestamp": "2026-03-30T10:00:00"},
        {"author": {"username": "erfanalisiam_00984", "global_name": "Erfan Ali SIam", "id": "123", "bot": False}, "content": "What should I do next?", "timestamp": "2026-03-30T11:00:00"},
    ]
    result = format_messages(messages)
    assert "OpenClaw" in result  # bots included as context
    assert "Erfan Ali SIam" in result  # full display name used
    assert "What should I do next?" in result

def test_format_messages_empty():
    assert format_messages([]) == ""

def test_format_report_sorts_by_priority():
    channel_analyses = [
        {"channel": "general", "summary": "low", "items": [{"from": "tim", "message": "hey", "action_needed": "ack", "draft": "hey", "priority": "low"}]},
        {"channel": "fdlxibalba", "summary": "urgent", "items": [{"from": "Erfan", "message": "blocked", "action_needed": "unblock", "draft": "on it", "priority": "high"}]},
    ]
    report_text, items = format_report(channel_analyses)
    assert items[0]["priority"] == "high"
    assert items[1]["priority"] == "low"

def test_parse_approval_input():
    assert parse_approval_input("1,3", 5) == [1, 3]
    assert parse_approval_input("all", 5) == [1, 2, 3, 4, 5]
    assert parse_approval_input("none", 5) == []
    assert parse_approval_input("99", 5) is None  # invalid

if __name__ == "__main__":
    test_format_messages_includes_bots_as_context()
    test_format_messages_empty()
    test_format_report_sorts_by_priority()
    test_parse_approval_input()
    print("PASS: discord_report tests")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/aimacpro/4_agents/discord_agent && python3 test_discord_report.py`
Expected: `ImportError: cannot import name 'format_messages' from 'discord_report'`

- [ ] **Step 3: Rewrite discord_report.py**

```python
#!/usr/bin/env python3
"""
Discord Channel Report Tool
Scans all channels, analyzes with LLM, presents draft responses for approval.

Usage: python3 discord_report.py
No manual API key setup needed - auto-discovers everything.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from discord_api import DiscordClient, CHANNELS, BOT_IDS
from llm_analyzer import LLMAnalyzer


def format_messages(messages: list[dict]) -> str:
    """Format Discord API message objects into readable text.
    Includes ALL messages (bots too) for context. Uses full display names."""
    if not messages:
        return ""
    lines = []
    for m in messages:
        author_obj = m.get("author", {})
        # Use global_name (display name) first, fall back to username
        name = author_obj.get("global_name") or author_obj.get("username", "?")
        content = m.get("content", "")[:200]
        ts = m.get("timestamp", "")[:19]
        if content:
            lines.append(f"[{ts}] {name}: {content}")
    return "\n".join(lines)


def has_human_activity(messages: list[dict]) -> bool:
    """Check if any messages are from humans (not bots)."""
    for m in messages:
        author = m.get("author", {})
        if author.get("id") not in BOT_IDS and not author.get("bot", False):
            return True
    return False


def format_report(channel_analyses: list[dict]) -> tuple[str, list]:
    """Format LLM analysis into a numbered approval list."""
    items = []
    for analysis in channel_analyses:
        channel = analysis.get("channel", "?")
        for item in analysis.get("items", []):
            items.append({
                "channel": channel,
                "channel_id": CHANNELS.get(channel, channel),
                "from": item.get("from", "?"),
                "message": item.get("message", ""),
                "draft": item.get("draft", ""),
                "priority": item.get("priority", "medium"),
                "action": item.get("action_needed", ""),
            })

    # Sort by priority
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: order.get(x["priority"], 3))

    # Build display
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  DISCORD CHANNEL REPORT - {date_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"  {len(items)} items need your response",
        "",
    ]

    emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for idx, item in enumerate(items, 1):
        e = emoji.get(item["priority"], "⚪")
        lines.append(f"  [{idx}] {e} #{item['channel']} - {item['from']}")
        msg = item["message"][:80]
        lines.append(f"      MSG:   \"{msg}{'...' if len(item['message']) > 80 else ''}\"")
        draft = item["draft"][:80]
        lines.append(f"      DRAFT: \"{draft}{'...' if len(item['draft']) > 80 else ''}\"")
        if item["action"]:
            lines.append(f"      ACTION: {item['action']}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines), items


def parse_approval_input(user_input: str, total: int) -> Optional[list[int]]:
    """Parse approval input. Returns list of indices, [] for none, None for invalid."""
    text = user_input.strip().lower()
    if text == "none":
        return []
    if text == "all":
        return list(range(1, total + 1))
    try:
        indices = [int(x.strip()) for x in text.split(",")]
        if all(1 <= x <= total for x in indices):
            return indices
    except ValueError:
        pass
    return None


def main():
    print("Discord Channel Report")
    print("======================\n")

    # Init Discord client
    discord = DiscordClient()
    print(f"  Bot: {discord.bot_id}")

    # Init LLM
    analyzer = LLMAnalyzer()
    if not analyzer.backend:
        print("\n  ERROR: No LLM available.")
        print("  - Start Ollama: open /Applications/Ollama.app (or brew install ollama)")
        print("  - Or set ANTHROPIC_API_KEY in env")
        sys.exit(1)
    print(f"  LLM: {analyzer.backend}" + (f" ({analyzer.ollama_model})" if analyzer.backend == "ollama" else ""))
    print(f"\n  Scanning {len(CHANNELS)} channels...\n")

    # Fetch all channel messages
    all_messages = discord.fetch_all_channels(limit=20, delay=0.3)

    # Filter to channels with human activity, format for LLM
    active_channels = {}
    quiet_channels = []
    for name, messages in all_messages.items():
        if has_human_activity(messages):
            formatted = format_messages(messages)
            if formatted:
                active_channels[name] = formatted
                print(f"    {name}: {len(messages)} msgs (human activity)")
            else:
                quiet_channels.append(name)
        else:
            quiet_channels.append(name)

    if not active_channels:
        print("\n  All channels quiet. Nothing needs your attention.")
        return

    print(f"\n    {len(quiet_channels)} channels quiet, {len(active_channels)} with activity")
    print(f"\n  Analyzing with {analyzer.backend}...")

    # Batch analyze all active channels in one LLM call
    channel_analyses = analyzer.analyze(active_channels)

    if not channel_analyses:
        print("\n  No items need your response. All clear.")
        return

    # Format and display
    report, items = format_report(channel_analyses)
    print(report)

    if not items:
        print("  No items need your response. All clear.")
        return

    # Approval loop
    while True:
        try:
            user_input = input("  Send which drafts? (1,3 / all / none): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return

        approved = parse_approval_input(user_input, len(items))
        if approved is not None:
            break
        print(f"  Invalid. Enter numbers 1-{len(items)}, 'all', or 'none'.")

    if not approved:
        print("  No drafts sent.")
        return

    # Send approved drafts
    for idx in approved:
        item = items[idx - 1]
        channel_id = item["channel_id"]
        draft = item["draft"]
        print(f"\n  Sending to #{item['channel']}...", end=" ")
        if discord.send_message(channel_id, draft):
            print("sent")
        else:
            print("FAILED")

    print("\n  Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/aimacpro/4_agents/discord_agent && python3 test_discord_report.py`
Expected: `PASS: discord_report tests`

- [ ] **Step 5: Commit**

```bash
cd ~/aimacpro/4_agents/discord_agent
git add discord_report.py test_discord_report.py
git commit -m "feat: rewrite discord_report with direct API calls and Ollama support"
```

---

### Task 4: Fix discord.sh Dead Code

**Files:**
- Modify: `discord_agent/discord.sh:76`

- [ ] **Step 1: Remove dead code on line 76**

Line 76 is a broken first attempt at payload construction that gets immediately overwritten by line 78. Remove it.

Change the `send` case from:

```bash
  send)
    channel=$(resolve_channel "${1:?channel required}")
    message="${2:?message required}"
    payload=$(python3 -c "import json; print(json.dumps({'content': $(python3 -c "import sys,json; print(json.dumps('$message'))" 2>/dev/null || echo "\"$message\"")}))" 2>/dev/null)
    # Safer: use python to build the whole payload
    payload=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$message")
    discord_api POST "/channels/$channel/messages" -d "$payload"
    ;;
```

To:

```bash
  send)
    channel=$(resolve_channel "${1:?channel required}")
    message="${2:?message required}"
    payload=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$message")
    discord_api POST "/channels/$channel/messages" -d "$payload"
    ;;
```

- [ ] **Step 2: Test that send still works**

Run: `~/aimacpro/4_agents/discord_agent/discord.sh whoami`
Expected: `Bot: OpenClaw#7326` / `ID: 1475745144912220311`

- [ ] **Step 3: Commit**

```bash
cd ~/aimacpro/4_agents/discord_agent
git add discord.sh
git commit -m "fix: remove dead code in discord.sh send command"
```

---

### Task 5: End-to-End Test

- [ ] **Step 1: Run all unit tests**

```bash
cd ~/aimacpro/4_agents/discord_agent
python3 test_discord_api.py && python3 test_llm_analyzer.py && python3 test_discord_report.py
```

Expected: All 3 print PASS.

- [ ] **Step 2: Run the full report tool**

```bash
cd ~/aimacpro/4_agents/discord_agent
python3 discord_report.py
```

Expected output:
1. Bot ID displayed
2. LLM backend detected (ollama or anthropic)
3. Channels scanned with activity counts
4. Formatted report with numbered items
5. Approval prompt

- [ ] **Step 3: Test approval flow**

Type `none` at the prompt to verify no messages are sent.
Then run again and type `1` to test sending a single draft.

- [ ] **Step 4: Clean up test files and commit**

```bash
cd ~/aimacpro/4_agents/discord_agent
rm test_discord_api.py test_llm_analyzer.py test_discord_report.py
git add -A
git commit -m "feat: discord report tool complete - direct API, Ollama/Anthropic, batch analysis"
```

---

## Verification

```bash
# Full end-to-end
cd ~/aimacpro/4_agents/discord_agent && python3 discord_report.py

# Should:
# 1. Auto-detect bot token from bot.env (no manual setup)
# 2. Auto-detect LLM (Ollama if running, else Anthropic from credentials.env)
# 3. Scan 25 channels via direct Discord API calls
# 4. Show which channels have human activity
# 5. Batch-analyze in 1 LLM call (not 25)
# 6. Display numbered approval list sorted by priority
# 7. Send approved drafts using channel IDs (not aliases)
```

## What Changed vs Original

| Problem | Before | After |
|---------|--------|-------|
| API key | Manual `export ANTHROPIC_API_KEY` | Auto-discovers from credentials.env |
| LLM | Anthropic only | Ollama first, Anthropic fallback |
| Discord calls | 25 subprocess calls to discord.sh | Direct `requests` to Discord API |
| Author names | Regex `\S+` breaks on spaces | Full `global_name` from API JSON |
| LLM calls | 25 separate API calls | 1 batched call |
| Co-managed send | Fails (no alias) | Uses channel IDs directly |
| Bot context | Stripped before analysis | Included as context |
| Rate limiting | None | 0.3s delay between Discord calls |
