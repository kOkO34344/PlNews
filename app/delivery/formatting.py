"""Render a digest into Telegram-sized HTML chunks.

Telegram caps messages at 4096 characters and supports a small HTML subset, so the
digest goes out as one message per category plus an optional deep-dive thread.
"""
from __future__ import annotations

import html
import re

from app.analysis.democracy import SEVERITY_LABEL, weighted_direction
from app.models.schemas import Category, DailyDigest, DigestItem

TG_LIMIT = 4000  # leave headroom under the 4096 hard cap

CATEGORY_TITLES = {
    Category.BG_POLITICS: "🇧🇬 <b>Bulgarian politics</b>",
    Category.GLOBAL_POLITICS: "🌍 <b>Global politics</b>",
    Category.AI_TECH_BUSINESS: "🤖 <b>AI · tech · business</b>",
}

ARROW = {-2: "🔻🔻", -1: "🔻", 0: "▪️", 1: "🔺", 2: "🔺🔺"}


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def _democracy_line(item: DigestItem) -> str:
    dem = item.analysis.democracy
    if not dem.relevant:
        return ""
    net = int(round(weighted_direction(dem)))
    dims = ", ".join(i.dimension.value.replace("_", " ") for i in dem.impacts[:2])
    return (f"\n{ARROW.get(net, '▪️')} <i>Democracy: {esc(SEVERITY_LABEL.get(net, 'mixed'))}"
            f"{f' — {esc(dims)}' if dims else ''} · significance {dem.significance:.1f}</i>")


def format_item(item: DigestItem, *, compact: bool = True) -> str:
    a = item.analysis
    parts = [f"<b>{item.rank}. {esc(a.headline)}</b>", esc(a.what_happened)]
    if not compact:
        parts.append(f"<i>Why it matters:</i> {esc(a.why_it_matters)}")
    dem = _democracy_line(item)
    if dem:
        parts.append(dem.strip())
    if not compact and a.bias.framing_devices:
        parts.append(f"🪞 <i>Framing:</i> {esc('; '.join(a.bias.framing_devices[:3]))}")
    if not compact and a.uncertainty:
        parts.append(f"❓ <i>Unknown:</i> {esc(a.uncertainty)}")
    srcs = " · ".join(f'<a href="{esc(r.url)}">{esc(r.source_name)}</a>' for r in item.refs[:4])
    parts.append(f"🔗 {srcs}")
    return "\n".join(p for p in parts if p)


def format_category(digest: DailyDigest, category: Category, *, compact: bool = True) -> str:
    items = digest.by_category(category)
    if not items:
        return f"{CATEGORY_TITLES[category]}\n<i>No story cleared the bar today.</i>"
    body = "\n\n".join(format_item(i, compact=compact) for i in items)
    return f"{CATEGORY_TITLES[category]}\n\n{body}"


def format_header(digest: DailyDigest) -> str:
    stats = digest.stats or {}
    head = f"📰 <b>3-3-3 Digest — {digest.digest_date.isoformat()}</b>"
    if digest.editorial_note:
        head += f"\n\n<i>{esc(digest.editorial_note)}</i>"
    net = stats.get("net_direction", 0)
    head += (f"\n\n<code>{stats.get('fetched', 0)} articles → {stats.get('clusters', 0)} stories → "
             f"9 selected · democracy net {net:+.2f}</code>")
    return head


def format_deep_dive(digest: DailyDigest) -> list[str]:
    dd = digest.deep_dive
    if not dd:
        return []
    blocks = [
        f"🔍 <b>Deep dive — {esc(dd.title)}</b>\n\n{esc(dd.executive_summary)}",
        f"<b>How we got here</b>\n{esc(dd.background)}",
        f"<b>The machinery</b>\n{esc(dd.mechanisms)}",
        f"<b>Democratic stakes</b>\n{esc(dd.democracy_analysis)}",
        f"<b>Precedent</b>\n{esc(dd.comparative_precedent)}",
        "<b>Scenarios</b>\n" + "\n".join(
            f"• <b>{esc(s.name)}</b> ({s.probability:.0%}) — {esc(s.description)}"
            for s in dd.scenarios),
        "<b>What to watch</b>\n" + "\n".join(f"• {esc(w)}" for w in dd.what_to_watch),
        f"<b>Counterargument</b>\n<i>{esc(dd.counterargument)}</i>\n\n"
        f"<code>confidence {dd.confidence:.0%}</code>",
    ]
    return [b for b in blocks if b and len(b.split("\n", 1)[-1].strip()) > 0]


def chunk(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Split on paragraph boundaries, never mid-tag."""
    if len(text) <= limit:
        return [text]
    out, current = [], ""
    for para in re.split(r"\n\n+", text):
        if len(current) + len(para) + 2 > limit:
            if current:
                out.append(current)
            while len(para) > limit:
                out.append(para[:limit])
                para = para[limit:]
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        out.append(current)
    return out


def build_messages(digest: DailyDigest, *, compact: bool = True,
                   include_deep_dive: bool = True) -> list[str]:
    msgs = [format_header(digest)]
    for cat in (Category.BG_POLITICS, Category.GLOBAL_POLITICS, Category.AI_TECH_BUSINESS):
        msgs.extend(chunk(format_category(digest, cat, compact=compact)))
    if include_deep_dive:
        for block in format_deep_dive(digest):
            msgs.extend(chunk(block))
    return msgs
