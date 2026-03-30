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
