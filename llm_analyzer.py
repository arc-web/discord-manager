# discord_agent/llm_analyzer.py
"""LLM analysis layer.

Provider chain:
  - "auto" + task_hint="chat" (default) -> openrouter:gemini -> openrouter:kimi -> ollama
  - "auto" + task_hint in ("agentic","long_context") -> openrouter:kimi -> openrouter:gemini -> ollama
  - explicit provider= short-circuits to that provider only

OpenRouter unified endpoint serves both Gemini Flash and Kimi K2.6 with one key.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests

# Reuse shared op_loader for 1Password resolution
_CREDS_DIR = Path.home() / "ai" / "workspaces" / "aimacpro" / "7_tools" / "credentials"
if str(_CREDS_DIR) not in sys.path:
    sys.path.insert(0, str(_CREDS_DIR))
try:
    from op_loader import load as _op_load
except ImportError:
    _op_load = None

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# UUID form because the item title contains an em-dash, which the op:// secret-reference
# parser rejects. UUID resolves to "OpenRouter Key — Claude Code Local" in Zeroclaw vault.
OPENROUTER_OP_REF = "op://Zeroclaw/qbmvnmef72w46iywjyt752zz2q/credential"
MODEL_GEMINI_FLASH = "google/gemini-2.5-flash"
MODEL_KIMI_K2 = "moonshotai/kimi-k2.6"

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
    def __init__(self, provider: str = "auto", task_hint: str = "chat"):
        """provider: 'auto' | 'gemini' | 'kimi' | 'ollama'
        task_hint: 'chat' | 'agentic' | 'long_context' (used when provider='auto')"""
        self.provider_choice = provider
        self.task_hint = task_hint
        self.ollama_model = None
        self.openrouter_key = None
        self.backend = self._resolve_backend()

    def _resolve_backend(self) -> Optional[str]:
        """Resolve which backend to use based on provider/task_hint and availability."""
        if self.provider_choice == "ollama":
            return self._try_ollama()
        if self.provider_choice == "gemini":
            return "gemini" if self._try_openrouter() else None
        if self.provider_choice == "kimi":
            return "kimi" if self._try_openrouter() else None

        # auto: build chain from task_hint
        if self.task_hint in ("agentic", "long_context"):
            chain = ["kimi", "gemini", "ollama"]
        else:  # chat
            chain = ["gemini", "kimi", "ollama"]

        for backend in chain:
            if backend in ("gemini", "kimi"):
                if self._try_openrouter():
                    return backend
            elif backend == "ollama":
                if self._try_ollama():
                    return "ollama"
        return None

    def _try_openrouter(self) -> bool:
        """Resolve OpenRouter key from env or 1Password. Returns True on success."""
        if self.openrouter_key:
            return True
        key = None
        if _op_load is not None:
            try:
                key = _op_load("OPENROUTER_API_KEY", OPENROUTER_OP_REF)
            except Exception as e:
                print(f"  op_loader: {e}")
                key = None
        if not key:
            key = os.getenv("OPENROUTER_API_KEY")
        if key:
            self.openrouter_key = key.strip()
            return True
        return False

    def _try_ollama(self) -> bool:
        """Probe local Ollama, pick a model. Returns True on success."""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                for preferred in ["qwen2.5:14b", "qwen2.5:7b", "llama3.2"]:
                    if any(preferred in m for m in models):
                        self.ollama_model = preferred
                        return True
                if models:
                    self.ollama_model = models[0]
                    return True
        except (requests.ConnectionError, requests.Timeout):
            pass
        return False

    def analyze(
        self,
        channel_messages: dict[str, str],
        role: str = None,
        team_context: str = None,
        server_name: str = None,
    ) -> list[dict]:
        """Analyze messages from multiple channels in one call."""
        if not self.backend:
            print("Error: No LLM available. Set OPENROUTER_API_KEY env or fix 1P op_loader, or start Ollama.")
            return []

        channel_blocks = ""
        for name, msgs in channel_messages.items():
            if msgs.strip():
                channel_blocks += f"\n--- #{name} ---\n{msgs}\n"

        if not channel_blocks.strip():
            return []

        effective_role = role
        if not effective_role:
            soul = load_soul(server_name)
            effective_role = soul if soul else DEFAULT_ROLE

        prompt = ANALYSIS_PROMPT.format(
            channel_blocks=channel_blocks,
            role=effective_role,
            team_context=team_context or DEFAULT_TEAM_CONTEXT,
        )

        if self.backend == "gemini":
            return self._call_openrouter(prompt, MODEL_GEMINI_FLASH)
        if self.backend == "kimi":
            return self._call_openrouter(prompt, MODEL_KIMI_K2)
        if self.backend == "ollama":
            return self._call_ollama(prompt)
        return []

    def _call_openrouter(self, prompt: str, model_id: str) -> list[dict]:
        """Call OpenRouter chat completions (OpenAI-compat)."""
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/arc-web/discord-manager",
                    "X-Title": "discord_manager",
                },
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 5000,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if os.getenv("LLM_DEBUG"):
                    print(f"\n--- raw {model_id} response ---\n{content}\n--- end ---\n")
                result = parse_analysis_json(content)
                return result.get("channels", [])
            print(f"OpenRouter error {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            print(f"OpenRouter error: {e}")
        return []

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
                timeout=600,
            )
            if resp.status_code == 200:
                result = parse_analysis_json(resp.json().get("response", ""))
                return result.get("channels", [])
        except Exception as e:
            print(f"Ollama error: {e}")
        return []
