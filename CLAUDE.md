# Discord Agent - Natural Language Interface

## How This Works

Mike speaks in plain English. I interpret intent and run the right tool.

**Rules:**
- Read-only requests (show me, who is, list, check) -> run immediately, report back
- Write actions (post, rename, move, set topic) -> confirm what I'm about to do, then run
- Destructive actions (delete channel, DM blast to everyone) -> always confirm explicitly before running
- When a server isn't specified, ask which one or default to the most recently discussed

**Working directory:** `~/aimacpro/4_agents/discord_agent/`
**Primary CLI:** `python3 community_ops.py <group> <action> --server <name>`
**Low-level CLI:** `bash discord.sh [-s <server>] <command>`
**Report tool:** `python3 discord_report.py [--server <name>]`

---

## Active Servers

| Name | Purpose | Bot | Target Flag |
|------|---------|-----|-------------|
| arc | ARC agency - internal team + client channels | OpenClaw | `--server arc` (default) |
| conference | Claude Code Conference - workshop server | claudeconference | `--server conference` |
| stackpack | StackPack.app community | StackPack.app | `--server stackpack` |

greenpenny server is coming - will follow the same pattern once bot is set up.

---

## Natural Language -> Tool Map

### Reading & Auditing

| What Mike says | What I run |
|----------------|-----------|
| "who's in [server]" / "show me the members" | `audit members --server X` |
| "who joined recently" / "newest members" | `audit members --server X` (sort by joined date) |
| "who's most active" / "check activity" | `audit activity --server X` |
| "who hasn't posted" / "who's lurking" / "quiet members" | `audit lurkers --server X` |
| "show me the channels" / "list channels" | `channels list --server X` |
| "which channels are dead" / "channel health" | `audit channels --server X` |
| "give me a full audit" / "server report" / "full picture" | `audit report --server X` (generates HTML, opens browser) |
| "read #general" / "what's been said in [channel]" | `discord.sh -s X read <channel> 20` |
| "check all channels for anything needing a response" | `python3 discord_report.py --server X` |
| "show me channel structure" / "how are channels organized" | `channels list --server X` |
| "who has what role" / "show roles" | `discord.sh -s X roles` |
| "server info" / "how many members" | `discord.sh -s X server-info` |
| "find [name]" / "search for [username]" | `discord.sh -s X member-search <query>` |
| "show permissions for [channel]" | `channels permissions <channel> --server X` |

### Posting & Messaging

| What Mike says | What I run |
|----------------|-----------|
| "post in [channel]: [message]" | `discord.sh -s X send <channel> "<message>"` |
| "send to all pods: [message]" | `discord.sh -s X broadcast pod-* "<message>"` |
| "post in general and all pods" | broadcast to `general,pod-*` |
| "DM [person]: [message]" | look up user ID via `search_members`, then `send_dm(user_id, message)` |
| "broadcast to everyone: [message]" | `discord.sh -s X broadcast <all channels> "<message>"` |
| "send a check-in" / "emoji poll" | `community_ops.py engage check-in` (requires active event) |
| "shoutout [person] for [reason]" | `community_ops.py engage shoutout <user> "<message>"` |
| "5 minute warning" / "countdown [N] minutes" | `community_ops.py engage countdown <N>` |
| "nudge people who haven't posted" | `community_ops.py engage nudge-silent` |

### Channel Management

| What Mike says | What I run |
|----------------|-----------|
| "rename [old] to [new]" | `channels rename <old> <new> --server X` |
| "set the topic of [channel] to [text]" | `channels topic <channel> "<text>" --server X` |
| "move [channel] to [category]" | `channels move <channel> <category> --server X` |
| "delete [channel]" | `channels delete <channel> --server X` (confirmation required) |
| "set up channels from this config" / scaffold | `channels scaffold <yaml> --server X` |
| "create a channel called [name]" | `discord_api.create_channel(name)` via python3 one-liner |

### Member & Roster Management

| What Mike says | What I run |
|----------------|-----------|
| "match this list against Discord" | `community_ops.py roster match <file>` |
| "who's in Discord but not on the roster" | `community_ops.py roster check` |
| "DM people who haven't joined Discord yet" | `community_ops.py roster nudge-missing` |

### Event / Workshop Mode

| What Mike says | What I run |
|----------------|-----------|
| "load the [event] config" | `community_ops.py event load events/<name>.yaml` |
| "event status" | `community_ops.py event status` |
| "assign pods" | `community_ops.py pods assign` |
| "rebalance pods for [N] people" | `community_ops.py pods rebalance --count <N>` |
| "post pod assignments" | `community_ops.py pods announce` |
| "post musical chairs / pod shuffle" | `community_ops.py pods musical-chairs` |
| "distribute API keys / credentials" | `community_ops.py it distribute-keys` |
| "post setup instructions" | `community_ops.py it setup-prompts` |
| "scan for errors / who is stuck" | `community_ops.py it scan-issues` then `it respond` |
| "post GitHub push prompts" | `community_ops.py dev push-prompts` |
| "post presentation prep" | `community_ops.py dev presentation-prep` |
| "post QA / stress test prompts" | `community_ops.py dev audit` |
| "run the schedule" | `community_ops.py schedule run` |

---

## Servers Deep Reference

### arc (default)
- ARC agency internal server
- Key channels: `general`, `alert`, `agents`, `agents-ops`, `agents-integrations`, `ai`, `ai-openclaw`
- Client channels: `co-moonraker-*`, `co-bpm-*`, `co-drivenstack-*`
- Bot: OpenClaw (bot.env)

### conference
- Claude Code Conference workshop server
- Key channels: `general`, `introductions`, `resources`, `pod-a` through `pod-f`
- Used for live events - full event ops mode
- Bot: claudeconference (conference.env)

### stackpack
- StackPack.app paid community server
- 20 members (16 human) as of 2026-04-11
- Bot: StackPack.app (stackpack.env)
- Channel structure (reorganized 2026-04-11):
  - COMMUNITY: `announcements`, `general`, `introductions`, `wins`
  - BUILDS & AGENTS: `showcase`, `help`, `collabs`, `resources`
  - TOOLS: `github-repos`, `claude-code`, `ai-tools`
  - AGEX: `agex-general`, `agex-tasks` (private - Mike + Hayley only, hidden from all other members)
- Known members and real names:
  - `advertisingreportcard` - Mike (949451361697804318)
  - `johannnn_0l` - Johan
  - `.camupton` - Cam Upton (392376655559131146)
  - `bentheautomator` - Ben
  - `sal.spoores` - Sal Torre
  - `hrconsult` - Helder (394699862693642250)
  - `ollyup` - Oliver (890329566181208107)
  - `tehmaal` - Tamal (491111269953175557)
  - `hb2503` - Hayley (804756980769751071)
  - `moonraker.ai` - Chris Morin
  - `cigarginger` - unknown
  - `tysonven` - unknown
  - `morgile` - unknown
  - `wsadmy7175` - unknown (山丂卂刀爪ㄚ)
  - `valiant_mango_24684` + `_oz_` - Oz (two accounts, situation unresolved)
- Bot: StackPack.app (stackpack.env)

---

## Complete Tool Reference

### community_ops.py

```
event load <yaml>               Load event config from YAML
event status                    Show active event

pods assign                     Assign roster to pods
pods rebalance [--count N]      Rebalance pods for N present members
pods announce                   Post assignments to pod channels
pods musical-chairs             Post pod shuffle announcement everywhere

roster check                    Check roster vs Discord members
roster nudge-missing            DM people on roster not yet in Discord
roster match <file>             Fuzzy match a names file against members

it setup-prompts                Post platform setup instructions to pods
it distribute-keys              Post API keys + PATs per pod
it scan-issues                  Scan channels for error messages
it respond                      Post known fixes for detected issues

dev push-prompts                Post GitHub push prompts to pods
dev test-access                 Post PAT test prompts to pods
dev presentation-prep           Post summary + NotebookLM prompts
dev clone-all                   Post clone-and-run prompts to general
dev audit                       Post QA stress-test prompts to pods

engage shoutout <user> <msg>    Shoutout a member everywhere
engage check-in                 Post emoji status poll to pods
engage nudge-silent             Ping/DM members who haven't posted
engage countdown <N>            Post N-minute warning everywhere

channels list [--server X]                      List all channels with categories/topics
channels rename <old> <new> [--server X]        Rename a channel
channels topic <ch> <text> [--server X]         Set channel topic
channels move <ch> <category> [--server X]      Move channel to category
channels delete <ch> [--server X]               Delete channel (confirm required)
channels scaffold <yaml> [--server X]           Create/update structure from YAML
channels permissions <ch> [--server X]          Show permission overrides

audit members [--server X] [--limit N]          Full member roster
audit activity [--server X] [--limit N]         Per-member message counts
audit channels [--server X] [--limit N]         Channel health stats
audit lurkers [--server X] [--limit N]          Members who never posted
audit report [--server X] [--limit N]           Full HTML report (opens browser)
```

### discord.sh

```
discord.sh [-s server] send <channel> <message>
discord.sh [-s server] read <channel> [limit]
discord.sh [-s server] broadcast <ch1,ch2,...|glob> <message>
discord.sh [-s server] broadcast-template <channels> <template_file> [VAR=val]
discord.sh [-s server] embed <channel> <json>
discord.sh [-s server] members [limit]
discord.sh [-s server] member-search <query>
discord.sh [-s server] roster-match <file>
discord.sh [-s server] channels
discord.sh [-s server] roles
discord.sh [-s server] server-info
discord.sh [-s server] react <channel> <msg_id> <emoji>
discord.sh [-s server] delete <channel> <msg_id>
discord.sh [-s server] edit <channel> <msg_id> <new_text>
discord.sh [-s server] pin <channel> <msg_id>
discord.sh [-s server] unpin <channel> <msg_id>
discord.sh [-s server] thread <channel> <msg_id> <thread_name>
discord.sh [-s server] threads <channel>
discord.sh [-s server] whoami
discord.sh [-s server] cache-channels
discord.sh servers
```

### discord_report.py

```
python3 discord_report.py [--server X]
```
Scans all channels for human activity, analyzes with LLM, shows draft responses for approval, sends approved ones.

---

## Workflow Examples

**"Who's not talking in StackPack?"**
1. `python3 community_ops.py audit lurkers --server stackpack`
2. Report back names, usernames, join dates

**"Rename the general channel to community"**
1. Confirm: "I'm going to rename #general to #community in StackPack - go ahead?"
2. `python3 community_ops.py channels rename general community --server stackpack`

**"Post a check-in to all pods for the conference"**
1. `python3 community_ops.py event status` (confirm conference is loaded)
2. `python3 community_ops.py engage check-in`

**"Check if anyone in StackPack needs a response"**
1. `python3 discord_report.py --server stackpack`
2. Show the draft responses, ask which to approve

**"DM Helder and ask him to say hi in his channel"**
1. `discord.sh -s stackpack member-search helder` -> get user ID for HRconsult
2. Confirm message text with Mike
3. `send_dm(user_id, message)` via python3 one-liner
