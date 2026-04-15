#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "Pillow>=10.0.0",
#     "PyYAML>=6.0",
# ]
# ///
"""
Content validation script for Doss-Gollin Lab website.
Validates frontmatter, image dimensions, and cross-references.

Run locally with `uv run .github/scripts/validate-content.py`.

Exit codes:
    0 - All validations passed (may have warnings)
    1 - Critical errors found (build-blocking issues)

When running in GitHub Actions (GITHUB_ACTIONS=true):
    - Emits workflow commands for inline PR annotations
    - Writes markdown summary to $GITHUB_STEP_SUMMARY
"""

import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# Detect GitHub Actions environment
GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"
GITHUB_STEP_SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install PyYAML")
    sys.exit(1)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationResult:
    severity: Severity
    file: str
    message: str

    def __str__(self) -> str:
        icon = "❌" if self.severity == Severity.ERROR else "⚠️"
        return f"{icon} [{self.severity.value.upper()}] {self.file}: {self.message}"

    def to_github_command(self) -> str:
        """Return GitHub Actions workflow command for inline annotation."""
        cmd = "error" if self.severity == Severity.ERROR else "warning"
        # Escape special characters for workflow commands
        msg = self.message.replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
        return f"::{cmd} file={self.file}::{msg}"


# Configuration
MAX_IMAGE_SIZE_MB = 4
REPO_ROOT = Path(__file__).parent.parent.parent
PEOPLE_DIR = REPO_ROOT / "people"
POSTS_DIR = REPO_ROOT / "posts"
TEACHING_DIR = REPO_ROOT / "teaching"
ASSETS_IMG_DIR = REPO_ROOT / "_assets" / "img"
PEOPLE_IMG_DIR = ASSETS_IMG_DIR / "people"

# People subdirectories and their specific requirements
PEOPLE_SUBDIRS = {
    "pi": {"required": ["title", "sortby", "started"], "needs_ended": False},
    "grad-students": {"required": ["title", "sortby", "started"], "needs_ended": False},
    "grad-students-coadvised": {"required": ["title", "sortby", "started", "primary_advisor"], "needs_ended": False},
    "alumni": {"required": ["title", "sortby", "started", "ended", "position"], "needs_ended": True},
    "undergrad-students": {"required": ["title", "sortby", "started"], "needs_ended": False},
}


def extract_frontmatter(filepath: Path) -> Optional[dict]:
    """Extract YAML frontmatter from a QMD file."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return None

    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def validate_people_pages() -> list[ValidationResult]:
    """Validate all people QMD files have required fields."""
    results = []

    for subdir, config in PEOPLE_SUBDIRS.items():
        subdir_path = PEOPLE_DIR / subdir
        if not subdir_path.exists():
            continue

        for qmd_file in subdir_path.glob("*.qmd"):
            if qmd_file.name == "index.qmd":
                continue

            rel_path = qmd_file.relative_to(REPO_ROOT)
            frontmatter = extract_frontmatter(qmd_file)

            if frontmatter is None:
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    "Could not parse YAML frontmatter"
                ))
                continue

            # Check required fields
            for field in config["required"]:
                if field not in frontmatter or not frontmatter[field]:
                    results.append(ValidationResult(
                        Severity.ERROR,
                        str(rel_path),
                        f"Missing required field: {field}"
                    ))

            # Check sortby format (should be "LastName, FirstName")
            sortby = frontmatter.get("sortby", "")
            if sortby and "," not in sortby:
                results.append(ValidationResult(
                    Severity.WARNING,
                    str(rel_path),
                    f"sortby field '{sortby}' should be 'LastName, FirstName' format"
                ))

            # Check about.image exists
            about = frontmatter.get("about", {})
            if isinstance(about, dict):
                image_path = about.get("image", "")
                if image_path:
                    # Resolve relative path from the QMD file's location
                    abs_image_path = (qmd_file.parent / image_path).resolve()
                    if not abs_image_path.exists():
                        results.append(ValidationResult(
                            Severity.ERROR,
                            str(rel_path),
                            f"Profile image not found: {image_path}"
                        ))
                else:
                    results.append(ValidationResult(
                        Severity.WARNING,
                        str(rel_path),
                        "No profile image specified in about.image"
                    ))

    return results


def validate_profile_images() -> list[ValidationResult]:
    """Validate all profile images are square and within size limits."""
    results = []

    if not PEOPLE_IMG_DIR.exists():
        return results

    for img_file in PEOPLE_IMG_DIR.iterdir():
        if img_file.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            continue

        rel_path = img_file.relative_to(REPO_ROOT)

        # Check file size
        size_mb = img_file.stat().st_size / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            results.append(ValidationResult(
                Severity.WARNING,
                str(rel_path),
                f"Image size ({size_mb:.1f}MB) exceeds {MAX_IMAGE_SIZE_MB}MB limit"
            ))

        # Check dimensions
        try:
            with Image.open(img_file) as img:
                width, height = img.size
                if width != height:
                    results.append(ValidationResult(
                        Severity.ERROR,
                        str(rel_path),
                        f"Image is not square: {width}x{height} (difference: {abs(width-height)}px)"
                    ))
        except Exception as e:
            results.append(ValidationResult(
                Severity.ERROR,
                str(rel_path),
                f"Could not read image: {e}"
            ))

    return results


def validate_posts() -> list[ValidationResult]:
    """Validate posts have valid dates and required fields."""
    results = []

    if not POSTS_DIR.exists():
        return results

    date_pattern = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

    for year_dir in POSTS_DIR.iterdir():
        if not year_dir.is_dir():
            continue

        for qmd_file in year_dir.glob("*.qmd"):
            rel_path = qmd_file.relative_to(REPO_ROOT)
            frontmatter = extract_frontmatter(qmd_file)

            if frontmatter is None:
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    "Could not parse YAML frontmatter"
                ))
                continue

            # Check required fields
            if "title" not in frontmatter or not frontmatter["title"]:
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    "Missing required field: title"
                ))

            if "date" not in frontmatter:
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    "Missing required field: date"
                ))
                continue

            # Check date format
            date_str = str(frontmatter["date"])
            if not date_pattern.match(date_str):
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    f"Invalid date format: {date_str} (expected YYYY-MM-DD)"
                ))

            # Check filename matches date
            filename_match = date_pattern.match(qmd_file.name)
            if filename_match:
                filename_date = f"{filename_match.group(1)}-{filename_match.group(2)}-{filename_match.group(3)}"
                # Handle both string dates and datetime objects
                if hasattr(frontmatter["date"], "strftime"):
                    frontmatter_date = frontmatter["date"].strftime("%Y-%m-%d")
                else:
                    frontmatter_date = str(frontmatter["date"])[:10]

                if filename_date != frontmatter_date:
                    results.append(ValidationResult(
                        Severity.WARNING,
                        str(rel_path),
                        f"Filename date ({filename_date}) doesn't match frontmatter date ({frontmatter_date})"
                    ))

    return results


def validate_teaching() -> list[ValidationResult]:
    """Validate teaching pages have required fields."""
    results = []

    if not TEACHING_DIR.exists():
        return results

    valid_semesters = {"Fall", "Spring", "Summer"}

    for qmd_file in TEACHING_DIR.glob("*.qmd"):
        if qmd_file.name == "index.qmd":
            continue

        rel_path = qmd_file.relative_to(REPO_ROOT)
        frontmatter = extract_frontmatter(qmd_file)

        if frontmatter is None:
            results.append(ValidationResult(
                Severity.ERROR,
                str(rel_path),
                "Could not parse YAML frontmatter"
            ))
            continue

        # Check required fields
        required_fields = ["title", "year", "semester", "coursenumber"]
        for field in required_fields:
            if field not in frontmatter or not frontmatter[field]:
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    f"Missing required field: {field}"
                ))

        # Validate year
        year = frontmatter.get("year")
        if year is not None:
            try:
                year_int = int(year)
                if year_int < 2000 or year_int > 2100:
                    results.append(ValidationResult(
                        Severity.WARNING,
                        str(rel_path),
                        f"Year {year} seems unlikely"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    Severity.ERROR,
                    str(rel_path),
                    f"Year '{year}' is not a valid number"
                ))

        # Validate semester
        semester = frontmatter.get("semester")
        if semester and semester not in valid_semesters:
            results.append(ValidationResult(
                Severity.WARNING,
                str(rel_path),
                f"Semester '{semester}' should be one of: {', '.join(valid_semesters)}"
            ))

    return results


def validate_image_references() -> list[ValidationResult]:
    """Check that all referenced images in people pages exist."""
    results = []
    referenced_images = set()

    # Collect all referenced images from people pages
    for subdir in PEOPLE_SUBDIRS.keys():
        subdir_path = PEOPLE_DIR / subdir
        if not subdir_path.exists():
            continue

        for qmd_file in subdir_path.glob("*.qmd"):
            if qmd_file.name == "index.qmd":
                continue

            frontmatter = extract_frontmatter(qmd_file)
            if frontmatter is None:
                continue

            about = frontmatter.get("about", {})
            if isinstance(about, dict):
                image_path = about.get("image", "")
                if image_path:
                    abs_path = (qmd_file.parent / image_path).resolve()
                    if abs_path.exists():
                        referenced_images.add(abs_path)

    # Find orphaned images (warning only)
    if PEOPLE_IMG_DIR.exists():
        for img_file in PEOPLE_IMG_DIR.iterdir():
            if img_file.suffix.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                continue
            if img_file.resolve() not in referenced_images:
                rel_path = img_file.relative_to(REPO_ROOT)
                results.append(ValidationResult(
                    Severity.WARNING,
                    str(rel_path),
                    "Image not referenced by any people page (may be orphaned)"
                ))

    return results


def emit_github_annotations(results: list[ValidationResult]) -> None:
    """Emit GitHub Actions workflow commands for inline PR annotations."""
    for result in results:
        print(result.to_github_command())


def write_github_summary(results: list[ValidationResult]) -> None:
    """Write markdown summary to GitHub Actions step summary."""
    if not GITHUB_STEP_SUMMARY:
        return

    errors = [r for r in results if r.severity == Severity.ERROR]
    warnings = [r for r in results if r.severity == Severity.WARNING]

    lines = ["## Content Validation Results\n"]

    if not errors and not warnings:
        lines.append("✅ **All validations passed!**\n")
    else:
        if errors:
            lines.append(f"### 🚨 Errors ({len(errors)})\n")
            lines.append("These must be fixed before merging:\n")
            lines.append("| File | Issue |")
            lines.append("|------|-------|")
            for r in errors:
                lines.append(f"| `{r.file}` | {r.message} |")
            lines.append("")

        if warnings:
            lines.append(f"### ⚠️ Warnings ({len(warnings)})\n")
            lines.append("Consider addressing these issues:\n")
            lines.append("| File | Issue |")
            lines.append("|------|-------|")
            for r in warnings:
                lines.append(f"| `{r.file}` | {r.message} |")
            lines.append("")

    with open(GITHUB_STEP_SUMMARY, "a") as f:
        f.write("\n".join(lines))


def print_summary(results: list[ValidationResult]) -> None:
    """Print a formatted summary of validation results."""
    errors = [r for r in results if r.severity == Severity.ERROR]
    warnings = [r for r in results if r.severity == Severity.WARNING]

    # In GitHub Actions, emit workflow commands for inline annotations
    if GITHUB_ACTIONS:
        emit_github_annotations(results)
        write_github_summary(results)

    print("\n" + "=" * 60)
    print("CONTENT VALIDATION SUMMARY")
    print("=" * 60)

    if errors:
        print(f"\n🚨 ERRORS ({len(errors)}) - These must be fixed:\n")
        for result in errors:
            print(f"  {result}")

    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}) - Consider addressing:\n")
        for result in warnings:
            print(f"  {result}")

    if not errors and not warnings:
        print("\n✅ All validations passed with no issues!\n")
    else:
        print(f"\n{'=' * 60}")
        print(f"Total: {len(errors)} error(s), {len(warnings)} warning(s)")
        print("=" * 60)


def main() -> int:
    """Run all validations and return exit code."""
    print("🔍 Running content validations...\n")

    results = []

    print("  Checking people pages...")
    results.extend(validate_people_pages())

    print("  Checking profile images...")
    results.extend(validate_profile_images())

    print("  Checking posts...")
    results.extend(validate_posts())

    print("  Checking teaching pages...")
    results.extend(validate_teaching())

    print("  Checking image references...")
    results.extend(validate_image_references())

    print_summary(results)

    # Only fail on errors, not warnings
    errors = [r for r in results if r.severity == Severity.ERROR]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
