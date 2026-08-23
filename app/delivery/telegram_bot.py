"""Telegram delivery + interaction.

Run standalone:  python -m app.delivery.telegram_bot
Push a digest:   await push_digest(digest)   (called by the scheduler)

Commands
  /today      today's 3-3-3 (compact)
  /full       today's digest with framing checks and uncertainty
  /deep       the deep dive
  /bg /world /tech   one category
  /trend      democracy indicator over the last 30 days
  /sources    source registry with lean/reliability
  /more <tag> /less <tag>   steer future selection
  /run        force a rebuild (owner only)
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
)

from app import repository as repo
from app.config import settings
from app.db import session_scope
from app.delivery import formatting as fmt
from app.models.schemas import Category, DailyDigest

log = structlog.get_logger(__name__)

CATEGORY_BY_COMMAND = {
    "bg": Category.BG_POLITICS,
    "world": Category.GLOBAL_POLITICS,
    "tech": Category.AI_TECH_BUSINESS,
}


# ------------------------------------------------------------------ guards --
def authorized(update: Update) -> bool:
    allowed = settings.allowed_chat_ids
    chat = update.effective_chat
    return bool(chat) and (not allowed or chat.id in allowed)


async def _deny(update: Update) -> None:
    chat = update.effective_chat
    log.warning("telegram.unauthorized", chat_id=chat.id if chat else None)
    if update.message:
        await update.message.reply_text("This bot is private.")


def guard(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not authorized(update):
            return await _deny(update)
        return await handler(update, context)

    return wrapper


# ------------------------------------------------------------------- utils --
def _load_digest(d: date | None = None) -> DailyDigest | None:
    with session_scope() as db:
        return repo.get_digest(db, d) if d else repo.latest_digest(db)


async def _send(update: Update, messages: list[str], keyboard: InlineKeyboardMarkup | None = None) -> None:
    for i, msg in enumerate(messages):
        await update.effective_chat.send_message(
            msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=keyboard if i == len(messages) - 1 else None,
        )
        await asyncio.sleep(0.15)  # stay under Telegram's rate limit


def _feedback_keyboard(digest: DailyDigest) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton("👍 more like this", callback_data=f"fb:more:{digest.digest_date}"),
        InlineKeyboardButton("👎 less", callback_data=f"fb:less:{digest.digest_date}"),
    ], [
        InlineKeyboardButton("🔍 deep dive", callback_data="cmd:deep"),
        InlineKeyboardButton("📈 trend", callback_data="cmd:trend"),
    ]]
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------- handlers --
@guard
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "3-3-3 Democracy-Aware News Analyst.\n\n"
        "Every morning: 3 Bulgarian politics · 3 global politics · 3 AI/tech/business, "
        "each with a democracy and framing check, plus one deep dive.\n\n"
        f"Your chat id is <code>{update.effective_chat.id}</code> — add it to "
        "TELEGRAM_ALLOWED_CHAT_IDS.\n\n"
        "/today /full /deep /bg /world /tech /trend /sources",
        parse_mode=ParseMode.HTML,
    )


@guard
async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    digest = _load_digest()
    if digest is None:
        await update.message.reply_text("No digest yet. Try /run.")
        return
    await _send(update, fmt.build_messages(digest, compact=True, include_deep_dive=False),
                _feedback_keyboard(digest))


@guard
async def cmd_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    digest = _load_digest()
    if digest is None:
        await update.message.reply_text("No digest yet. Try /run.")
        return
    await _send(update, fmt.build_messages(digest, compact=False, include_deep_dive=True))


@guard
async def cmd_deep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    digest = _load_digest()
    if digest is None or not digest.deep_dive:
        await update.effective_chat.send_message("No deep dive today.")
        return
    blocks = [c for b in fmt.format_deep_dive(digest) for c in fmt.chunk(b)]
    await _send(update, blocks)


@guard
async def cmd_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = (update.message.text or "/bg").lstrip("/").split("@")[0].split()[0]
    category = CATEGORY_BY_COMMAND.get(command)
    digest = _load_digest()
    if digest is None or category is None:
        await update.message.reply_text("Nothing to show.")
        return
    await _send(update, fmt.chunk(fmt.format_category(digest, category, compact=False)))


@guard
async def cmd_trend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with session_scope() as db:
        dates = repo.list_digest_dates(db, 30)
        rows = [(d, repo.get_digest(db, d)) for d in dates]
    lines = ["📈 <b>Democracy indicator — last 30 digests</b>", ""]
    for d, dg in rows:
        if not dg:
            continue
        net = float(dg.stats.get("net_direction", 0) or 0)
        bar_len = int(abs(net) * 10)
        bar = ("🟥" if net < 0 else "🟩") * max(bar_len, 1) if net else "▪️"
        lines.append(f"<code>{d.isoformat()}</code> {bar} {net:+.2f}")
    await update.effective_chat.send_message("\n".join(lines), parse_mode=ParseMode.HTML)


@guard
async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.ingestion.sources import SOURCES

    lines = ["<b>Source registry</b>", ""]
    for s in SOURCES:
        if not s.enabled:
            continue
        lines.append(f"• {fmt.esc(s.name)} — <code>{s.lean.value}/{s.reliability.value}</code>")
    for msg in fmt.chunk("\n".join(lines)):
        await update.effective_chat.send_message(msg, parse_mode=ParseMode.HTML)


@guard
async def cmd_steer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/more <tag> and /less <tag> adjust the `personal` term in selection."""
    text = update.message.text or ""
    signal = "more" if text.startswith("/more") else "less"
    tag = " ".join(context.args).strip().lower()
    if not tag:
        await update.message.reply_text(f"Usage: /{signal} <topic or entity>")
        return
    with session_scope() as db:
        repo.add_feedback(db, signal=signal, tag=tag, channel="telegram")
    await update.message.reply_text(f"Noted: {signal} “{tag}”.")


@guard
async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.digest.builder import build_daily_digest

    await update.message.reply_text("Building… this takes a few minutes.")

    async def _job() -> None:
        with session_scope() as db:
            digest = await build_daily_digest(db)
        await _send(update, fmt.build_messages(digest, compact=True, include_deep_dive=False),
                    _feedback_keyboard(digest))

    context.application.create_task(_job())


@guard
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if data.startswith("fb:"):
        _, signal, day = data.split(":", 2)
        with session_scope() as db:
            repo.add_feedback(db, signal=signal, digest_date=date.fromisoformat(day),
                              channel="telegram")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Thanks — recorded “{signal}”.")
    elif data == "cmd:deep":
        await cmd_deep(update, context)
    elif data == "cmd:trend":
        await cmd_trend(update, context)


# ------------------------------------------------------------------- push --
async def push_digest(digest: DailyDigest, chat_ids: set[int] | None = None) -> None:
    """Called by the scheduler after a successful build."""
    from telegram import Bot

    bot = Bot(settings.telegram_bot_token)
    targets = chat_ids or settings.allowed_chat_ids
    messages = fmt.build_messages(digest, compact=True, include_deep_dive=False)
    for chat_id in targets:
        for msg in messages:
            await bot.send_message(chat_id, msg, parse_mode=ParseMode.HTML,
                                   disable_web_page_preview=True)
            await asyncio.sleep(0.2)
        if digest.deep_dive:
            await bot.send_message(
                chat_id, "🔍 Deep dive ready — /deep", parse_mode=ParseMode.HTML)
    log.info("telegram.pushed", chats=len(targets), messages=len(messages))


def build_application() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("full", cmd_full))
    app.add_handler(CommandHandler("deep", cmd_deep))
    app.add_handler(CommandHandler(list(CATEGORY_BY_COMMAND), cmd_category))
    app.add_handler(CommandHandler("trend", cmd_trend))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler(["more", "less"], cmd_steer))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_start))
    return app


def main() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    logging_msg = "telegram.starting"
    log.info(logging_msg, allowed=len(settings.allowed_chat_ids))
    build_application().run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
