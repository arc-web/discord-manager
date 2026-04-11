"""Distributes API keys and GitHub PATs to pod channels."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from discord_api import DiscordClient
from event_config import EventConfig

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _load_template(name: str) -> str:
    """Load a template file by name."""
    return (TEMPLATES_DIR / name).read_text()


def _render(template: str, variables: dict) -> str:
    """Substitute {{key}} placeholders in a template string."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def distribute_api_keys(client: DiscordClient, event: EventConfig) -> None:
    """Post api_key_setup template to each pod channel with the pod's key."""
    template = _load_template("api_key_setup.md")
    api_keys = event.credentials.get("api_keys", {})
    pod_names = event.pods.get("names", [])

    for pod in pod_names:
        key = api_keys.get(pod) or api_keys.get(f"pod_{pod}", "API_KEY_NOT_SET")
        channel_id = client.resolve_channel(pod)
        message = _render(template, {"pod_letter": pod, "api_key": key})
        client.send_message(channel_id, message)
        print(f"Distributed API key to pod {pod}")


def distribute_github_pats(client: DiscordClient, event: EventConfig) -> None:
    """Post github_push and github_test_access templates to each pod channel."""
    push_template = _load_template("github_push.md")
    test_template = _load_template("github_test_access.md")
    github_pats = event.credentials.get("github_pats", {})
    github_repos = event.credentials.get("github_repos", {})
    pod_names = event.pods.get("names", [])

    for pod in pod_names:
        pat = github_pats.get(pod) or github_pats.get(f"pod_{pod}", "PAT_NOT_SET")
        repo = github_repos.get(pod) or github_repos.get(f"pod_{pod}", f"org/pod-{pod}")
        repo_name = repo.split("/")[-1] if "/" in repo else repo
        channel_id = client.resolve_channel(pod)

        variables = {
            "pod_letter": pod,
            "github_pat": pat,
            "github_repo": repo,
            "repo_name": repo_name,
        }

        # Post push instructions
        push_msg = _render(push_template, variables)
        client.send_message(channel_id, push_msg)

        # Post test access instructions
        test_msg = _render(test_template, variables)
        client.send_message(channel_id, test_msg)

        print(f"Distributed GitHub PAT to pod {pod}")


def distribute_all(client: DiscordClient, event: EventConfig) -> None:
    """Run both API key and GitHub PAT distribution."""
    distribute_api_keys(client, event)
    if event.credentials.get("github_pats"):
        distribute_github_pats(client, event)
