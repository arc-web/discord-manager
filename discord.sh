#!/bin/bash
# discord.sh - Manage Discord via OpenClaw's bot token (local, no SSH needed)
# Token stored in ~/.config/discord/bot.env
# Usage: discord.sh <command> [args...]
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

set -euo pipefail

# Load token - check agent dir first, then fallback
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/bot.env"
if [[ ! -f "$ENV_FILE" ]]; then
  ENV_FILE="$HOME/.config/discord/bot.env"
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: bot.env not found in $SCRIPT_DIR or ~/.config/discord/" >&2
  exit 1
fi
source "$ENV_FILE"

API_BASE="https://discord.com/api/v10"

# Resolve channel alias to ID
resolve_channel() {
  case "$1" in
    agents)              echo "1475741313956843643" ;;
    agents-ops)          echo "1485448423225167892" ;;
    agents-integrations) echo "1485448423175098398" ;;
    agents-team)         echo "1485448423401459893" ;;
    agents-business)     echo "1485448423527419964" ;;
    alert)               echo "1477586864926883961" ;;
    general)             echo "1264976266084352205" ;;
    ai)                  echo "1478284164250865777" ;;
    ai-openclaw)         echo "1478284164993388726" ;;
    sfbayareamoving)     echo "1478284209423384657" ;;
    fdlxibalba)          echo "1478284208052113509" ;;
    proximahire)         echo "1478284208764882965" ;;
    collabmedspa)        echo "1478284207498334228" ;;
    *)                   echo "$1" ;;
  esac
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
  print(f'{u[\"id\"]:>22} | {bot}{name}')
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

  help|*)
    echo "discord.sh - Discord management via OpenClaw bot token (local)"
    echo ""
    echo "Commands:"
    echo "  send <channel> <message>          Send a text message"
    echo "  embed <channel> <json>            Send embed (raw JSON)"
    echo "  channels                          List guild channels"
    echo "  read <channel> [limit]            Read recent messages"
    echo "  threads <channel>                 List active threads"
    echo "  react <channel> <msg_id> <emoji>  Add reaction"
    echo "  delete <channel> <msg_id>         Delete a message"
    echo "  edit <channel> <msg_id> <text>    Edit a message"
    echo "  pin <channel> <msg_id>            Pin a message"
    echo "  unpin <channel> <msg_id>          Unpin a message"
    echo "  thread <channel> <msg_id> <name>  Create thread from message"
    echo "  whoami                            Show bot info"
    echo "  members [limit]                   List guild members"
    echo "  roles                             List guild roles"
    echo ""
    echo "Channel aliases:"
    echo "  Agents: agents agents-ops agents-integrations agents-team agents-business"
    echo "  Team: alert general ai ai-openclaw"
    echo "  Clients: sfbayareamoving fdlxibalba proximahire collabmedspa"
    echo ""
    echo "Examples:"
    echo "  discord.sh send agents 'Hello!'"
    echo "  discord.sh read agents 5"
    echo "  discord.sh channels"
    ;;
esac
