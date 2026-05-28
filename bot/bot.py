#!/usr/bin/env python3
import os
import logging
import functools
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from converter import convert_and_save

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
AUTHORIZED_USER_ID = int(os.environ.get("AUTHORIZED_USER_ID", "0"))
WORKOUTS_DIR = Path(os.environ.get("WORKOUTS_DIR", "../workouts"))

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def require_auth(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if AUTHORIZED_USER_ID == 0:
            await update.message.reply_text(
                "Bot is in setup mode — AUTHORIZED_USER_ID not set.\n"
                "Use /whoami to get your ID, then set it in .env and restart."
            )
            return
        if update.effective_user.id != AUTHORIZED_USER_ID:
            logger.warning(f"Rejected message from user {update.effective_user.id}")
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Workout tracker ready.\n\n"
        "Send your workout as plain text, one exercise per line:\n\n"
        "run 5mins\n"
        "squat 60(6), 90(6), 90(6), 90(6)\n"
        "dips 10, 10, 10\n"
        "pullups 6, 6, 6, 6\n\n"
        "Use /cancel to discard a workout."
    )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Name: {user.full_name}\n"
        f"Username: @{user.username}\n"
        f"Telegram ID: {user.id}\n\n"
        "Set AUTHORIZED_USER_ID to your ID in .env to lock the bot to you."
    )


@require_auth
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text("Cancelled. Send a new workout whenever you're ready.")


@require_auth
async def handle_workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if not text:
        return

    now = datetime.now()
    WORKOUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write .pending file — Phase 2 converter picks this up
    date_str = now.strftime("%Y-%m-%d")
    pending_path = WORKOUTS_DIR / f"{date_str}.pending"

    # Append timestamp header so converter knows when this was logged
    payload = f"logged_at: {now.strftime('%Y-%m-%d %H:%M')}\n---\n{text}\n"
    pending_path.write_text(payload, encoding="utf-8")

    line_count = len([l for l in text.splitlines() if l.strip()])
    await update.message.reply_text(
        f"Got it — {line_count} line(s) received. Converting..."
    )
    logger.info(f"Workout saved to {pending_path} ({line_count} lines)")

    try:
        summary = await convert_and_save(pending_path, WORKOUTS_DIR)
        await update.message.reply_text(f"Done! {summary}")
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        await update.message.reply_text(
            f"Conversion failed: {e}\nRaw file kept at {pending_path.name}"
        )


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_workout))

    logger.info(f"Bot starting (polling). Authorized user: {AUTHORIZED_USER_ID or 'NOT SET'}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
