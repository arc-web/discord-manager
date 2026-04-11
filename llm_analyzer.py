# discord_agent/llm_analyzer.py
"""LLM analysis layer. Ollama first, Anthropic fallback."""

import json
import os
import re
from pathlib import Path
from typing import Optional

import requests

AGENT_DIR = Path(__file__).parent
DEFAULT_ROLE = "Mike, the founder of Advertising Report Card (an ads agency)"


def load_soul(server_name: str) -> Optional[str]:
    """Load personality soul doc for a server if available."""
    if not server_name:
        return None
    soul_path = AGENT_DIR / "souls" / f"{server_name}_soul.md"
    if soul_path.exists():
        return soul_path.read_text()
    return None

DEFAULT_TEAM_CONTEXT = """- Mike (advertisingreportcard) - owner, the person reading this report
- Johan_l (johannnn_0l) - operator, configures AI agents
- Erfan (erfanalisiam_00984) - PPC/ads team
- Shakil, DNCesar, OllyUp, tim - team members
- OpenClaw, ZeroClaw - AI bots (ignore their automated posts unless they flag a real issue)"""

ANALYSIS_PROMPT = """You are analyzing Discord messages for {role}.

CHANNELS AND MESSAGES:
{channel_blocks}

TEAM MEMBERS:
{team_context}

Return a JSON array. One object per channel that needs attention. If a channel has no actionable items, skip it entirely.

[
  {{
    "channel": "channel-name",
    "summary": "one-sentence summary",
    "items": [
      {{
        "from": "author display name",
        "message": "key quote or description (under 100 chars)",
        "action_needed": "what should be done",
        "draft": "ready-to-send response (direct, no corporate tone)",
        "priority": "high/medium/low"
      }}
    ]
  }}
]

Rules:
- Only include channels where a human needs a response, decision, or acknowledgment
- high = blocking someone or client-facing, medium = needs input soon, low = FYI/acknowledge
- Draft responses: direct, concise, natural voice. Not formal.
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
        self.ollama_model = None
        self.anthropic_key = None
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

    def analyze(
        self,
        channel_messages: dict[str, str],
        role: str = None,
        team_context: str = None,
        server_name: str = None,
    ) -> list[dict]:
        """Analyze messages from multiple channels in one call.
        channel_messages: {channel_name: formatted_message_string}
        role: who is reading (defaults to Mike/ARC)
        team_context: team member list (defaults to ARC team)
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

        # Use soul doc for voice if available
        effective_role = role
        if not effective_role:
            soul = load_soul(server_name)
            effective_role = soul if soul else DEFAULT_ROLE

        prompt = ANALYSIS_PROMPT.format(
            channel_blocks=channel_blocks,
            role=effective_role,
            team_context=team_context or DEFAULT_TEAM_CONTEXT,
        )

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
