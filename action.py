import sys
import os
import argparse
from tkinter import W
from mapsplat import mapsplat
from pathlib import Path
from subprocess import run as prun
import jinja2
from github import Github


WEB_WD = "mapsplat__web"
PR_BODY = jinja2.Template("""
Hello! This is [mapsplat](https://github.com/{{ action_repo }}) asking you to
merge in new changes from [{{ repo }}](https://github.com/{{ repo }}).
""".strip())


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('data-path', type=Path)
    parser.add_argument('web-repo', type=str)
    parser.add_argument('by-institution-path', type=Path)
    parser.add_argument('index-path', type=Path)
    args = parser.parse_args(argv)

    # Get current rev
    cur_rev = prun(
        "git",
        "rev-list",
        "--pretty=oneline",
        "--max-count=1",
        "HEAD",
        capture_output=True,
        encoding="utf-8"
    ).stdout.strip()

    # Check out website
    prun("git", "checkout", f"git@github.com:{args.web_repo}", WEB_WD)

    # Run map splat
    web_path = Path(WEB_WD)
    mapsplat(args.data_path, web_path / args.by_institution_path, web_path / args.insert_index)

    # Push the changes
    os.environ["GIT_DIR"] = str(WEB_WD)
    prun("git", "checkout", "-B", "mapsplat/update-people")
    prun("git", "commit", "-m", f"Update people info based on map rev: {cur_rev}")
    prun("git", "push", "--force")
    del os.environ["GIT_DIR"]

    # Ensure there is an open pull request from this branch
    git = Github('GITHUB_TOKEN')
    repo = git.get_repo(args.web_repo)
    found = False
    for pr in repo.get_pulls(state='open'):
        for label in pr.get_labels():
            if label == "mapsplat":
                found = True
                break
        if found:
            break
    if not found:
        pr = repo.create_pull(
            title="Update list of RSE people/institutions from map data",
            body=PR_BODY.render({
                "action_repo": os.environ["GITHUB_ACTION_REPOSITORY"],
                "repo": os.environ["GITHUB_REPOSITORY"],
            }),
            base="main",
            head="mapsplat/update-people",
        )
        pr.add_to_labels("mapsplat")


if __name__ == "__main__":
    main()