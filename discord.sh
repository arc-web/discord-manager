#!/bin/bash
# discord.sh - Multi-server Discord management CLI
# Usage: discord.sh [-s server] <command> [args...]
#
# Server selection:
#   -s, --server <name>    Use named server from servers.json (default: from config)
#
# Commands:
#   send <channel> <message>             - Send a text message
#   embed <channel> <json>               - Send an embed (JSON string)
#   channels                             - List guild channels
#   read <channel> [limit]               - Read recent messages (default: 10)
#   threads <channel>                    - List active threads
#   react <channel> <msg_id> <emoji>     - Add reaction
#   delete <channel> <msg_id>            - Delete a message
#   edit <channel> <msg_id> <text>       - Edit a message
#   pin <channel> <msg_id>               - Pin a message
#   unpin <channel> <msg_id>             - Unpin a message
#   thread <channel> <msg_id> <name>     - Create thread from message
#   whoami                               - Show bot info
#   members [limit]                      - List guild members
#   roles                                - List guild roles
#   server-info                          - Show guild name, member count, permissions
#   broadcast <ch1,ch2,...> <message>     - Send to multiple channels (supports globs like pod-*)
#   broadcast-template <ch1,...> <file> [VAR=val ...] - Templated broadcast
#   member-search <query>                - Fuzzy search members by name
#   roster-match <file>                  - Match names file against server members
#   cache-channels                       - Fetch and cache channel list
#   servers                              - List available servers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse --server flag
SERVER_NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--server)
      SERVER_NAME="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# Load config via python helper
_load_config() {
  local server_arg="${SERVER_NAME:-}"
  local config_output
  config_output=$(python3 - "$SCRIPT_DIR" "$server_arg" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from config_loader import load_server_config
server = sys.argv[2] if sys.argv[2] else None
c = load_server_config(server)
print(f'DISCORD_BOT_TOKEN={c["token"]}')
print(f'DISCORD_GUILD_ID={c["guild_id"]}')
print(f'DISCORD_BOT_ID={c["bot_id"]}')
print(f'SERVER_LABEL={c["name"]}')
PYEOF
  ) || {
    echo "Error loading server config" >&2
    exit 1
  }
  eval "$config_output"
}

_load_config

API_BASE="https://discord.com/api/v10"

# Resolve channel alias to ID using python config
resolve_channel() {
  local channel_name="$1"
  local server_arg="${SERVER_NAME:-}"
  python3 - "$SCRIPT_DIR" "$server_arg" "$channel_name" <<'PYEOF'
import sys, json, pathlib
sys.path.insert(0, sys.argv[1])
from config_loader import load_server_config
server = sys.argv[2] if sys.argv[2] else None
name = sys.argv[3]
config = load_server_config(server)
aliases = config.get('aliases', {})
if name in aliases:
    print(aliases[name])
else:
    cache = pathlib.Path(sys.argv[1]) / '.cache' / f'{config["name"]}_channels.json'
    if cache.exists():
        channels = json.loads(cache.read_text())
        if name in channels:
            print(channels[name])
            sys.exit(0)
    print(name)
PYEOF
}

# Resolve glob pattern to channel IDs
resolve_channels_glob() {
  local pattern="$1"
  local server_arg="${SERVER_NAME:-}"
  python3 - "$SCRIPT_DIR" "$server_arg" "$pattern" <<'PYEOF'
import sys, json, fnmatch, pathlib
sys.path.insert(0, sys.argv[1])
from config_loader import load_server_config
server = sys.argv[2] if sys.argv[2] else None
pattern = sys.argv[3]
config = load_server_config(server)
aliases = config.get('aliases', {})
cache_file = pathlib.Path(sys.argv[1]) / '.cache' / f'{config["name"]}_channels.json'
discovered = json.loads(cache_file.read_text()) if cache_file.exists() else {}
all_channels = {**discovered, **aliases}
parts = pattern.split(',') if ',' in pattern else [pattern]
results = []
for p in parts:
    p = p.strip()
    if '*' in p or '?' in p:
        for name, cid in all_channels.items():
            if fnmatch.fnmatch(name, p):
                results.append(f'{name}:{cid}')
    elif p in all_channels:
        results.append(f'{p}:{all_channels[p]}')
    else:
        results.append(f'{p}:{p}')
for r in results:
    print(r)
PYEOF
}

# Direct curl to Discord API
discord_api() {
  local method="$1" endpoint="$2"
  shift 2
  curl -s -X "$method" \
    -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    "$@" \
    "${API_BASE}${endpoint}"
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  send)
    channel=$(resolve_channel "${1:?channel required}")
    message="${2:?message required}"
    payload=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$message")
    discord_api POST "/channels/$channel/messages" -d "$payload"
    ;;

  embed)
    channel=$(resolve_channel "${1:?channel required}")
    embed_json="${2:?embed JSON required}"
    discord_api POST "/channels/$channel/messages" -d "{\"embeds\": [$embed_json]}"
    ;;

  channels)
    discord_api GET "/guilds/$DISCORD_GUILD_ID/channels" | \
      python3 -c "
import sys,json
channels=json.load(sys.stdin)
types={0:'text',2:'voice',4:'category',5:'announce',15:'forum'}
for c in sorted(channels, key=lambda x: (x.get('position',0))):
  t=types.get(c['type'],str(c['type']))
  print(f'{c[\"id\"]:>22} | {t:>8} | {c.get(\"name\",\"\")}')
"
    ;;

  read)
    channel=$(resolve_channel "${1:?channel required}")
    limit="${2:-10}"
    discord_api GET "/channels/$channel/messages?limit=$limit" | \
      python3 -c "
import sys,json
msgs=json.load(sys.stdin)
for m in reversed(msgs):
  author=m['author'].get('global_name') or m['author']['username']
  content=m.get('content','')[:200]
  ts=m['timestamp'][:19]
  embeds=f' [{len(m.get(\"embeds\",[]))} embeds]' if m.get('embeds') else ''
  print(f'[{ts}] {author}: {content}{embeds}')
"
    ;;

  threads)
    channel=$(resolve_channel "${1:?channel required}")
    discord_api GET "/guilds/$DISCORD_GUILD_ID/threads/active" | \
      python3 -c "
import sys,json
data=json.load(sys.stdin)
ch='$channel'
threads=data.get('threads',[])
for t in threads:
  if t.get('parent_id') == ch or ch == 'all':
    print(f'{t[\"id\"]:>22} | {t.get(\"name\",\"\")} | msgs: {t.get(\"message_count\",\"?\")}')
"
    ;;

  react)
    channel=$(resolve_channel "${1:?channel required}")
    msg_id="${2:?message_id required}"
    emoji="${3:?emoji required}"
    encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$emoji'))")
    discord_api PUT "/channels/$channel/messages/$msg_id/reactions/$encoded/@me"
    ;;

  delete)
    channel=$(resolve_channel "${1:?channel required}")
    msg_id="${2:?message_id required}"
    discord_api DELETE "/channels/$channel/messages/$msg_id"
    ;;

  edit)
    channel=$(resolve_channel "${1:?channel required}")
    msg_id="${2:?message_id required}"
    text="${3:?text required}"
    payload=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$text")
    discord_api PATCH "/channels/$channel/messages/$msg_id" -d "$payload"
    ;;

  pin)
    channel=$(resolve_channel "${1:?channel required}")
    msg_id="${2:?message_id required}"
    discord_api PUT "/channels/$channel/pins/$msg_id"
    ;;

  unpin)
    channel=$(resolve_channel "${1:?channel required}")
    msg_id="${2:?message_id required}"
    discord_api DELETE "/channels/$channel/pins/$msg_id"
    ;;

  thread)
    channel=$(resolve_channel "${1:?channel required}")
    msg_id="${2:?message_id required}"
    name="${3:?thread name required}"
    payload=$(python3 -c "import json,sys; print(json.dumps({'name': sys.argv[1]}))" "$name")
    discord_api POST "/channels/$channel/messages/$msg_id/threads" -d "$payload"
    ;;

  whoami)
    discord_api GET "/users/@me" | python3 -c "
import sys,json
u=json.load(sys.stdin)
print(f'Server: $SERVER_LABEL')
print(f'Bot: {u[\"username\"]}#{u[\"discriminator\"]}')
print(f'ID:  {u[\"id\"]}')
"
    ;;

  members)
    limit="${1:-20}"
    discord_api GET "/guilds/$DISCORD_GUILD_ID/members?limit=$limit" | \
      python3 -c "
import sys,json
members=json.load(sys.stdin)
for m in members:
  u=m['user']
  name=u.get('global_name') or u['username']
  bot='[BOT] ' if u.get('bot') else ''
  print(f'{u[\"id\"]:>22} | {bot}{name} (@{u[\"username\"]})')
"
    ;;

  roles)
    discord_api GET "/guilds/$DISCORD_GUILD_ID/roles" | \
      python3 -c "
import sys,json
roles=json.load(sys.stdin)
for r in sorted(roles, key=lambda x: -x['position']):
  print(f'{r[\"id\"]:>22} | pos {r[\"position\"]:>2} | {r[\"name\"]}')
"
    ;;

  server-info)
    discord_api GET "/guilds/$DISCORD_GUILD_ID?with_counts=true" | \
      python3 -c "
import sys,json
g=json.load(sys.stdin)
print(f'Server: {g[\"name\"]}')
print(f'ID: {g[\"id\"]}')
print(f'Owner: {g.get(\"owner_id\",\"?\")}')
print(f'Members: {g.get(\"approximate_member_count\",\"?\")} ({g.get(\"approximate_presence_count\",\"?\")} online)')
print(f'Boost Level: {g.get(\"premium_tier\",0)}')
print(f'Channels: checking...')
" && discord_api GET "/guilds/$DISCORD_GUILD_ID/channels" | \
      python3 -c "
import sys,json
channels=json.load(sys.stdin)
types={0:'text',2:'voice',4:'category',5:'announce',15:'forum'}
counts={}
for c in channels:
  t=types.get(c['type'],'other')
  counts[t]=counts.get(t,0)+1
for t,n in sorted(counts.items()):
  print(f'  {t}: {n}')
"
    ;;

  broadcast)
    targets="${1:?channels required (comma-separated or glob)}"
    message="${2:?message required}"
    payload=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$message")
    while IFS=: read -r name cid; do
      echo -n "  Sending to #$name... "
      result=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "${API_BASE}/channels/$cid/messages")
      if [[ "$result" == "200" ]]; then
        echo "sent"
      else
        echo "FAILED ($result)"
      fi
      sleep 0.3
    done < <(resolve_channels_glob "$targets")
    ;;

  broadcast-template)
    targets="${1:?channels required}"
    template_file="${2:?template file required}"
    shift 2
    if [[ ! -f "$template_file" ]]; then
      echo "Error: template file not found: $template_file" >&2
      exit 1
    fi
    template=$(cat "$template_file")
    # Collect VAR=val pairs
    vars_json="{}"
    for arg in "$@"; do
      if [[ "$arg" == *=* ]]; then
        key="${arg%%=*}"
        val="${arg#*=}"
        vars_json=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]=sys.argv[3]; print(json.dumps(d))" "$vars_json" "$key" "$val")
      fi
    done
    while IFS=: read -r name cid; do
      # Substitute variables + {{channel}}
      content=$(python3 -c "
import json,sys
template=sys.argv[1]
variables=json.loads(sys.argv[2])
variables['channel']=sys.argv[3]
for k,v in variables.items():
    template=template.replace('{{'+k+'}}',v)
print(template)
" "$template" "$vars_json" "$name")
      payload=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$content")
      echo -n "  Sending to #$name... "
      result=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "${API_BASE}/channels/$cid/messages")
      if [[ "$result" == "200" ]]; then
        echo "sent"
      else
        echo "FAILED ($result)"
      fi
      sleep 0.3
    done < <(resolve_channels_glob "$targets")
    ;;

  member-search)
    query="${1:?search query required}"
    python3 - "$SCRIPT_DIR" "${SERVER_NAME:-}" "$query" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from discord_api import DiscordClient
server = sys.argv[2] if sys.argv[2] else None
client = DiscordClient(server_name=server)
results = client.search_members(sys.argv[3])
if not results:
    print('No matches found.')
else:
    for m in results:
        u = m['user']
        display = m.get('nick') or u.get('global_name') or u['username']
        bot = ' [BOT]' if u.get('bot') else ''
        print(f'{u["id"]:>22} | {display} (@{u["username"]}){bot}')
PYEOF
    ;;

  roster-match)
    file="${1:?names file required}"
    if [[ ! -f "$file" ]]; then
      echo "Error: file not found: $file" >&2
      exit 1
    fi
    python3 - "$SCRIPT_DIR" "${SERVER_NAME:-}" "$file" <<'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[1])
from discord_api import DiscordClient
server = sys.argv[2] if sys.argv[2] else None
client = DiscordClient(server_name=server)
with open(sys.argv[3]) as f:
    names = [line.strip() for line in f if line.strip()]
result = client.roster_match(names)
print(f'MATCHED ({len(result["matched"])}):')
for m in result['matched']:
    fuzzy = ' (fuzzy)' if m.get('fuzzy') else ''
    print(f'  {m["roster_name"]} -> {m["display_name"]} (@{m["username"]}, ID: {m["id"]}){fuzzy}')
print(f'\nUNMATCHED ({len(result["unmatched"])}):')
for name in result['unmatched']:
    suggestions = result['suggestions'].get(name, [])
    hint = f' (did you mean: {", ".join(suggestions)})' if suggestions else ''
    print(f'  {name}{hint}')
PYEOF
    ;;

  cache-channels)
    mkdir -p "$SCRIPT_DIR/.cache"
    discord_api GET "/guilds/$DISCORD_GUILD_ID/channels" | \
      python3 -c "
import sys,json
channels=json.load(sys.stdin)
result={c['name']:c['id'] for c in channels if c.get('name')}
cache_path='$SCRIPT_DIR/.cache/${SERVER_LABEL}_channels.json'
with open(cache_path,'w') as f:
    json.dump(result,f,indent=2)
print(f'Cached {len(result)} channels to {cache_path}')
"
    ;;

  servers)
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from config_loader import list_servers, load_server_config
import json
servers_file = '$SCRIPT_DIR/servers.json'
try:
    with open(servers_file) as f:
        config = json.load(f)
    default = config.get('default', '')
    for name in config['servers']:
        marker = ' (default)' if name == default else ''
        s = config['servers'][name]
        print(f'  {name}{marker} - guild: {s.get(\"guild_id\",\"?\")} - env: {s.get(\"env_file\",\"?\")}')
except FileNotFoundError:
    print('  No servers.json found. Using legacy bot.env.')
"
    ;;

  help|*)
    echo "discord.sh - Multi-server Discord management CLI"
    echo ""
    echo "Usage: discord.sh [-s server] <command> [args...]"
    echo ""
    echo "Server selection:"
    echo "  -s, --server <name>   Use named server (default: from servers.json)"
    echo "  servers               List available servers"
    echo ""
    echo "Message commands:"
    echo "  send <channel> <message>          Send a text message"
    echo "  embed <channel> <json>            Send embed (raw JSON)"
    echo "  edit <channel> <msg_id> <text>    Edit a message"
    echo "  delete <channel> <msg_id>         Delete a message"
    echo "  react <channel> <msg_id> <emoji>  Add reaction"
    echo "  pin <channel> <msg_id>            Pin a message"
    echo "  unpin <channel> <msg_id>          Unpin a message"
    echo ""
    echo "Read commands:"
    echo "  read <channel> [limit]            Read recent messages"
    echo "  channels                          List guild channels"
    echo "  threads <channel>                 List active threads"
    echo ""
    echo "Broadcast commands:"
    echo "  broadcast <ch1,ch2,...> <msg>      Send to multiple channels"
    echo "  broadcast-template <ch,...> <file> [VAR=val ...]"
    echo "                                    Templated broadcast"
    echo ""
    echo "Member commands:"
    echo "  members [limit]                   List guild members"
    echo "  member-search <query>             Fuzzy search members"
    echo "  roster-match <file>               Match names file vs members"
    echo ""
    echo "Info commands:"
    echo "  whoami                            Show bot info"
    echo "  roles                             List guild roles"
    echo "  server-info                       Show guild details"
    echo "  cache-channels                    Cache channel list"
    echo ""
    echo "Examples:"
    echo "  discord.sh send agents 'Hello!'           # ARC default"
    echo "  discord.sh -s conference channels          # Conference server"
    echo "  discord.sh -s conference broadcast 'pod-*' 'Hello pods!'"
    echo "  discord.sh -s conference member-search 'Cris'"
    ;;
esac
