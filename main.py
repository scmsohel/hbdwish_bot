# main.py
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os, json, asyncio

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Render environment variable
CHANNEL_ID = "@nextgentech_bd"
CHANNEL_LINK = "https://t.me/nextgentech_bd"
DATA_FILE = "user_data.json"

EN_SITE = "https://birthday-wish-en.netlify.app/sc.html?nama="
BN_SITE = "https://birthday-wish-bn.netlify.app/sc.html?nama="

# ================== INIT JSON ==================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def save_user(user_id:int, data:dict):
    with open(DATA_FILE,"r") as f:
        all_data = json.load(f)
    all_data[str(user_id)] = data
    with open(DATA_FILE,"w") as f:
        json.dump(all_data,f)

def get_user(user_id:int):
    with open(DATA_FILE,"r") as f:
        all_data = json.load(f)
    return all_data.get(str(user_id), {})

# ================== HELPERS ==================
async def is_member(user_id:int, context:ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def join_verify_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📢 Join Our Channel', url=CHANNEL_LINK)],
        [InlineKeyboardButton('✅ Verify', callback_data='verify_membership')]
    ])

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="bn"),
         InlineKeyboardButton("🇬🇧 English", callback_data="en")]
    ])

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await update.message.reply_text(
            "⚠️ অনুগ্রহ করে আমাদের চ্যানেলে join করুন:",
            reply_markup=join_verify_keyboard()
        )
        return
    await update.message.reply_text(
        "আপনি কোন ভাষায় wish করতে চান?",
        reply_markup=language_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not await is_member(user_id, context):
        await query.edit_message_text(
            "❌ আপনি এখনো join করেননি।",
            reply_markup=join_verify_keyboard()
        )
        return

    data = get_user(user_id)

    if query.data == 'verify_membership':
        await query.edit_message_text(
            "✅ আপনি চ্যানেল join করেছেন!\n\nআপনি কোন ভাষায় wish করতে চান?",
            reply_markup=language_keyboard()
        )
    elif query.data in ['bn','en']:
        data["language"] = query.data
        save_user(user_id, data)
        if query.data == "bn":
            await query.edit_message_text("🎉 যাকে wish করতে চাও? তার নাম লিখো (বাংলায়):")
        else:
            await query.edit_message_text("🎉 Who do you want to wish? Please type their name:")
    elif query.data == "copy_link":
        if "link" in data:
            link = data["link"]
            await query.message.reply_text(
                f"👉👉 `{link}`",
                parse_mode="MarkdownV2"
            )
        else:
            await query.message.reply_text("প্রথমে নাম লিখুন। / Write a name first.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    if not user_data.get("language"):
        await update.message.reply_text(
            "⚠️ আগে ভাষা নির্বাচন করুন:",
            reply_markup=language_keyboard()
        )
        return

    name = update.message.text.strip()
    user_data["name"] = name

    lang = user_data["language"]
    if lang == "bn":
        link = BN_SITE + name.replace(" ", "%20")
        msg = f"🎂 তোমার উইশ লিঙ্ক তৈরি হয়েছে।"
    else:
        link = EN_SITE + name.replace(" ", "%20")
        msg = f"🎂 Your birthday wish link is ready."

    user_data["link"] = link
    save_user(user_id, user_data)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("কপি লিঙ্ক", callback_data="copy_link")],
        [InlineKeyboardButton("Wish চেক", url=link)]
    ])
    await update.message.reply_text(msg, reply_markup=keyboard)

# ================== FASTAPI + BOT ==================
app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(handle_callback))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot_app.bot)
    asyncio.create_task(bot_app.process_update(update))
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    print("Bot webhook ready.")
