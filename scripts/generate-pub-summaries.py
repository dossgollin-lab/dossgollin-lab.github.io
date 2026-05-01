# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "anthropic>=0.40",
#   "pypdf>=4.0",
#   "pyzotero>=1.5",
#   "pyyaml>=6.0",
# ]
# ///
"""Generate LLM summaries for lab publications and write them as sidecar files.

Usage:
    uv run scripts/generate-pub-summaries.py

Prerequisites:
    - Zotero desktop must be running (uses local Zotero API on port 23119)
    - ANTHROPIC_API_KEY environment variable set
    - Install Zotero BetterBibTeX plugin for citekey matching

The script is safe to re-run: it skips any citekey that already has a file
in _summaries/. Running all ~30 papers through Claude Sonnet has a real cost —
treat this as a one-time batch operation, not part of the build.
"""

import io
import json
import re
import subprocess
import sys
from pathlib import Path

import anthropic
import pypdf
import yaml

SUMMARIES_DIR = Path("_summaries")
PUBS_DIRS = [
    Path("bibliography/publications/article"),
    Path("bibliography/publications/conference"),
    Path("bibliography/publications/forthcoming"),
]
MODEL = "claude-sonnet-4-6"

# Path to the Zotero skill's CLI script.
ZOTERO_SKILL_DIR = Path.home() / ".claude" / "skills" / "zotero"
ZOTERO_SCRIPT = ZOTERO_SKILL_DIR / "scripts" / "zotero.py"

SYSTEM_PROMPT = (
    "You are a science communicator writing for a general audience. "
    "Write clearly, avoid jargon, and use an engaging reporter-style voice."
)

USER_PROMPT = """\
Generate a 1–2 paragraph summary of the following research paper.

Requirements:
- Reporter-style, general-audience voice
- Speak from the research team's perspective (use "we" / "our")
- Lead with the problem or challenge being addressed
- State the key finding and why it matters
- Accessible to a curious non-specialist; define technical terms if unavoidable
- Present tense throughout
- 150–200 words total; do not exceed 200 words
- Do not mention institution names
- Return only the summary paragraphs — no headings, labels, or preamble

Full paper text (may be truncated):
{text}
"""


def get_citekey(qmd_path: Path) -> str:
    return qmd_path.stem


def has_summary(citekey: str) -> bool:
    return (SUMMARIES_DIR / f"{citekey}.md").exists()


def load_frontmatter(qmd_path: Path) -> dict:
    text = qmd_path.read_text().replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def extract_nocite_citekey(fm: dict) -> str | None:
    """Extract the real BBT citekey from the nocite frontmatter field.

    The nocite field looks like: '@doss-gollin_fatalism:2020'
    We strip the leading '@' to get the actual citekey.
    """
    nocite = fm.get("nocite", "")
    if not nocite:
        return None
    # Strip surrounding quotes and leading '@'
    nocite = str(nocite).strip().strip('"').strip("'")
    if nocite.startswith("@"):
        nocite = nocite[1:]
    return nocite or None


def fetch_pdf_bytes(bbt_citekey: str, title: str) -> bytes | None:
    """Fetch PDF bytes from local Zotero by resolving the BBT citekey.

    Uses the Zotero skill's CLI to resolve the citekey to a local PDF path,
    then reads the file. Falls back to a title search if the direct resolve
    fails (e.g. unpinned citekeys that BBT hasn't synced yet).

    Args:
        bbt_citekey: The real BBT citekey (e.g. 'doss-gollin_fatalism:2020').
                     This is the value from the nocite frontmatter field, without
                     the leading '@'.
        title: Full paper title, used as a fallback search term.

    Returns:
        Raw PDF bytes, or None if no PDF is found in Zotero.
    """
    def _run_resolve(*args: str) -> dict | list | None:
        cmd = [
            "uv", "run", "--project", str(ZOTERO_SKILL_DIR),
            "python", str(ZOTERO_SCRIPT),
            *args,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return None
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None

    def _pdf_from_result(result: dict) -> bytes | None:
        pdf_path_str = result.get("pdf_path")
        if not pdf_path_str:
            return None
        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            return None
        return pdf_path.read_bytes()

    # Strategy 1: direct citekey resolve
    if bbt_citekey:
        result = _run_resolve("resolve", bbt_citekey, "--compact")
        if isinstance(result, dict):
            pdf_bytes = _pdf_from_result(result)
            if pdf_bytes is not None:
                return pdf_bytes

    # Strategy 2: title search fallback
    if title:
        results = _run_resolve("resolve", "--search", title, "--compact")
        if isinstance(results, list):
            for item in results:
                pdf_bytes = _pdf_from_result(item)
                if pdf_bytes is not None:
                    return pdf_bytes

    return None


def extract_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def generate_summary(text: str, client: anthropic.Anthropic) -> str:
    truncated = text[:12_000]
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT.format(text=truncated)}],
    )
    return message.content[0].text.strip()


def main() -> None:
    SUMMARIES_DIR.mkdir(exist_ok=True)
    client = anthropic.Anthropic()

    qmd_files = [f for d in PUBS_DIRS if d.exists() for f in sorted(d.glob("*.qmd"))]
    print(f"Found {len(qmd_files)} pub QMDs")

    skipped = processed = errors = 0
    for qmd_path in qmd_files:
        citekey = get_citekey(qmd_path)

        if has_summary(citekey):
            print(f"  skip (exists): {citekey}")
            skipped += 1
            continue

        print(f"  processing:   {citekey}")
        fm = load_frontmatter(qmd_path)
        title = fm.get("title", "")
        bbt_citekey = extract_nocite_citekey(fm)

        pdf_bytes = fetch_pdf_bytes(bbt_citekey or citekey, title)

        if pdf_bytes is None:
            print(f"    no PDF found in Zotero — skipping")
            errors += 1
            continue

        try:
            text = extract_text(pdf_bytes)
            summary = generate_summary(text, client)
            out_path = SUMMARIES_DIR / f"{citekey}.md"
            out_path.write_text(summary + "\n")
            print(f"    wrote {out_path}")
            processed += 1
        except Exception as exc:
            print(f"    error: {exc}", file=sys.stderr)
            errors += 1

    print(f"\nDone. processed={processed} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    main()
