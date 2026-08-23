"""Obsidian vault writer.

Produces one daily note per digest plus stub notes for entities, so the vault
accumulates a linked graph of actors and institutions over time. Frontmatter is
Dataview-friendly: you can chart `democracy_net` across months from inside Obsidian.
"""
from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.analysis.democracy import SEVERITY_LABEL
from app.config import settings
from app.models.schemas import Category, DailyDigest

log = structlog.get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"

CATEGORY_LABELS: list[tuple[Category, str]] = [
    (Category.BG_POLITICS, "🇧🇬 Bulgarian politics"),
    (Category.GLOBAL_POLITICS, "🌍 Global politics"),
    (Category.AI_TECH_BUSINESS, "🤖 AI · tech · business"),
]

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return _SLUG.sub("-", str(value).lower()).strip("-")[:48]


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=(), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["slug"] = _slug
    return env


def render_digest_markdown(digest: DailyDigest) -> str:
    env = _env()
    template = env.get_template("digest.md.j2")
    all_tags = sorted({t for i in digest.items for t in i.analysis.tags})[:12]
    return template.render(
        d=digest,
        categories=CATEGORY_LABELS,
        all_tags=all_tags,
        severity=lambda v: SEVERITY_LABEL.get(int(v), "unclear"),
        prev_date=(digest.digest_date - timedelta(days=1)).isoformat(),
    )


def note_filename(digest: DailyDigest) -> str:
    return f"{digest.digest_date.isoformat()} — 3-3-3 Digest.md"


def write_obsidian_note(digest: DailyDigest, vault: Path | None = None,
                        write_entity_stubs: bool = True) -> Path:
    vault = Path(vault or settings.obsidian_vault_path)
    daily_dir = vault / "Digests"
    daily_dir.mkdir(parents=True, exist_ok=True)

    path = daily_dir / note_filename(digest)
    path.write_text(render_digest_markdown(digest), encoding="utf-8")

    if write_entity_stubs:
        _write_entity_stubs(vault, digest)
    _update_index(vault, digest)

    log.info("obsidian.written", path=str(path))
    return path


def _write_entity_stubs(vault: Path, digest: DailyDigest) -> None:
    """Create (never overwrite) a note per entity and append a backlink line."""
    ent_dir = vault / "Entities"
    ent_dir.mkdir(parents=True, exist_ok=True)
    link = f"[[{digest.digest_date.isoformat()} — 3-3-3 Digest]]"

    for item in digest.items:
        for entity in item.analysis.entities:
            safe = re.sub(r'[\\/:*?"<>|]', "-", entity).strip()
            if not safe:
                continue
            p = ent_dir / f"{safe}.md"
            if not p.exists():
                p.write_text(
                    f"---\ntype: entity\ntags: [entity]\n---\n\n# {safe}\n\n## Mentions\n",
                    encoding="utf-8",
                )
            line = f"- {digest.digest_date.isoformat()} — {item.analysis.headline} → {link}\n"
            existing = p.read_text(encoding="utf-8")
            if line not in existing:
                p.write_text(existing + line, encoding="utf-8")


def _update_index(vault: Path, digest: DailyDigest) -> None:
    """Maintain a simple MOC so the vault has one entry point."""
    idx = vault / "3-3-3 Digests.md"
    header = (
        "---\ntype: moc\n---\n\n# 3-3-3 Digests\n\n"
        "```dataview\nTABLE date, democracy_net, stories FROM \"Digests\" SORT date DESC\n```\n\n"
        "## Archive\n"
    )
    if not idx.exists():
        idx.write_text(header, encoding="utf-8")
    line = f"- [[{digest.digest_date.isoformat()} — 3-3-3 Digest]]\n"
    body = idx.read_text(encoding="utf-8")
    if line not in body:
        idx.write_text(body + line, encoding="utf-8")
