
import os
import re
import asyncio
import logging
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==========================================
# CxW SCRIPT CONFIGURATION
# ==========================================

BOT_TOKEN = os.environ["TELE_BOT"]
SYSTEM_PASSWORD = os.environ["PASS_SYS"]
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]

API_URL = "https://data.cocoxwho.my.id/api/scripts"

HEADERS = {
    "Content-Type": "application/json",
    "x-auth-pass": ADMIN_TOKEN
}

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==========================================
# API HANDLER
# ==========================================

def api_request(method, endpoint="", data=None):
    url = API_URL + endpoint

    response = requests.request(
        method,
        url,
        headers=HEADERS,
        json=data,
        timeout=30
    )

    response.raise_for_status()

    if response.status_code == 204:
        return {}

    if not response.text:
        return {}

    return response.json()


def get_scripts():
    result = api_request("GET", "?all=true")

    if isinstance(result, dict):
        return result.get("scripts", [])

    return result


def add_script(name, tags, url):
    return api_request("POST", "", {
        "name": name,
        "tags": tags,
        "url": url,
        "isPublic": True
    })


def edit_script(script_id, name, tags, url):
    data = {
        "name": name,
        "tags": tags,
        "url": url
    }

    return api_request(
        "PUT",
        "/" + script_id,
        data
    )


def delete_script(script_id):
    return api_request(
        "DELETE",
        "/" + script_id
    )


# ==========================================
# TAG HANDLER
# ==========================================

def parse_tags(text):
    tags = []

    for tag in text.split(","):
        tag = tag.strip().lower()

        if tag.startswith("#"):
            tag = tag[1:]

        if tag and tag not in tags:
            tags.append(tag)

    return tags or ["universal"]


def format_tags(tags):
    if isinstance(tags, str):
        tags = parse_tags(tags)

    return ", ".join("#" + tag for tag in tags)


# ==========================================
# KEYBOARDS
# ==========================================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Script",
                callback_data="add"
            ),
            InlineKeyboardButton(
                "✏️ Edit Script",
                callback_data="edit"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Delete Script",
                callback_data="delete"
            ),
            InlineKeyboardButton(
                "🏷 Check All Tag",
                callback_data="tags"
            )
        ],
        [
            InlineKeyboardButton(
                "📚 All Script",
                callback_data="all"
            ),
            InlineKeyboardButton(
                "🔎 Check ID Script",
                callback_data="ids"
            )
        ]
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ Cancel / Main Menu",
                callback_data="home"
            )
        ]
    ])


async def show_menu(update, context):
    context.user_data["flow"] = None

    message = (
        "╔════════════════════╗\n"
        "       ✦ CxW SCRIPT ✦\n"
        "╚════════════════════╝\n\n"
        "Welcome to CxW Script Manager.\n\n"
        "Pilih fitur yang ingin digunakan:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=main_keyboard()
        )
    else:
        await update.effective_message.reply_text(
            message,
            reply_markup=main_keyboard()
        )


# ==========================================
# START / AUTHENTICATION
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["authenticated"] = False
    context.user_data["flow"] = "login"

    await update.message.reply_text(
        "╔════════════════════╗\n"
        "       ✦ CxW SCRIPT ✦\n"
        "╚════════════════════╝\n\n"
        "Welcome to CxW Script.\n\n"
        "🔐 Silakan masukkan password untuk mengakses bot:"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if not user_data.get("authenticated"):
        if user_data.get("flow") != "login":
            return

        password = update.message.text.strip()

        if password == SYSTEM_PASSWORD:
            user_data["authenticated"] = True
            user_data["flow"] = None

            await update.message.reply_text(
                "✅ Authentication Successful!\n"
                "Selamat datang di CxW Script."
            )

            await show_menu(update, context)

        else:
            await update.message.reply_text(
                "❌ Password salah!\n"
                "Silakan coba kembali."
            )

        return

    flow = user_data.get("flow")
    value = update.message.text.strip()

    # ======================================
    # ADD SCRIPT
    # ======================================

    if flow == "add_name":
        user_data["new_name"] = value
        user_data["flow"] = "add_tags"

        await update.message.reply_text(
            "🏷 Masukkan Tag Script:\n\n"
            "Contoh:\n"
            "#sae, #rap, #bf",
            reply_markup=back_keyboard()
        )

    elif flow == "add_tags":
        user_data["new_tags"] = parse_tags(value)
        user_data["flow"] = "add_url"

        await update.message.reply_text(
            "🔗 Masukkan URL Script:",
            reply_markup=back_keyboard()
        )

    elif flow == "add_url":
        if not value.startswith(("https://", "http://")):
            await update.message.reply_text(
                "❌ URL tidak valid. Masukkan URL HTTP/HTTPS."
            )
            return

        try:
            result = await asyncio.to_thread(
                add_script,
                user_data["new_name"],
                user_data["new_tags"],
                value
            )

            user_data["flow"] = None

            await update.message.reply_text(
                "✅ SCRIPT BERHASIL DITAMBAHKAN!\n\n"
                f"📌 Nama: {user_data['new_name']}\n"
                f"🏷 Tag: {format_tags(user_data['new_tags'])}\n"
                f"🆔 ID: {result.get('id', '-')}\n"
                f"🔗 URL: {value}",
                reply_markup=main_keyboard()
            )

        except Exception as error:
            await update.message.reply_text(
                f"❌ Gagal menambahkan script:\n{error}",
                reply_markup=main_keyboard()
            )

        return

    # ======================================
    # EDIT SCRIPT
    # ======================================

    elif flow == "edit_id":
        try:
            scripts = await asyncio.to_thread(get_scripts)

            script = next(
                (s for s in scripts if s["id"] == value),
                None
            )

            if not script:
                await update.message.reply_text(
                    "❌ Script ID tidak ditemukan."
                )
                return

            user_data["edit_id"] = value
            user_data["edit_old"] = script
            user_data["flow"] = "edit_name"

            await update.message.reply_text(
                "✏️ EDIT SCRIPT\n\n"
                f"Nama sekarang: {script.get('name', '')}\n"
                f"Tag sekarang: {format_tags(script.get('tags', []))}\n"
                f"URL sekarang: {script.get('url', '')}\n\n"
                "Masukkan nama baru.\n"
                "Kirim - jika ingin mempertahankan nama lama.",
                reply_markup=back_keyboard()
            )

        except Exception as error:
            await update.message.reply_text(f"❌ Error: {error}")

    elif flow == "edit_name":
        old = user_data["edit_old"]
        user_data["edit_name"] = (
            old.get("name", "") if value == "-" else value
        )

        user_data["flow"] = "edit_tags"

        await update.message.reply_text(
            "Masukkan tag baru:\n"
            "Contoh: #sae, #bf\n\n"
            "Kirim - untuk mempertahankan tag lama."
        )

    elif flow == "edit_tags":
        old = user_data["edit_old"]

        user_data["edit_tags"] = (
            old.get("tags", ["universal"])
            if value == "-"
            else parse_tags(value)
        )

        user_data["flow"] = "edit_url"

        await update.message.reply_text(
            "Masukkan URL baru.\n\n"
            "Kirim - untuk mempertahankan URL lama."
        )

    elif flow == "edit_url":
        old = user_data["edit_old"]

        new_url = old.get("url", "") if value == "-" else value

        if not new_url.startswith(("https://", "http://")):
            await update.message.reply_text(
                "❌ URL tidak valid."
            )
            return

        try:
            await asyncio.to_thread(
                edit_script,
                user_data["edit_id"],
                user_data["edit_name"],
                user_data["edit_tags"],
                new_url
            )

            user_data["flow"] = None

            await update.message.reply_text(
                "✅ SCRIPT BERHASIL DIPERBARUI!\n\n"
                f"🆔 ID: {user_data['edit_id']}\n"
                f"📌 Nama: {user_data['edit_name']}\n"
                f"🏷 Tag: {format_tags(user_data['edit_tags'])}\n"
                f"🔗 URL: {new_url}",
                reply_markup=main_keyboard()
            )

        except Exception as error:
            await update.message.reply_text(
                f"❌ Gagal edit:\n{error}",
                reply_markup=main_keyboard()
            )

        return

    # ======================================
    # DELETE SCRIPT
    # ======================================

    elif flow == "delete_id":
        try:
            scripts = await asyncio.to_thread(get_scripts)

            script = next(
                (s for s in scripts if s["id"] == value),
                None
            )

            if not script:
                await update.message.reply_text(
                    "❌ ID script tidak ditemukan."
                )
                return

            user_data["delete_id"] = value
            user_data["delete_name"] = script.get("name", "Unknown")
            user_data["flow"] = None

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Confirm Delete",
                        callback_data="confirm_delete"
                    ),
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data="home"
                    )
                ]
            ])

            await update.message.reply_text(
                "⚠️ KONFIRMASI DELETE\n\n"
                f"Nama: {script.get('name')}\n"
                f"ID: {value}\n\n"
                "Yakin ingin menghapus script ini?",
                reply_markup=keyboard
            )

        except Exception as error:
            await update.message.reply_text(f"❌ Error: {error}")

# ==========================================
# LIST DISPLAY
# ==========================================

async def send_chunks(message, text):
    chunks = []

    while len(text) > 3500:
        position = text.rfind("\n", 0, 3500)

        if position < 1:
            position = 3500

        chunks.append(text[:position])
        text = text[position:].lstrip()

    if text:
        chunks.append(text)

    for chunk in chunks:
        await message.reply_text(chunk)


async def display_scripts(update, context, ids_only=False):
    scripts = await asyncio.to_thread(get_scripts)

    if not scripts:
        await update.callback_query.message.reply_text(
            "Belum ada script tersimpan."
        )
        return

    if ids_only:
        lines = [
            "🆔 CxW SCRIPT - ID LIST\n"
        ]

        for index, script in enumerate(scripts, 1):
            lines.append(
                f"{index}. {script.get('name', 'Unknown')}\n"
                f"ID: {script.get('id', '-')}\n"
            )

    else:
        lines = [
            "📚 CxW SCRIPT - ALL SCRIPTS\n"
        ]

        for index, script in enumerate(scripts, 1):
            lines.append(
                f"{index}. {script.get('name', 'Unknown')}\n"
                f"🆔 {script.get('id', '-')}\n"
                f"🏷 {format_tags(script.get('tags', []))}\n"
                f"🔗 {script.get('url', '-')}\n"
            )

    await send_chunks(
        update.callback_query.message,
        "\n".join(lines)
    )


# ==========================================
# BUTTON HANDLER
# ==========================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_data = context.user_data

    if not user_data.get("authenticated"):
        await query.edit_message_text(
            "🔒 Silakan login menggunakan /start."
        )
        return

    action = query.data

    if action == "home":
        await show_menu(update, context)

    elif action == "add":
        user_data["flow"] = "add_name"

        await query.edit_message_text(
            "➕ ADD SCRIPT\n\n"
            "Masukkan nama script:",
            reply_markup=back_keyboard()
        )

    elif action == "edit":
        user_data["flow"] = "edit_id"

        await query.edit_message_text(
            "✏️ EDIT SCRIPT\n\n"
            "Masukkan ID script yang ingin diedit:",
            reply_markup=back_keyboard()
        )

    elif action == "delete":
        user_data["flow"] = "delete_id"

        await query.edit_message_text(
            "🗑 DELETE SCRIPT\n\n"
            "Masukkan ID script yang ingin dihapus:",
            reply_markup=back_keyboard()
        )

    elif action == "confirm_delete":
        script_id = user_data.get("delete_id")

        if not script_id:
            await show_menu(update, context)
            return

        try:
            await asyncio.to_thread(delete_script, script_id)

            user_data.pop("delete_id", None)
            user_data["flow"] = None

            await query.edit_message_text(
                "✅ SCRIPT BERHASIL DIHAPUS!\n\n"
                f"ID: {script_id}\n"
                f"Nama: {user_data.get('delete_name', '-')}"
            )

            await query.message.reply_text(
                "Menu utama:",
                reply_markup=main_keyboard()
            )

        except Exception as error:
            await query.edit_message_text(
                f"❌ Gagal menghapus script:\n{error}"
            )

    elif action == "all":
        await display_scripts(update, context, False)

    elif action == "ids":
        await display_scripts(update, context, True)

    elif action == "tags":
        try:
            scripts = await asyncio.to_thread(get_scripts)

            tags = set()

            for script in scripts:
                current = script.get("tags", [])

                if isinstance(current, str):
                    current = parse_tags(current)

                tags.update(current)

            output = "🏷 CxW SCRIPT - ALL TAGS\n\n"

            for tag in sorted(tags):
                count = sum(
                    tag in (
                        parse_tags(s.get("tags", ""))
                        if isinstance(s.get("tags"), str)
                        else s.get("tags", [])
                    )
                    for s in scripts
                )

                output += f"#{tag} — {count} scripts\n"

            output += f"\nTotal Tag: {len(tags)}"

            await query.message.reply_text(output)

        except Exception as error:
            await query.message.reply_text(
                f"❌ Gagal mengambil tag:\n{error}"
            )


# ==========================================
# APPLICATION
# ==========================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    logging.info("CxW Script Bot started.")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
