# ARC Formatting Style Guide

## Brand Color
`#1A1A2E` - dark navy, professional, agency
Decimal for embeds: `1710638`

## Plain Message Format

Status update:
```
STATUS EMOJI **[Project/Client] - Status**

What happened. One sentence.
Owner: @name
Next: action by date
```

Issue flag:
```
🔴 **[Client] - Issue: Short description**

What's broken or at risk.
Impact: who/what is affected
On it: @name
ETA: timeframe
```

Win post:
```
🟢 **[Client] - Result**

The metric or outcome.
What drove it.
Next move.
```

## Embed Format

Client update embed:
```json
{
  "title": "EMOJI Client Name - Update Type",
  "description": "The key result or status in one sentence.",
  "color": 1710638,
  "fields": [
    {"name": "WHAT HAPPENED", "value": "Brief context", "inline": false},
    {"name": "OWNER", "value": "@name", "inline": true},
    {"name": "NEXT ACTION", "value": "What happens next + when", "inline": true}
  ],
  "footer": {"text": "Advertising Report Card"}
}
```

## Status Emoji System

| Status | Emoji |
|--------|-------|
| Done / on track | 🟢 |
| In progress | 🟡 |
| Blocked / urgent | 🔴 |
| FYI / no action needed | ⚪ |
| Client-facing | 👤 |
| Internal only | 🔒 |

## Dos and Don'ts

DO:
- Always state the owner of an action
- Include a deadline or timeframe
- Lead with the result, not the activity
- Use the status emoji system consistently
- Keep client names in headers for easy scanning

DON'T:
- Use em dashes
- Report what you did without stating the outcome
- Leave next steps vague
- Use decorative emoji
- Write more than 3 sentences in a status update
