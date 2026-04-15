# Doss-Gollin lab site

Source code for the Doss-Gollin Research Group's [website](https://dossgollin-lab.github.io/), built with [Quarto](https://quarto.org/) and deployed to GitHub Pages.

The site is a living document and lab members are strongly encouraged to suggest improvements.
Don't hesitate to reach out for help on Slack if you're stuck — contributing to the website is a great learning experience!

## How to contribute

Direct pushes to `master` are not allowed.
All changes go through a pull request:

1. Create a branch off `master` (or fork the repo).
2. Preview your edits with `quarto preview` (port 4200).
3. Before committing, run the local checks (see below).
4. Commit and push your branch, then open a pull request against `master`.
5. PR CI runs the same checks plus a full site build. Fix anything that fails, then request review.
6. Once merged, the site is automatically rendered and deployed to GitHub Pages.

To add yourself to the people page, follow the steps on the [lab-guide wiki](https://github.com/dossgollin-lab/lab-guide/wiki).

## Local development

Install prerequisites (one-time):

```bash
brew install --cask quarto
brew install lychee uv
```

Before committing, run:

```bash
# Validate frontmatter, images, cross-references
uv run .github/scripts/validate-content.py

# Link check (uses the same config as CI)
lychee --config .lychee.toml --root-dir "$(pwd)" '**/*.qmd' '**/*.md'
```

`uv run` handles Python dependencies inline via PEP 723 — no venv setup needed.
`quarto preview` gives you a live preview on port 4200; `quarto render` produces a static build in `_site/`.

## Continuous integration

Two GitHub Actions workflows run on this repo:

- **`publish-quarto.yml`** — on every push to `master`, updates the `bibliography` submodule, runs `quarto check`, renders the site, and publishes to the `gh-pages` branch.
- **`pr-checks.yml`** — on every pull request, validates content frontmatter, renders the site, and runs [lychee](https://lychee.cli.rs/) against the rendered HTML to catch broken links. The link-check job is non-blocking (warnings only) because external sites can be flaky.

## Guidance for editors

See [`.claude/CLAUDE.md`](.claude/CLAUDE.md) for writing style, image best practices (including how to add alt text without a visible caption), and content conventions.
