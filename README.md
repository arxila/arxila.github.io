# arxila.io

Source of the [arxila.io](https://arxila.io) website: the list of Arxila OSS projects and the
Go vanity import paths (`arxila.io/<module>`).

## Editing the project list

Edit [`projects.toml`](projects.toml). Repositories are listed under `active`, `development` or
`archived`, in the order they are shown. Descriptions and languages are taken from GitHub at
build time, so they are not edited here. A listed repository that is not public yet is skipped
until it is.

The `see_also` list (`owner/repo` entries) adds projects by the same author from outside the organization,
shown in a separate section at the end of the page. The `archived` section is shown collapsed.

Go modules are declared in the `[go]` table of the same file.

## How it is published

The `Build and deploy site` workflow runs `scripts/build.py`, which writes the site to `_site/`.
The workflow runs on every push to `main` and on demand. After changing a repository's
description on GitHub, run it by hand: in this repository's **Actions** tab, select
**Build and deploy site** → **Run workflow** (or `gh workflow run pages.yml -R arxila/arxila.github.io`).

To build and preview locally (Python 3.11+):

```bash
GH_TOKEN=$(gh auth token) python3 scripts/build.py
python3 -m http.server 8765 --directory _site
```
