# 💻 Windows Setup - Step by Step

**Step 1: Open your terminal**
1. Press the **Windows key** on your keyboard (bottom left, has the Windows logo)
2. Type **powershell**
3. Click **Windows PowerShell** when it appears

**Step 2: Install Claude Code**
```
irm https://claude.ai/install.ps1 | iex
```
Wait for it to finish.

**Step 3: Add Claude to your path**
```
$env:Path += ";$env:USERPROFILE\.local\bin"
```

**Step 4: Set your API key**
```
$env:ANTHROPIC_API_KEY="{{api_key}}"
```

**Step 5: Start Claude Code**
```
claude
```

If Claude responds, you're in! Raise your hand.
