<div align="center">

<a href="https://arc-web.github.io/discord-manager/">
  <img src="https://img.shields.io/badge/🎬_Interactive_Presentation-View_Live-7B2FBE?style=for-the-badge&labelColor=0F0F1A&color=7B2FBE" alt="View Interactive Presentation" />
</a>

</div>

---

# discord_manager

Local Discord management across multiple servers (arc, stackpack, conference).
Calls Discord REST API directly via per-server bot tokens. No VPS dependency.

## Files

- `discord.sh` - low-level CLI for raw Discord operations (send, read, edit, channels, members, etc.)
- `community_ops.py` - high-level CLI for audits, channel management, events, engagement
- `discord_report.py` - LLM-drafted channel scan with HITL approval before sending
- `discord_api.py` - thin Python REST client wrapping Discord API v10
- `llm_analyzer.py` - LLM provider chain (OpenRouter Gemini -> Kimi -> Ollama)
- `config_loader.py` - per-server credential resolution via 1Password op_loader
- `.env.1p.<server>` - per-server `op://` ref templates (no secrets, committable)
- `bot.env` - active bot token + guild config (chmod 600, never commit)
- `servers.json` - server registry
- `souls/<server>_soul.md` - per-server personality docs for LLM drafts

## Servers

| Name | Bot | Default? |
|------|-----|----------|
| arc | OpenClaw | yes |
| conference | claudeconference | no |
| stackpack | StackPack.app | no |

## Usage

### Low-level (discord.sh)

```bash
discord.sh -s arc send agents "Hello"
discord.sh -s stackpack read general 20
discord.sh -s arc channels
discord.sh -s arc whoami
discord.sh -s conference members
```

`discord.sh help` for the full command list.

### High-level (community_ops.py)

```bash
python3 community_ops.py audit activity --server arc --limit 7
python3 community_ops.py audit lurkers --server stackpack
python3 community_ops.py channels list --server arc
python3 community_ops.py engage shoutout @user "great work"
python3 community_ops.py event load events/conference.yaml
```

Full command reference in `CLAUDE.md`.

### Automated Report (discord_report.py)

Scans all channels with human activity, LLM-drafts responses, presents an approval list.

```bash
# Interactive (TTY)
python3 discord_report.py --server arc

# Headless (no stdin) - send specific items / all / none
python3 discord_report.py --server arc --approve "1,3"
python3 discord_report.py --server arc --approve all
python3 discord_report.py --server arc --dry-run

# Force a provider
python3 discord_report.py --server arc --provider gemini
python3 discord_report.py --server arc --provider kimi
python3 discord_report.py --server arc --provider ollama
```

Output:
```
[1] 🔴 #fdlxibalba - Erfan
    MSG:   "Hey man, what should I do next..."
    DRAFT: "Good work on tracking. Next step is..."
    ACTION: respond with next-step direction

Send which drafts? (1,3 / all / none): 1,3
```

## LLM Provider Chain

`llm_analyzer.py` resolves backends in order based on `task_hint`:

| task_hint | chain |
|-----------|-------|
| `chat` (default) | gemini -> kimi -> ollama |
| `agentic` / `long_context` | kimi -> gemini -> ollama |

Cloud calls go through OpenRouter (one key, two model IDs).

- `google/gemini-2.5-flash` - daily report primary, ~$0.01/run
- `moonshotai/kimi-k2.6` - agentic/long-context secondary, ~$0.02/run
- Ollama (`qwen2.5:14b`) - local fallback, free, slow

Anthropic excluded (Claude Code OAuth token is harness-only - 3rd-party use risks ban).

Credential resolution (first hit wins):
1. `OPENROUTER_API_KEY` env var
2. `op://Zeroclaw/<uuid>/credential` via shared op_loader

## Bot tokens

Per-server tokens stored in `bot.env` / `<server>.env`. Loaded via `config_loader.py` from 1Password `op://` refs in `.env.1p.<server>`. Tokens never live in committed files.

---

## Versions

**v1.1 - 2026-04-27**
- Repo renamed `discord_agent` -> `discord_manager`, moved to `~/ai/agents/comms/discord_manager/`
- Multi-server support (arc / stackpack / conference) via `--server` flag and per-server `.env.1p.*` templates
- LLM layer rewritten: OpenRouter unified key, Gemini Flash primary, Kimi K2.6 secondary, Ollama fallback. Anthropic dropped.
- `discord_report.py` headless flags: `--approve "1,3"|all|none`, `--dry-run`, `--provider`, `--task-hint`
- `community_ops.py` high-level CLI for audits, engagement, events, channels
- Per-server `souls/` for LLM personality

**v1.0 - 2026-03-30**
- `discord.sh` CLI (send, read, edit, delete, pin, react, threads, members, roles)
- `discord_api.py` REST client (Discord API v10)
- `discord_report.py` LLM scan + approval loop
- `llm_analyzer.py` Ollama-first / Anthropic fallback (deprecated in v1.1)
- `server_docs.md` server documentation
- Bot token in `bot.env`, no VPS

---

## What's Next

**Automation**
- Scheduled report - cron `discord_report.py` (morning digest, EOD sweep), push results to a summary channel
- Auto-responder rules - triggers (keywords, channels, authors) fire canned response without approval
- Alert routing - watch channels, ping Mike via DM when high-priority keywords appear ("urgent", "blocked", "not working")

**Member Activity**
- `member_activity.py` - most active, message %, last seen, response gaps, silent detection
- Engagement trends - week-over-week ramp/quiet detection
- Client health score - per-client rollup green/yellow/red on recency + volume

**Intelligence (Kimi long-context)**
- Thread summarizer - auto-summarize long threads into pinned TL;DR
- Unanswered question detector - scan messages ending in `?` with no reply, surface in report
- Sentiment tracking - flag tone shift / rising frustration
- Client brief generator - 30-day channel pull -> status brief (wins, blockers, next steps)

**Channel Management**
- Bulk archiver - identify zero-activity channels 30+ days, propose archive
- Template creator - spin up new client channel set (main + threads) from template
- Cross-channel search - keyword across all channels, return matches with context

**Integrations**
- n8n webhook - trigger reports / send messages from n8n workflows
- Airtable sync - log activity + member stats to Airtable
- Slack bridge - mirror critical alert channel to Slack

---

_Last updated: 2026-04-27_
