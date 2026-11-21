#!/usr/bin/env python3
#
# =========================================================================
#
#   Copyright (c) 2026 Arxila OSS (https://arxila.io)
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#   implied. See the License for the specific language governing
#   permissions and limitations under the License.
#
# =========================================================================
#

"""Builds the arxila.io static site into _site/.

Reads projects.toml, fetches each listed repository's description from the
GitHub API, and renders templates/*.html. Static files are copied from site/.

Usage: python3 scripts/build.py [output_dir]

Set GITHUB_TOKEN (or GH_TOKEN) to avoid anonymous API rate limits.
"""

import html
import json
import os
import re
import shutil
import string
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ORG = "arxila"
DOMAIN = "arxila.io"
ROOT = Path(__file__).resolve().parent.parent
SECTIONS = [
    ("active", "Projects"),
    ("development", "Under Development"),
    ("archived", "Archived"),
]


def warn(msg):
    print(f"warning: {msg}", file=sys.stderr)


def fetch(api_path):
    req = urllib.request.Request(
        f"https://api.github.com/{api_path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "arxila-site-builder",
        },
    )
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def fetch_repo(name):
    return fetch(f"repos/{ORG}/{name}")


def linkify_mentions(escaped_text):
    """Turns @user mentions (in already-escaped text) into GitHub profile links."""
    return re.sub(
        r"(?<![\w@])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))",
        r'<a href="https://github.com/\1">@\1</a>',
        escaped_text,
    )


def render(template_name, **values):
    text = (ROOT / "templates" / template_name).read_text(encoding="utf-8")
    return string.Template(text).substitute(values)


def project_item(repo):
    name = html.escape(repo["name"])
    url = html.escape(repo["html_url"], quote=True)
    desc = html.escape((repo.get("description") or "").strip())
    lang = repo.get("language")
    lang_html = f'<span class="lang">{html.escape(lang)}</span>' if lang else ""
    return (
        f'<li><a class="project" href="{url}">'
        f'<span class="head"><span class="name">{name}</span>{lang_html}</span>'
        f'<span class="desc">{desc}</span>'
        f"</a></li>"
    )


def go_import_meta(path, repo):
    return (
        f'<meta name="go-import" content="{DOMAIN}/{html.escape(path, quote=True)} '
        f'git https://github.com/{ORG}/{html.escape(repo, quote=True)}">'
    )


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site"
    config = tomllib.loads((ROOT / "projects.toml").read_text(encoding="utf-8"))

    seen = set()
    sections_html = []
    for key, title in SECTIONS:
        items = []
        for name in config.get(key, []):
            if name in seen:
                sys.exit(f"error: '{name}' is listed more than once in projects.toml")
            seen.add(name)
            repo = fetch_repo(name)
            if repo is None or repo.get("private"):
                warn(f"'{name}' is not a public repository of {ORG}; skipped")
                continue
            if repo.get("archived") and key != "archived":
                warn(f"'{name}' is archived on GitHub but listed under '{key}'")
            if not repo.get("archived") and key == "archived":
                warn(f"'{name}' is listed as archived but is not archived on GitHub")
            items.append(project_item(repo))
        if items:
            sections_html.append(
                f'<section class="{key}"><h2>{title}</h2>'
                f'<ul class="projects">{"".join(items)}</ul></section>'
            )

    org_description = (fetch(f"orgs/{ORG}").get("description") or "").strip()
    if not org_description:
        sys.exit(f"error: the {ORG} organization has no description on GitHub")

    go_modules = config.get("go", {})

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)

    (out / "index.html").write_text(
        render(
            "index.html",
            sections="\n".join(sections_html),
            description=linkify_mentions(html.escape(org_description)),
            description_text=html.escape(org_description, quote=True),
        ),
        encoding="utf-8",
    )

    # One page per Go module. Deeper import paths (e.g. arxila.io/x/cmd/x) are
    # answered by 404.html, which carries every go-import tag: the go command
    # reads the tags even from a 404 response and picks the matching prefix.
    for path, repo in go_modules.items():
        page = out / path / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            render(
                "go.html",
                module=html.escape(f"{DOMAIN}/{path}"),
                meta=go_import_meta(path, repo),
                repo_url=html.escape(f"https://github.com/{ORG}/{repo}", quote=True),
                doc_url=html.escape(f"https://pkg.go.dev/{DOMAIN}/{path}", quote=True),
            ),
            encoding="utf-8",
        )

    all_meta = "\n    ".join(go_import_meta(p, r) for p, r in go_modules.items())
    (out / "404.html").write_text(render("404.html", meta=all_meta), encoding="utf-8")
    (out / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(f"built {out}")


if __name__ == "__main__":
    main()
