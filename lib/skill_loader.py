"""SKILL.md parser, validator, and file I/O for the Skills Manager page."""

from __future__ import annotations

import re
from pathlib import Path


_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def list_skill_files(assets_dir: Path | None = None) -> list[Path]:
    """Return all .md files in the assets directory, sorted by name."""
    d = assets_dir or _ASSETS_DIR
    if not d.exists():
        return []
    return sorted(d.glob("*.md"))


def load_skill(path: Path) -> dict:
    """Read a SKILL.md file and parse YAML frontmatter + body.

    Returns dict with keys: path, filename, frontmatter (dict), body (str),
    raw (str), line_count (int).
    """
    raw = path.read_text(encoding="utf-8")
    frontmatter: dict = {}
    body = raw

    fm_match = re.match(r"^---\s*\n(.*?\n)---\s*\n", raw, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = raw[fm_match.end():]
        for line in fm_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if val.startswith(">-") or val.startswith("|"):
                    continue
                if val:
                    frontmatter[key] = val

        if "description" not in frontmatter:
            desc_match = re.search(
                r"^description:\s*>-?\s*\n((?:\s+.+\n)+)",
                fm_text,
                re.MULTILINE,
            )
            if desc_match:
                desc_lines = desc_match.group(1).strip().splitlines()
                frontmatter["description"] = " ".join(l.strip() for l in desc_lines)

    return {
        "path": path,
        "filename": path.name,
        "frontmatter": frontmatter,
        "body": body,
        "raw": raw,
        "line_count": raw.count("\n") + 1,
    }


def save_skill(path: Path, content: str) -> bool:
    """Write content back to a skill file. Returns True on success."""
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def validate_skill(content: str) -> list[str]:
    """Validate skill file content. Returns list of warning strings (empty = valid)."""
    warnings: list[str] = []
    line_count = content.count("\n") + 1

    fm_match = re.match(r"^---\s*\n(.*?\n)---\s*\n", content, re.DOTALL)
    if not fm_match:
        warnings.append("Missing YAML frontmatter (---...--- block at top of file).")
        return warnings

    fm_text = fm_match.group(1)

    if not re.search(r"^name:", fm_text, re.MULTILINE):
        warnings.append("Frontmatter is missing required 'name' field.")

    if not re.search(r"^description:", fm_text, re.MULTILINE):
        warnings.append("Frontmatter is missing required 'description' field.")

    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    if name_match:
        name = name_match.group(1).strip()
        if len(name) > 64:
            warnings.append(f"Skill name exceeds 64 characters ({len(name)} chars).")
        if not re.match(r"^[a-z0-9-]+$", name):
            warnings.append("Skill name should only contain lowercase letters, numbers, and hyphens.")

    if line_count > 500:
        warnings.append(f"File has {line_count} lines (recommended max: 500).")

    return warnings
