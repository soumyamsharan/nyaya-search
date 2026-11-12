"""Publish to Hugging Face (free): the database dump as a dataset repo, the API as a Docker Space.

Uses the token saved by `hf auth login` on this machine; no token is passed on the command line.

    uv run python scripts/publish_hf.py db --user <hf-user>
    uv run python scripts/publish_hf.py space --user <hf-user> --origin https://<site>.vercel.app
"""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
DATASET = "nyaya-search-db"
SPACE = "nyaya-search-api"
DUMP_NAME = "nyaya.dump"
LOCAL_DUMP = ROOT / "data" / "backups" / DUMP_NAME
GROQ_MODEL = "openai/gpt-oss-20b"  # Groq production model available to regular accounts


def dump_url(user: str) -> str:
    return f"https://huggingface.co/datasets/{user}/{DATASET}/resolve/main/{DUMP_NAME}"


def publish_db(api: HfApi, user: str) -> None:
    """pg_dump the local database (minus run logs) and upload it as a public dataset file."""
    LOCAL_DUMP.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "pg_dump", "-U", "nyaya", "-d", "nyaya", "-Fc",
         "--exclude-table-data=llm_calls", "--exclude-table-data=ingest_runs", "--exclude-table-data=shared_notes", "-f", f"/backups/{DUMP_NAME}"],
        cwd=ROOT,
        check=True,
    )
    print(f"dump: {LOCAL_DUMP.stat().st_size / 1e6:.0f} MB")
    repo = f"{user}/{DATASET}"
    api.create_repo(repo, repo_type="dataset", exist_ok=True)
    api.upload_file(path_or_fileobj=str(LOCAL_DUMP), path_in_repo=DUMP_NAME, repo_id=repo, repo_type="dataset",
                    commit_message="Database dump for the Nyaya Search API Space")
    print(f"uploaded: {dump_url(user)}")


def stage_space() -> Path:
    """Folder with exactly what the Space build needs."""
    stage = Path(tempfile.mkdtemp(prefix="hf-space-"))
    for name in ("Dockerfile", "start.sh", "README.md"):
        shutil.copy(ROOT / "deploy" / "hf-space" / name, stage / name)
    shutil.copy(ROOT / "deploy" / "requirements-api.txt", stage / "requirements-api.txt")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for package in ("core", "api"):
        shutil.copytree(ROOT / package, stage / package, ignore=ignore)
    return stage


def publish_space(api: HfApi, user: str, origin: str | None) -> None:
    repo = f"{user}/{SPACE}"
    api.create_repo(repo, repo_type="space", space_sdk="docker", exist_ok=True)
    variables = {"DB_DUMP_URL": dump_url(user), "LLM_MODEL": GROQ_MODEL, "LLM_DAILY_CAP": "300"}
    if origin:
        variables["ALLOWED_ORIGINS"] = f"{origin},http://localhost:3000"
    for key, value in variables.items():
        api.add_space_variable(repo, key, value)
    stage = stage_space()
    api.upload_folder(repo_id=repo, repo_type="space", folder_path=str(stage), commit_message="Deploy Nyaya Search API",
                      delete_patterns=["*"])
    shutil.rmtree(stage)
    print(f"Space: https://huggingface.co/spaces/{repo}")
    print(f"API:   https://{user}-{SPACE}.hf.space  (after the build finishes)")
    print("Add the secret LLM_API_KEY (your Groq key) in the Space settings if you have not yet.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["db", "space"])
    parser.add_argument("--user", required=True, help="Hugging Face username")
    parser.add_argument("--origin", help="Website origin allowed by CORS, e.g. https://<site>.vercel.app")
    args = parser.parse_args()
    api = HfApi()
    print(f"logged in to Hugging Face as: {api.whoami()['name']}")
    if args.what == "db":
        publish_db(api, args.user)
    else:
        publish_space(api, args.user, args.origin)


if __name__ == "__main__":
    main()
