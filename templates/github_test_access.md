# 🐙 Pod {{pod_letter}} - Test Your GitHub Access

Paste this into Claude Code:

```
I need you to test that we have full access to our pod GitHub repo. Do all of this without asking me any questions:

1. Set up git credentials using this token: {{github_pat}}
2. Clone https://github.com/{{github_repo}}.git to a folder on my Desktop called {{repo_name}}
3. Go into that folder
4. Create a small test file called test-access.txt that says "Pod {{pod_letter}} connected successfully"
5. Add it, commit it, and push it to main
6. Then delete the test file, commit that, and push again
7. Tell me if everything worked

If anything fails, show me the exact error and try to fix it. Don't ask me questions, just make it work.
```
