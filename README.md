# discord_agent

Local Discord management for the Advertising Report Card server.
Uses OpenClaw's bot token to call Discord REST API directly - no VPS dependency.

## Files

- `discord.sh` - CLI tool for all Discord operations (send, read, edit, channels, members, etc.)
- `bot.env` - Bot token and guild config (chmod 600, never commit)
- `server_docs.md` - Full server documentation (members, channels, categories, threads, timeline)
- `discord_report.py` - Automated channel report tool (scans all channels, drafts responses for approval)

## Usage

### Manual Commands (discord.sh)

```bash
# Via scripts alias
discord.sh send agents "Hello"
discord.sh read agents 5
discord.sh channels

# Direct
./discord.sh whoami
./discord.sh members
./discord.sh roles
```

Run `discord.sh help` for all commands and channel aliases.

### Automated Report (discord_report.py)

Scans all 25 channels, uses Claude to draft responses, presents approval list:

```bash
export ANTHROPIC_API_KEY='your-key'
python3 discord_report.py

# Or via wrapper script
discord-report
```

Channels scanned:
- Agents (5): agents, agents-ops, agents-integrations, agents-team, agents-business
- Clients (4): sfbayareamoving, fdlxibalba, proximahire, collabmedspa
- Co-managed (9): BPM, Moonraker, DrivenStack clients
- Team ops (5): general, alert, ai-openclaw, team-ppc, n8n-general

Output format:
```
[1] 🔴 fdlxibalba — Erfan asking what to do next
    MSG:  "Hey man, what should I do next..."
    DRAFT: "Good work on tracking. Next step is..."

Send which drafts? (e.g. '1,3' or 'all' or 'none'): 1,3
```

---

## Versions

**v1.0 - 2026-03-30**
- `discord.sh` CLI - full Discord operations from terminal (send, read, edit, delete, pin, react, threads, members, roles)
- `discord_api.py` - thin Python REST client wrapping Discord API v10
- `discord_report.py` - automated channel report: scans 25 channels, LLM-drafts responses, approval loop before sending
- `llm_analyzer.py` - Ollama-first LLM backend with Anthropic fallback, auto-discovers API keys
- `server_docs.md` - full server documentation (members, channels, categories, active threads, timeline)
- Bot token stored locally in `bot.env` - no VPS dependency

---

## What's Next

Ideas for making Discord management smarter and more automated:

**Automation**
- Scheduled report - run `discord_report.py` on a cron (morning digest, end-of-day sweep) and push results to a summary channel
- Auto-responder rules - define triggers (keywords, channels, authors) that fire a canned response without needing approval
- Alert routing - watch specific channels and ping Mike via DM or the alert channel when high-priority keywords appear (e.g. "urgent", "blocked", "not working")

**Member Activity**
- `member_activity.py` - who is most active, message % share per member, last seen timestamps, response gap alerts, silent member detection
- Engagement trends - week-over-week comparison showing who is ramping up or going quiet
- Client health score - per-client channel activity rolled up into a single status (green/yellow/red) based on recency and volume

**Intelligence**
- Thread summarizer - auto-summarize long threads into a TL;DR pinned at the top
- Unanswered question detector - scan for messages ending in `?` that never got a reply, surface them in the report
- Sentiment tracking - flag channels where tone has shifted negative or frustration is rising
- Client brief generator - pull the last 30 days of a client channel and generate a status brief (wins, blockers, next steps)

**Channel Management**
- Bulk channel archiver - identify channels with zero activity for 30+ days, propose archiving them
- Channel template creator - spin up a new client channel set (main + threads) from a standard template
- Cross-channel search - search a keyword across all channels at once and return matches with context

**Integrations**
- n8n webhook - trigger report runs or send messages from n8n workflows
- Airtable sync - log message activity and member stats to an Airtable base for tracking over time
- Slack bridge - mirror critical alert channel messages to a Slack workspace
