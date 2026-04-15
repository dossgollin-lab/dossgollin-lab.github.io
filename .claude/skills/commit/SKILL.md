---
name: commit
description: Run pre-commit checks for this Quarto site (content validation + lychee link check) and create a commit. Use when the user asks to commit changes on this repository.
---

# Commit for dossgollin-lab.github.io

Direct pushes to `master` are not allowed on this repository.
Every change goes through a feature branch and a pull request.

## Pre-commit checks

Before creating a commit, run these two commands from the repo root:

```bash
uv run .github/scripts/validate-content.py
lychee --config .lychee.toml --root-dir "$(pwd)" '**/*.qmd' '**/*.md'
```

The first validates frontmatter, image dimensions, and cross-references (dependencies are declared inline in the script via PEP 723, so `uv run` installs them automatically). The second runs the same link check that CI runs, using the shared `.lychee.toml` config.

If `lychee` or `uv` is not installed, offer: `brew install lychee uv`.

## If checks fail

- **Real broken links** (404, connection errors on canonical domains): fix the link or remove it.
- **Bot-block false positives** (401/403/406/415 from sites like profiles.rice.edu, forbes.com, wsj.com): already accepted in `.lychee.toml`. If a new domain is consistently false-positive, add it to the `exclude` list in `.lychee.toml`.
- **Frontmatter errors** from `validate-content.py`: fix the flagged file(s).

Do not bypass failing checks with `--no-verify` or by skipping this step unless the user explicitly asks.

## Commit flow

After `make check` passes:

1. Stage specific files (not `git add -A`) so untracked scratch files and secrets don't sneak in.
2. Create a branch off `master` if not already on one.
3. Create a commit with a descriptive message (imperative mood, explain the "why" when non-obvious). Follow the git safety protocol from the default Claude Code system prompt: never amend, never force-push, no `--no-verify`.
4. Push the branch with `-u origin <branch>`.
5. Open a PR against `master` with `gh pr create`, summarizing the change and a test plan.

## Follow-up

After the PR is open, the PR checks workflow runs the same `lychee` check against the rendered site plus a Quarto build. If those fail, iterate with new commits on the same branch — do not amend or force-push.
