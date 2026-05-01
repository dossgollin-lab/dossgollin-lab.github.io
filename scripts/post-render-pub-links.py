# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4", "pyyaml"]
# ///
"""Post-render script: inject publication link buttons into _site/publications.html.

Registered in _quarto.yml as:
  post-render: uv run scripts/post-render-pub-links.py

Reads about.links from each pub QMD frontmatter and injects styled link buttons
into the corresponding listing card in the rendered publications page.
"""

import re
import sys
from html import escape
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

PUBS_HTML = Path("_site/publications.html")
PUBS_QMD_DIRS = [
    Path("bibliography/publications/article"),
    Path("bibliography/publications/conference"),
    Path("bibliography/publications/forthcoming"),
    # "other/" (dissertation, whitepapers) intentionally excluded — not in the site listing
]


def load_pub_links() -> dict[str, list[dict]]:
    """Return {normalized_title: [{"text": ..., "href": ...}, ...]} for all pubs."""
    result = {}
    for pub_dir in PUBS_QMD_DIRS:
        if not pub_dir.exists():
            continue
        for qmd_path in pub_dir.glob("*.qmd"):
            text = qmd_path.read_text().replace("\r\n", "\n")
            match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not match:
                continue
            try:
                fm = yaml.safe_load(match.group(1))
            except yaml.YAMLError:
                continue
            title = fm.get("title", "")
            if not title:
                continue
            links = fm.get("about", {})
            if isinstance(links, dict):
                links = links.get("links", [])
            else:
                links = []
            if links:
                result[_normalize(title)] = links
    return result


def _normalize(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower().strip())


def make_button_html(links: list[dict]) -> str:
    buttons = []
    for link in links:
        text = link.get("text", "Link")
        href = link.get("href", "#")
        if "doi.org" in href and text.upper().startswith("DOI"):
            text = "Paper"
        buttons.append(
            f'<a href="{escape(href)}" class="btn btn-outline-primary btn-sm me-1" '
            f'target="_blank" rel="noopener">{escape(text)}</a>'
        )
    return '<div class="pub-links mt-1">' + "".join(buttons) + "</div>"


def inject_buttons(html: str, pub_links: dict[str, list[dict]]) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for title_el in soup.select(".listing-title"):
        if title_el.name == "th":
            continue  # skip column header cells
        title_text = title_el.get_text()
        normalized = _normalize(title_text)
        links = pub_links.get(normalized)
        if not links:
            continue
        button_html = make_button_html(links)
        button_soup = BeautifulSoup(button_html, "html.parser")
        title_el.parent.insert_after(button_soup)
    return str(soup)


def main() -> None:
    if not PUBS_HTML.exists():
        print(f"  {PUBS_HTML} not found — skipping pub-links injection", file=sys.stderr)
        return
    pub_links = load_pub_links()
    if not pub_links:
        print("  No pub links found — skipping injection", file=sys.stderr)
        return
    html = PUBS_HTML.read_text()
    updated = inject_buttons(html, pub_links)
    PUBS_HTML.write_text(updated)
    print(f"  Injected link buttons for {len(pub_links)} pubs into {PUBS_HTML}")


if __name__ == "__main__":
    main()
