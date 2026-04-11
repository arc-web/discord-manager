# Claude Code Conference Formatting Style Guide

## Brand Color
`#5865F2` - Discord blurple, tech, official
Decimal for embeds: `5793266`

## Plain Message Format

Instructions (always numbered + code block):
```
EMOJI **Step title**

1. First action
2. Second action
   ```
   paste this command
   ```
3. Third action

If it works, you'll see X. Raise your hand.
```

Urgency messages:
```
🚨 **SHORT. CAPS. NO FLUFF.**

ONE LINE OF WHAT TO DO.
You have N minutes.
```

Status check:
```
📊 **Quick check - react with your status:**

✅ Done and working
⏳ In progress
❌ Blocked
🔴 Need help NOW
```

## Embed Format

Setup/instruction embed:
```json
{
  "title": "EMOJI Step N: What to Do",
  "description": "Context in one sentence. What this step achieves.",
  "color": 5793266,
  "fields": [
    {"name": "INSTRUCTIONS", "value": "Numbered steps here", "inline": false},
    {"name": "SUCCESS LOOKS LIKE", "value": "What you should see when it works", "inline": false}
  ],
  "footer": {"text": "Claude Code Conference"}
}
```

## Emoji Set

| Use | Emoji |
|-----|-------|
| Setup / install | 💻 |
| GitHub | 🐙 |
| API keys | 🔑 |
| Terminal | 🖥️ |
| Success / working | ✅ |
| In progress | ⏳ |
| Blocked | ❌ |
| Urgent / now | 🚨 |
| Presentation | 🎤 |
| QA / testing | 🔍 |
| UI / design | ✨ |
| Countdown | ⏱️ |
| Pod / team | 🎯 |

## Dos and Don'ts

DO:
- Put every command in a code block
- Number every multi-step process
- State the success condition explicitly
- Use CAPS for urgency (sparingly)
- @everyone only for time-critical moments

DON'T:
- Use em dashes
- Write instructions in paragraph form
- Leave out the success condition
- Use @everyone for regular updates
- Skip code blocks for commands
