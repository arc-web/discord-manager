"""
review_gate.py - HITL review gate via Discord emoji reactions.

Posts a review card to #agency-automation, adds ✅/✏️/❌ reactions,
polls until a human reacts, and records the decision in Supabase.

Usage:
    from review_gate import ReviewGate

    gate = ReviewGate(server="arc")
    result = gate.ask(
        run_id="<uuid>",
        gate_name="lp_review",
        title="Landing Page Ready for Review",
        description="Preview the draft before it goes to the client.",
        fields={
            "Client": "nycmindfulmentalhealth.com",
            "Preview URL": "https://preview-slug.pages.dev",
            "Price": "$497",
        },
    )
    # result = {"decision": "approve"|"revise"|"reject", "notes": "", "run_id": ...}
"""

import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_server_config

API_BASE = "https://discord.com/api/v10"
SUPABASE_TABLE = "agency_runs"

# Emoji constants
EMOJI_APPROVE = "✅"
EMOJI_REVISE = "✏️"
EMOJI_REJECT = "❌"

REACTION_MAP = {
    EMOJI_APPROVE: "approve",
    EMOJI_REVISE: "revise",
    EMOJI_REJECT: "reject",
}

GATE_COLOR = {
    "lp_review": 0x5865F2,
    "proposal_review": 0x57F287,
    "stripe_review": 0xFEE75C,
    "email_review": 0xEB459E,
    "ad_diff_review": 0xED4245,
}


class ReviewGate:
    def __init__(self, server: str = "arc"):
        config = load_server_config(server)
        self.token = config["token"]
        self.guild_id = config["guild_id"]
        self.bot_id = config["bot_id"]
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }
        self._channel_id: Optional[str] = None

    # -- Channel setup --

    def _ensure_channel(self) -> str:
        if self._channel_id:
            return self._channel_id
        # Try to find existing channel
        resp = requests.get(
            f"{API_BASE}/guilds/{self.guild_id}/channels",
            headers=self.headers,
            timeout=10,
        )
        if resp.status_code == 200:
            for ch in resp.json():
                if ch.get("name") == "agency-automation":
                    self._channel_id = ch["id"]
                    return self._channel_id
        # Create it
        resp = requests.post(
            f"{API_BASE}/guilds/{self.guild_id}/channels",
            headers=self.headers,
            json={"name": "agency-automation", "type": 0, "topic": "Agency automation review gates - HITL approvals"},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            self._channel_id = resp.json()["id"]
            return self._channel_id
        raise RuntimeError(f"Could not find or create #agency-automation: {resp.status_code} {resp.text}")

    # -- Core --

    def ask(
        self,
        run_id: str,
        gate_name: str,
        title: str,
        description: str,
        fields: dict,
        poll_interval: int = 30,
        timeout_hours: int = 24,
    ) -> dict:
        """Post a review card, poll for emoji reaction, return decision dict."""
        channel_id = self._ensure_channel()

        # Build embed
        embed_fields = [{"name": k, "value": str(v)[:1024], "inline": False} for k, v in fields.items()]
        embed_fields.append({
            "name": "Decision",
            "value": f"{EMOJI_APPROVE} Approve   {EMOJI_REVISE} Revise   {EMOJI_REJECT} Reject",
            "inline": False,
        })
        color = GATE_COLOR.get(gate_name, 0x5865F2)

        payload = {
            "embeds": [{
                "title": title[:256],
                "description": description[:4096],
                "color": color,
                "fields": embed_fields,
                "footer": {"text": f"run_id: {run_id} | gate: {gate_name}"},
            }]
        }

        # Post embed
        resp = requests.post(
            f"{API_BASE}/channels/{channel_id}/messages",
            headers=self.headers,
            json=payload,
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to post review card: {resp.status_code} {resp.text}")

        message_id = resp.json()["id"]
        print(f"[review_gate] Posted gate '{gate_name}' for run {run_id} (msg {message_id})")

        # Add reactions
        for emoji in [EMOJI_APPROVE, EMOJI_REVISE, EMOJI_REJECT]:
            self._add_reaction(channel_id, message_id, emoji)
            time.sleep(0.5)

        # Poll for human response
        deadline = time.time() + timeout_hours * 3600
        while time.time() < deadline:
            decision, reactor_id = self._check_reactions(channel_id, message_id)
            if decision:
                result = {
                    "decision": decision,
                    "run_id": run_id,
                    "gate_name": gate_name,
                    "reactor_id": reactor_id,
                    "notes": "",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                self._record_approval(run_id, gate_name, result)
                print(f"[review_gate] Decision: {decision} by user {reactor_id}")
                return result
            print(f"[review_gate] Waiting for response on '{gate_name}'... ({int((deadline - time.time())/3600):.0f}h left)")
            time.sleep(poll_interval)

        result = {
            "decision": "timeout",
            "run_id": run_id,
            "gate_name": gate_name,
            "reactor_id": None,
            "notes": "No response within timeout window",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._record_approval(run_id, gate_name, result)
        return result

    # -- Helpers --

    def _add_reaction(self, channel_id: str, message_id: str, emoji: str) -> None:
        encoded = urllib.parse.quote(emoji)
        requests.put(
            f"{API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded}/@me",
            headers={k: v for k, v in self.headers.items() if k != "Content-Type"},
            timeout=10,
        )

    def _check_reactions(self, channel_id: str, message_id: str) -> tuple[Optional[str], Optional[str]]:
        """Check each reaction emoji for a non-bot user. Returns (decision, user_id) or (None, None)."""
        for emoji, decision in REACTION_MAP.items():
            encoded = urllib.parse.quote(emoji)
            resp = requests.get(
                f"{API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{encoded}",
                headers=self.headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            for user in resp.json():
                if not user.get("bot") and user.get("id") != self.bot_id:
                    return decision, user["id"]
        return None, None

    def _record_approval(self, run_id: str, gate_name: str, result: dict) -> None:
        """Append the gate result to agency_runs.approvals in Supabase."""
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            # Try op_loader if available
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aimacpro/7_tools/credentials"))
                from op_loader import load
                supabase_url = load("SUPABASE_URL")
                supabase_key = load("SUPABASE_SERVICE_ROLE_KEY")
            except Exception:
                print(f"[review_gate] WARNING: Supabase creds not available, skipping DB write. Result: {result}")
                return

        # Append approval to the JSONB array via Supabase RPC or raw SQL approach
        # Use the REST API append pattern: fetch current -> append -> patch
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        patch_resp = requests.patch(
            f"{supabase_url}/rest/v1/{SUPABASE_TABLE}?run_id=eq.{run_id}",
            headers=headers,
            json={"approvals": requests.get(
                f"{supabase_url}/rest/v1/{SUPABASE_TABLE}?run_id=eq.{run_id}&select=approvals",
                headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
                timeout=10,
            ).json()[0].get("approvals", []) + [result]},
            timeout=10,
        )
        if patch_resp.status_code not in (200, 204):
            print(f"[review_gate] WARNING: Supabase write failed: {patch_resp.status_code} {patch_resp.text}")
        else:
            print(f"[review_gate] Recorded gate '{gate_name}' in Supabase for run {run_id}")


# -- CLI for testing --

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post a test review gate")
    parser.add_argument("--run-id", default="test-run-001")
    parser.add_argument("--gate", default="lp_review")
    parser.add_argument("--server", default="arc")
    parser.add_argument("--poll", type=int, default=15, help="Poll interval seconds")
    args = parser.parse_args()

    gate = ReviewGate(server=args.server)
    result = gate.ask(
        run_id=args.run_id,
        gate_name=args.gate,
        title="TEST: Landing Page Ready for Review",
        description="This is a test gate. React with an emoji to confirm the review gate works end-to-end.",
        fields={
            "Client": "testclient.com",
            "Preview URL": "https://preview-test.pages.dev",
            "Price": "$497",
            "Notes": "Inline CSS, Custom Code block for GHL Funnels",
        },
        poll_interval=args.poll,
        timeout_hours=1,
    )
    print(json.dumps(result, indent=2))
