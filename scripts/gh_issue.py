"""Post and read GitHub issues on this repo, so reviews and questions live where
the owner answers them (the Claude app reads and replies on GitHub).

    uv run python scripts/gh_issue.py post --title "Review 1.1: US loader" \
        --body-file review/1.1.md --label review
    uv run python scripts/gh_issue.py comment 3 --body-file answer.md
    uv run python scripts/gh_issue.py read 3          # issue body + every comment, oldest first
    uv run python scripts/gh_issue.py close 3 --body "Approved ..."  # comment, then close
    uv run python scripts/gh_issue.py list            # open issues

The token comes from GITHUB_TOKEN if set, else from `git credential fill` for
github.com (the same store `git push` uses). It is sent in a header and never
printed or written to disk.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import requests

REPO = "uty101/Yield-Curve-Carry-Strategy"
API = f"https://api.github.com/repos/{REPO}"
LABEL_COLOURS = {
    "review": "0e8a16",
    "question": "d93f0b",
    "decision": "1d76db",
    "session": "5319e7",
}


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password=") :]
    sys.exit("no GitHub token: set GITHUB_TOKEN or store one with git credential manager")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "curvecarry-gh-issue",
        }
    )
    return s


def _ensure_labels(s: requests.Session, labels: list[str]) -> None:
    for name in labels:
        r = s.post(f"{API}/labels", json={"name": name, "color": LABEL_COLOURS.get(name, "ededed")})
        if r.status_code not in (201, 422):  # 422 = already exists
            r.raise_for_status()


def _read_body(path: str | None, text: str | None) -> str:
    if path:
        return open(path, encoding="utf-8").read()
    if text:
        return text
    return sys.stdin.read()


def post(args: argparse.Namespace) -> None:
    s = _session()
    labels = args.label or []
    _ensure_labels(s, labels)
    body = _read_body(args.body_file, args.body)
    r = s.post(f"{API}/issues", json={"title": args.title, "body": body, "labels": labels})
    r.raise_for_status()
    j = r.json()
    print(f"#{j['number']} {j['html_url']}")


def comment(args: argparse.Namespace) -> None:
    s = _session()
    body = _read_body(args.body_file, args.body)
    r = s.post(f"{API}/issues/{args.number}/comments", json={"body": body})
    r.raise_for_status()
    print(r.json()["html_url"])


def read(args: argparse.Namespace) -> None:
    s = _session()
    r = s.get(f"{API}/issues/{args.number}")
    r.raise_for_status()
    j = r.json()
    print(f"# #{j['number']} {j['title']}  [{j['state']}]")
    print(f"by {j['user']['login']}  {j['created_at']}")
    print(j["body"] or "")
    page = 1
    while True:
        c = s.get(f"{API}/issues/{args.number}/comments", params={"per_page": 100, "page": page})
        c.raise_for_status()
        items = c.json()
        for it in items:
            print(f"\n---\n**{it['user']['login']}**  {it['created_at']}\n\n{it['body']}")
        if len(items) < 100:
            break
        page += 1


def close(args: argparse.Namespace) -> None:
    s = _session()
    if args.body_file or args.body:
        body = _read_body(args.body_file, args.body)
        s.post(f"{API}/issues/{args.number}/comments", json={"body": body}).raise_for_status()
    r = s.patch(
        f"{API}/issues/{args.number}", json={"state": "closed", "state_reason": "completed"}
    )
    r.raise_for_status()
    print(f"#{args.number} closed {r.json()['html_url']}")


def list_issues(args: argparse.Namespace) -> None:
    s = _session()
    r = s.get(f"{API}/issues", params={"state": args.state, "per_page": 100})
    r.raise_for_status()
    for j in r.json():
        labels = ",".join(lb["name"] for lb in j["labels"])
        print(f"#{j['number']:<4} {j['state']:<6} {j['comments']:>2}c  [{labels}] {j['title']}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="gh_issue.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("post", help="open an issue")
    a.add_argument("--title", required=True)
    a.add_argument("--body-file")
    a.add_argument("--body")
    a.add_argument("--label", action="append", help="repeatable; created if missing")
    a.set_defaults(fn=post)

    b = sub.add_parser("comment", help="comment on an issue")
    b.add_argument("number", type=int)
    b.add_argument("--body-file")
    b.add_argument("--body")
    b.set_defaults(fn=comment)

    c = sub.add_parser("read", help="print an issue and all its comments")
    c.add_argument("number", type=int)
    c.set_defaults(fn=read)

    e = sub.add_parser("close", help="optionally comment, then close an issue")
    e.add_argument("number", type=int)
    e.add_argument("--body-file")
    e.add_argument("--body")
    e.set_defaults(fn=close)

    d = sub.add_parser("list", help="list issues")
    d.add_argument("--state", default="open", choices=["open", "closed", "all"])
    d.set_defaults(fn=list_issues)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
