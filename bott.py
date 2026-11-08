
import os
import logging
import asyncio
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# CONFIGURATION
# ==========================================

BOT_TOKEN = os.environ["TELE_BOT"]
SYSTEM_PASSWORD = os.environ["PASS_SYS"]
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]

API_URL = "https://data.cocoxwho.my.id/api/scripts"

HEADERS = {
    "Content-Type": "application/json",
    "x-auth-pass": ADMIN_TOKEN,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

MENU_BUTTON = "☰ Open CxW Menu"

REPLY_MENU = ReplyKeyboardMarkup(
    [[MENU_BUTTON]],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Pilih menu CxW Script...",
)

# ==========================================
# API
# ==========================================

def api_request(method, endpoint="", data=None):
    response = requests.request(
        method,
        API_URL + endpoint,
        headers=HEADERS,
        json=data,
        timeout=30,
    )

    response.raise_for_status()

    if not response.text:
        return {}

    return response.json()


def get_scripts():
    result = api_request("GET", "?all=true")

    if isinstance(result, dict):
        if result.get("error"):
            raise RuntimeError(result["error"])

        return result.get("scripts", [])

    return result


def add_script(name, tags, url):
    return api_request("POST", "", {
        "name": name,
        "tags": tags,
        "url": url,
        "isPublic": True,
    })


def edit_script(script_id, data):
    return api_request(
        "PUT",
        "/" + str(script_id),
        data,
    )


def delete_script(script_id):
    return api_request(
        "DELETE",
        "/" + str(script_id),
    )


# ==========================================
# HELPERS
# ==========================================

def parse_tags(value):
    result = []

    for tag in value.split(","):
        tag = tag.strip().lower().lstrip("#")

        if tag and tag not in result:
            result.append(tag)

    return result or ["universal"]


def get_tags(script):
    tags = script.get("tags", ["universal"])

    if isinstance(tags, str):
        return parse_tags(tags)

    return tags or ["universal"]


def tag_text(script):
    return ", ".join("#" + t for t in get_tags(script))


def get_script(scripts, number):
    try:
        index = int(number) - 1

        if 0 <= index < len(scripts):
            return scripts[index]

    except (ValueError, TypeError):
        pass

    return None


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "＋ Add Script",
                callback_data="add",
            ),
            InlineKeyboardButton(
                "✎ Edit Script",
                callback_data="edit",
            ),
        ],
        [
            InlineKeyboardButton(
                "⌫ Delete Script",
                callback_data="delete",
            ),
            InlineKeyboardButton(
                "⌕ Search",
                callback_data="search",
            ),
        ],
        [
            InlineKeyboardButton(
                "▤ All Scripts",
                callback_data="all",
            ),
            InlineKeyboardButton(
                "▦ All Tags",
                callback_data="tags",
            ),
        ],
        [
            InlineKeyboardButton(
                "ID Script",
                callback_data="ids",
            ),
            InlineKeyboardButton(
                "↻ Refresh",
                callback_data="refresh",
            ),
        ],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "← Main Menu",
                callback_data="home",
            )
        ]
    ])


def edit_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Edit Name",
                callback_data="field_name",
            ),
            InlineKeyboardButton(
                "Edit Tags",
                callback_data="field_tags",
            ),
        ],
        [
            InlineKeyboardButton(
                "Edit URL",
                callback_data="field_url",
            )
        ],
        [
            InlineKeyboardButton(
                "← Main Menu",
                callback_data="home",
            )
        ],
    ])


async def show_menu(update, context, new_message=False):
    context.user_data["flow"] = None

    text = (
        "CxW SCRIPT\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Script Management System\n\n"
        "Pilih menu yang ingin digunakan."
    )

    if update.callback_query and not new_message:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=main_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            text,
            reply_markup=REPLY_MENU,
        )

        await update.effective_message.reply_text(
            "Menu utama:",
            reply_markup=main_keyboard(),
        )


async def send_chunks(message, content):
    while content:
        part = content[:3500]

        if len(content) > 3500:
            split = part.rfind("\n")

            if split > 0:
                part = content[:split]

        await message.reply_text(part)

        content = content[len(part):].lstrip()


async def safe_scripts():
    return await asyncio.to_thread(get_scripts)


# ==========================================
# START / LOGIN
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("authenticated"):
        await show_menu(update, context, True)
        return

    context.user_data["flow"] = "login"

    await update.message.reply_text(
        "CxW SCRIPT\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Welcome to CxW Script.\n\n"
        "Masukkan password untuk melanjutkan:",
        reply_markup=ReplyKeyboardMarkup(
            [["Cancel"]],
            resize_keyboard=True,
        ),
    )


async def cancel(update, context):
    context.user_data["flow"] = None
    await show_menu(update, context, True)


async def logout(update, context):
    context.user_data.clear()

    await update.message.reply_text(
        "Anda telah logout.\n"
        "Masukkan password kembali melalui /start."
    )


# ==========================================
# TEXT HANDLER
# ==========================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    data = context.user_data

    if text == "Cancel":
        if data.get("authenticated"):
            await show_menu(update, context, True)
        else:
            data["flow"] = None
            await update.message.reply_text(
                "Login dibatalkan. Gunakan /start untuk mencoba lagi."
            )
        return

    if text == MENU_BUTTON:
        if data.get("authenticated"):
            await show_menu(update, context, True)
        else:
            await update.message.reply_text(
                "Silakan login melalui /start."
            )
        return

    if not data.get("authenticated"):
        if data.get("flow") != "login":
            return

        if text == SYSTEM_PASSWORD:
            data["authenticated"] = True
            data["flow"] = None

            await update.message.reply_text(
                "Login berhasil.\n"
                "Selamat datang di CxW Script.",
                reply_markup=REPLY_MENU,
            )

            await show_menu(update, context, True)

        else:
            await update.message.reply_text(
                "Password salah. Silakan coba lagi."
            )

        return

    flow = data.get("flow")

    # ADD SCRIPT

    if flow == "add_name":
        data["add_name"] = text
        data["flow"] = "add_tags"

        await update.message.reply_text(
            "Masukkan tag script.\n\n"
            "Contoh: #sae, #bf, #rap",
            reply_markup=back_keyboard(),
        )

    elif flow == "add_tags":
        data["add_tags"] = parse_tags(text)
        data["flow"] = "add_url"

        await update.message.reply_text(
            "Masukkan URL script:",
            reply_markup=back_keyboard(),
        )

    elif flow == "add_url":
        if not text.startswith(("https://", "http://")):
            await update.message.reply_text("URL harus menggunakan HTTP/HTTPS.")
            return

        try:
            result = await asyncio.to_thread(
                add_script,
                data["add_name"],
                data["add_tags"],
                text,
            )

            data["flow"] = None

            await update.message.reply_text(
                "Script berhasil ditambahkan.\n\n"
                f"Nama: {data['add_name']}\n"
                f"Tag: {', '.join('#' + t for t in data['add_tags'])}\n"
                f"ID: {result.get('id', '-')}\n"
                f"URL: {text}",
                reply_markup=REPLY_MENU,
            )

            await update.message.reply_text(
                "Menu utama:",
                reply_markup=main_keyboard(),
            )

        except Exception as error:
            await update.message.reply_text(
                f"Gagal menambahkan script:\n{error}"
            )

    # SELECT SCRIPT FOR EDIT

    elif flow == "edit_number":
        scripts = await safe_scripts()
        script = get_script(scripts, text)

        if not script:
            await update.message.reply_text(
                f"Nomor tidak valid. Pilih 1 sampai {len(scripts)}."
            )
            return

        data["edit_script"] = script
        data["edit_number"] = int(text)
        data["flow"] = None

        await update.message.reply_text(
            "EDIT SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Nomor: {text}\n"
            f"Nama: {script.get('name', '-')}\n"
            f"Tag: {tag_text(script)}\n"
            f"URL: {script.get('url', '-')}\n\n"
            "Pilih bagian yang ingin diedit:",
            reply_markup=edit_keyboard(),
        )

    elif flow == "edit_value":
        script = data["edit_script"]
        field = data["edit_field"]

        if field == "name":
            payload = {"name": text}
        elif field == "tags":
            payload = {"tags": parse_tags(text)}
        else:
            if not text.startswith(("https://", "http://")):
                await update.message.reply_text("URL tidak valid.")
                return
            payload = {"url": text}

        try:
            await asyncio.to_thread(
                api_request,
                "PUT",
                "/" + str(script["id"]),
                payload,
            )

            data["flow"] = None

            await update.message.reply_text(
                "Script berhasil diperbarui.\n"
                f"Nomor: {data['edit_number']}\n"
                f"Firebase ID: {script['id']}",
                reply_markup=REPLY_MENU,
            )

            await update.message.reply_text(
                "Menu utama:",
                reply_markup=main_keyboard(),
            )

        except Exception as error:
            await update.message.reply_text(f"Gagal edit: {error}")

    # DELETE SCRIPT

    elif flow == "delete_number":
        scripts = await safe_scripts()
        script = get_script(scripts, text)

        if not script:
            await update.message.reply_text(
                f"Nomor tidak valid. Pilih 1 sampai {len(scripts)}."
            )
            return

        data["delete_script"] = script
        data["delete_number"] = int(text)
        data["flow"] = None

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Confirm Delete",
                    callback_data="confirm_delete",
                ),
                InlineKeyboardButton(
                    "Cancel",
                    callback_data="home",
                ),
            ]
        ])

        await update.message.reply_text(
            "KONFIRMASI DELETE\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Nomor: {text}\n"
            f"Nama: {script.get('name', '-')}\n"
            f"ID: {script.get('id', '-')}\n\n"
            "Apakah kamu yakin ingin menghapus script ini?",
            reply_markup=keyboard,
        )

    # SEARCH

    elif flow == "search":
        scripts = await safe_scripts()
        query = text.lower()

        matches = []

        for index, script in enumerate(scripts, 1):
            name = str(script.get("name", "")).lower()

            if query in name or query == str(index):
                matches.append((index, script))

        data["flow"] = None

        if not matches:
            await update.message.reply_text(
                "Tidak ada script yang cocok dengan pencarian tersebut.",
                reply_markup=main_keyboard(),
            )
            return

        output = ["SEARCH RESULTS\n━━━━━━━━━━━━━━━━━━\n"]

        for index, script in matches:
            output.append(
                f"#{index} — {script.get('name', '-')}\n"
                f"Firebase ID: {script.get('id', '-')}\n"
                f"Tags: {tag_text(script)}\n"
                f"URL: {script.get('url', '-')}\n"
            )

        await send_chunks(
            update.message,
            "\n".join(output),
        )

        await update.message.reply_text(
            "Menu utama:",
            reply_markup=main_keyboard(),
        )


# ==========================================
# LISTS
# ==========================================

async def show_scripts(query, ids_only=False):
    scripts = await safe_scripts()

    if not scripts:
        await query.message.reply_text("Belum ada script.")
        return

    lines = []

    if ids_only:
        lines.append("SCRIPT ID LIST\n━━━━━━━━━━━━━━━━━━\n")

        for index, script in enumerate(scripts, 1):
            lines.append(
                f"#{index} {script.get('name', '-')}\n"
                f"ID: {script.get('id', '-')}\n"
            )
    else:
        lines.append("ALL SCRIPTS\n━━━━━━━━━━━━━━━━━━\n")

        for index, script in enumerate(scripts, 1):
            lines.append(
                f"#{index} {script.get('name', '-')}\n"
                f"ID: {script.get('id', '-')}\n"
                f"Tags: {tag_text(script)}\n"
                f"URL: {script.get('url', '-')}\n"
            )

    await send_chunks(
        query.message,
        "\n".join(lines),
    )


async def show_tags(query):
    scripts = await safe_scripts()
    counts = {}

    for script in scripts:
        for tag in get_tags(script):
            counts[tag] = counts.get(tag, 0) + 1

    if not counts:
        await query.message.reply_text("Belum ada tag.")
        return

    output = [
        "ALL TAGS\n━━━━━━━━━━━━━━━━━━\n"
    ]

    for tag, count in sorted(counts.items()):
        output.append(f"#{tag} — {count} scripts")

    output.append(f"\nTotal tags: {len(counts)}")

    await send_chunks(query.message, "\n".join(output))


# ==========================================
# CALLBACKS
# ==========================================

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    data = context.user_data
    action = query.data

    if not data.get("authenticated"):
        await query.message.reply_text(
            "Silakan login menggunakan /start."
        )
        return

    if action == "home":
        await show_menu(update, context)
        return

    if action == "refresh":
        await show_menu(update, context)
        return

    if action == "add":
        data["flow"] = "add_name"

        await query.edit_message_text(
            "ADD SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nama script:",
            reply_markup=back_keyboard(),
        )

    elif action == "edit":
        scripts = await safe_scripts()

        if not scripts:
            await query.edit_message_text("Belum ada script untuk diedit.")
            return

        data["flow"] = "edit_number"

        await query.edit_message_text(
            "EDIT SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nomor urutan script yang ingin diedit.\n\n"
            "Gunakan All Scripts untuk melihat nomor."
        )

    elif action == "delete":
        scripts = await safe_scripts()

        if not scripts:
            await query.edit_message_text("Belum ada script untuk dihapus.")
            return

        data["flow"] = "delete_number"

        await query.edit_message_text(
            "DELETE SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nomor urutan script yang ingin dihapus."
        )

    elif action == "search":
        data["flow"] = "search"

        await query.edit_message_text(
            "SEARCH SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nama atau nomor urutan script:",
            reply_markup=back_keyboard(),
        )

    elif action == "all":
        await show_scripts(query)

    elif action == "ids":
        await show_scripts(query, True)

    elif action == "tags":
        await show_tags(query)

    elif action.startswith("field_"):
        script = data.get("edit_script")

        if not script:
            await query.edit_message_text("Sesi edit tidak ditemukan.")
            return

        field = action.replace("field_", "")

        data["edit_field"] = field
        data["flow"] = "edit_value"

        prompts = {
            "name": "Masukkan nama script yang baru:",
            "tags": "Masukkan tag baru. Contoh: #sae, #bf:",
            "url": "Masukkan URL baru:",
        }

        await query.edit_message_text(
            prompts[field],
            reply_markup=back_keyboard(),
        )

    elif action == "confirm_delete":
        script = data.get("delete_script")

        if not script:
            await query.edit_message_text("Data penghapusan tidak ditemukan.")
            return

        try:
            await asyncio.to_thread(
                delete_script,
                str(script["id"]),
            )

            data["flow"] = None
            data.pop("delete_script", None)

            await query.edit_message_text(
                "SCRIPT DELETED\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"Nomor: {data.get('delete_number', '-')}\n"
                f"Nama: {script.get('name', '-')}\n"
                f"ID: {script.get('id', '-')}"
            )

            await query.message.reply_text(
                "Menu utama:",
                reply_markup=main_keyboard(),
            )

        except Exception as error:
            await query.edit_message_text(
                f"Gagal menghapus script:\n{error}"
            )


# ==========================================
# ERROR HANDLER
# ==========================================

async def error_handler(update, context):
    logging.error(
        "Bot error: %s",
        context.error,
    )


# ==========================================
# MAIN
# ==========================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("logout", logout))

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    app.add_error_handler(error_handler)

    logging.info("CxW Script V2 started.")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
