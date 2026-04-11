"""GitHub operations - push prompts, test access, clone-all."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig
from event_ops.announcements import load_template, render_template, announce_to_pods


def _get_pod_github(event: EventConfig, pod_name: str) -> tuple[str, str]:
    """Get (github_pat, github_repo) for a pod from event credentials."""
    creds = event.credentials
    pat = creds.get("github_pats", {}).get(pod_name, "")
    repo = creds.get("github_repos", {}).get(pod_name, "")
    return pat, repo


def post_push_prompts(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post github_push.md to each pod with their PAT and repo."""
    template = load_template("github_push")
    pod_names = event.pods.get("names", [])
    results = {}

    for pod_name in pod_names:
        pat, repo = _get_pod_github(event, pod_name)
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)
        content = render_template(template, {
            "pod_name": pod_name,
            "pod_letter": pod_name.upper(),
            "github_pat": pat,
            "github_repo": repo,
            "event_name": event.name,
        })
        success = client.send_message(channel_id, content)
        results[channel_name] = success
        status = "sent" if success else "FAILED"
        print(f"  #{channel_name}: {status}")

    return results


def post_test_access_prompts(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post github_test_access.md to each pod with their PAT and repo."""
    template = load_template("github_test_access")
    pod_names = event.pods.get("names", [])
    results = {}

    for pod_name in pod_names:
        pat, repo = _get_pod_github(event, pod_name)
        repo_name = repo.split("/")[-1] if "/" in repo else repo
        channel_name = f"pod-{pod_name}"
        channel_id = client.resolve_channel(channel_name)
        content = render_template(template, {
            "pod_name": pod_name,
            "pod_letter": pod_name.upper(),
            "github_pat": pat,
            "github_repo": repo,
            "repo_name": repo_name,
            "event_name": event.name,
        })
        success = client.send_message(channel_id, content)
        results[channel_name] = success
        status = "sent" if success else "FAILED"
        print(f"  #{channel_name}: {status}")

    return results


def post_clone_all_prompts(client: DiscordClient, event: EventConfig) -> dict[str, bool]:
    """Post clone_and_run.md for every pod repo to general channel."""
    template = load_template("clone_and_run")
    pod_names = event.pods.get("names", [])
    repos = event.credentials.get("github_repos", {})
    results = {}
    general_id = client.resolve_channel("general")

    for pod_name in pod_names:
        repo = repos.get(pod_name, "")
        if not repo:
            continue
        project_name = repo.split("/")[-1] if "/" in repo else repo
        content = render_template(template, {
            "github_repo": repo,
            "project_name": project_name,
            "pod_name": pod_name,
            "pod_letter": pod_name.upper(),
        })
        success = client.send_message(general_id, content)
        results[pod_name] = success
        status = "sent" if success else "FAILED"
        print(f"  Pod {pod_name.upper()} clone prompt: {status}")

    return results


def generate_push_prompt(github_pat: str, github_repo: str) -> str:
    """Return a one-shot Claude Code prompt for pushing all work."""
    return (
        f"Push all my work to GitHub right now. "
        f"Use this token for authentication: {github_pat} "
        f"Target repo: https://github.com/{github_repo}.git "
        f"Add all files, commit with a descriptive message about what was built, "
        f"and push to main. If the repo doesn't have a remote set up, add it. "
        f"Don't ask questions, just push everything."
    )
