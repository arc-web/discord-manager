# 🐙 Pod {{pod_letter}} - Push Your Work to GitHub

Paste this into Claude Code:

```
I need you to push all my work to our pod GitHub repo. Here's the info:

- Repo URL: https://github.com/{{github_repo}}.git
- GitHub token: {{github_pat}}

Please:
1. Set the remote to use this token for authentication
2. Add all my files
3. Commit with a message describing what we built
4. Push everything to the main branch
5. Confirm it worked and show me the repo URL

If there are any errors, fix them and try again. Don't ask me questions, just make it work.
```
