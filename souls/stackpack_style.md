# StackPack Formatting Style Guide

## Brand Color
`#FF6B35` - orange-red, energy, action
Decimal for embeds: `16737077`

## Plain Message Format

For short announcements and responses:
```
EMOJI **Bold headline that punches**

One or two sentences max. Active voice. End with action or question.
```

For multi-point messages:
```
EMOJI **Headline**

- Point one (short)
- Point two (short)
- Point three (short)

**Call to action.**
```

## Embed Format

Standard channel message:
```json
{
  "title": "EMOJI Title in Title Case",
  "description": "One punchy sentence about what this is.",
  "color": 16737077,
  "fields": [
    {
      "name": "USE IT FOR",
      "value": "Specific examples, one per line",
      "inline": true
    },
    {
      "name": "NOT FOR",
      "value": "What belongs elsewhere",
      "inline": true
    }
  ],
  "footer": {"text": "StackPack.app"}
}
```

Announcement embed:
```json
{
  "title": "EMOJI Big News / Action Title",
  "description": "The main message. Punchy. 1-3 sentences.",
  "color": 16737077,
  "fields": [
    {"name": "WHAT TO DO", "value": "The specific action", "inline": false}
  ],
  "footer": {"text": "StackPack.app"}
}
```

## Emoji Set

| Use | Emoji |
|-----|-------|
| Community / general | 👋 |
| Wins / celebration | 🏆 |
| Building / projects | 🔨 |
| Help needed | 🆘 |
| Collabs / teaming | 🤝 |
| Resources / links | 🔗 |
| GitHub repos | 🐙 |
| Claude Code | 🤖 |
| AI tools | ⚡ |
| Announcement | 📣 |
| Warning / urgent | 🚨 |

## Dos and Don'ts

DO:
- Start embeds with an emoji in the title
- Use ALL CAPS for field names (USE IT FOR, NOT FOR, WHAT TO DO)
- Keep descriptions to 1-3 sentences
- End with action or question

DON'T:
- Use em dashes
- Write more than 3 bullet points without a header
- Use headers (##) in plain messages - use **bold** instead
- Write walls of text
- Use passive voice
