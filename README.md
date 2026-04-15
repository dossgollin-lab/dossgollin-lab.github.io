# Doss-Gollin lab site

Source code for the Doss-Gollin Research Group's [website](https://dossgollin-lab.github.io/), built with [Quarto](https://quarto.org/) and deployed to GitHub Pages.

The site is a living document and lab members are strongly encouraged to suggest improvements.
Don't hesitate to reach out for help on Slack if you're stuck — contributing to the website is a great learning experience!

## How to contribute

Direct pushes to `master` are not allowed.
All changes go through a pull request:

1. Create a branch off `master` (or fork the repo).
2. Make your edits locally. Preview with `quarto preview` (runs on port 4200).
3. Commit and push your branch.
4. Open a pull request against `master`.
5. CI runs a link check on your PR (see below). Fix any reported issues, then request review.
6. Once merged, the site is automatically rendered and deployed to GitHub Pages.

To add yourself to the people page, follow the steps on the [lab-guide wiki](https://github.com/dossgollin-lab/lab-guide/wiki).

## Continuous integration

Two GitHub Actions workflows run on this repo:

- **`publish-quarto.yml`** — on every push to `master`, updates the `bibliography` submodule, runs `quarto check`, renders the site, and publishes to the `gh-pages` branch.
- **`link-check.yml`** — on every pull request and weekly (Mondays 06:00 UTC), runs [lychee](https://lychee.cli.rs/) over all `.qmd` and `.md` files to catch broken links. Configuration lives in `.lychee.toml`. Some domains (LinkedIn, X, Google Scholar, DOI) are excluded because they block automated checks.

## Guidance for editors

See [`.claude/CLAUDE.md`](.claude/CLAUDE.md) for writing style, image best practices (including how to add alt text without a visible caption), and content conventions.
