
import os
import re
import logging
import asyncio
from urllib.parse import urlsplit, urlunsplit

import requests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==================================================
# CxW SCRIPT V3 CONFIG
# ==================================================

BOT_TOKEN = os.environ["TELE_BOT"]
PASS_FULL = os.environ["PASS_SYS"]
PASS_LIMITED = os.environ["PASS_SYS1"]
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

# ==================================================
# KEYBOARD
# ==================================================

def menu_keyboard(role):
    rows = [
        ["➕ Add Script", "✏️ Edit Script"],
        ["🔎 Search Script", "📋 Check Script"],
        ["📚 All Scripts", "🏷 Check All Tag"],
        ["🆔 Check ID Script", "🔄 Refresh"],
    ]

    if role == "full":
        rows.insert(1, ["🗑 Delete Script"])

    rows.append(["🚪 Logout"])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Select CxW Script menu..."
    )


def input_keyboard(options):
    return ReplyKeyboardMarkup(
        options + [["↩️ Main Menu"]],
        resize_keyboard=True,
        is_persistent=True,
    )


# ==================================================
# API REQUESTS
# ==================================================

def api_request(method, endpoint="", payload=None):
    response = requests.request(
        method,
        API_URL + endpoint,
        headers=HEADERS,
        json=payload,
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
    return api_request(
        "POST",
        "",
        {
            "name": name,
            "tags": tags,
            "url": url,
            "isPublic": True,
        },
    )


def update_script(script_id, payload):
    return api_request(
        "PUT",
        "/" + str(script_id),
        payload,
    )


def remove_script(script_id):
    return api_request(
        "DELETE",
        "/" + str(script_id),
    )


# ==================================================
# URL NORMALIZATION / DUPLICATE CHECK
# ==================================================

def normalize_url(url):
    parts = urlsplit(url.strip())

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"

    return urlunsplit((
        scheme,
        netloc,
        path,
        parts.query,
        "",
    ))


def find_duplicate(scripts, url, exclude_id=None):
    target = normalize_url(url)

    for script in scripts:
        if str(script.get("id")) == str(exclude_id):
            continue

        existing = script.get("url", "")

        if not existing:
            continue

        try:
            if normalize_url(existing) == target:
                return script
        except Exception:
            continue

    return None


def valid_url(value):
    try:
        parts = urlsplit(value.strip())

        return (
            parts.scheme.lower() in ("http", "https")
            and bool(parts.netloc)
            and "." in parts.netloc
        )
    except Exception:
        return False


def parse_tags(value):
    tags = []

    for item in value.split(","):
        tag = item.strip().lower().lstrip("#")

        if tag and tag not in tags:
            tags.append(tag)

    return tags or ["universal"]


def get_tags(script):
    tags = script.get("tags", ["universal"])

    if isinstance(tags, str):
        return parse_tags(tags)

    return tags or ["universal"]


def format_tags(script):
    return ", ".join("#" + tag for tag in get_tags(script))


def select_number(scripts, value):
    try:
        number = int(value)
        if 1 <= number <= len(scripts):
            return number - 1, scripts[number - 1]
    except ValueError:
        pass

    return None, None


def find_by_name(scripts, value):
    query = value.strip().lower()

    return [
        (i, script)
        for i, script in enumerate(scripts, 1)
        if query in str(script.get("name", "")).lower()
    ]


# ==================================================
# MESSAGE HELPERS
# ==================================================

async def send_chunks(message, content):
    while content:
        chunk = content[:3500]

        if len(content) > 3500:
            split = chunk.rfind("\n")
            if split > 0:
                chunk = content[:split]

        await message.reply_text(chunk)
        content = content[len(chunk):].lstrip()


async def show_menu(update, context):
    context.user_data["flow"] = None

    role = context.user_data.get("role", "limited")

    await update.effective_message.reply_text(
        "✦ CxW SCRIPT MANAGEMENT ✦\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to CxW Script V3.\n\n"
        f"Access Level: {role.upper()}\n"
        "Silakan pilih menu dari keyboard di bawah.",
        reply_markup=menu_keyboard(role),
    )


async def fail_message(update, error):
    logging.exception("Operation failed", exc_info=error)

    await update.effective_message.reply_text(
        "⚠️ Operation Failed\n\n"
        f"{str(error)[:1000]}"
    )


# ==================================================
# AUTHENTICATION
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data

    if data.get("authenticated"):
        await update.message.reply_text(
            "Kamu sudah login.\n"
            "Gunakan tombol menu di keyboard.",
            reply_markup=menu_keyboard(data["role"]),
        )
        return

    data["flow"] = "login"

    await update.message.reply_text(
        "✦ CxW SCRIPT AUTHENTICATION ✦\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Masukkan password untuk mengakses sistem:",
        reply_markup=ReplyKeyboardRemove(),
    )


async def login(update, context, password):
    data = context.user_data

    if password == PASS_FULL:
        data["authenticated"] = True
        data["role"] = "full"

    elif password == PASS_LIMITED:
        data["authenticated"] = True
        data["role"] = "limited"

    else:
        await update.message.reply_text(
            "❌ Password tidak valid.\n"
            "Silakan coba lagi."
        )
        return

    data["flow"] = None

    await update.message.reply_text(
        "✅ ACCESS GRANTED\n\n"
        "Berhasil login ke CxW Script.",
        reply_markup=menu_keyboard(data["role"]),
    )

    await update.message.reply_text(
        "Dashboard siap digunakan."
    )


# ==================================================
# ACCESS CONTROL
# ==================================================

def is_authenticated(context):
    return bool(context.user_data.get("authenticated"))


def has_full_access(context):
    return context.user_data.get("role") == "full"


def can_use(context, action):
    if not is_authenticated(context):
        return False

    if action == "delete":
        return has_full_access(context)

    return True


# ==================================================
# DUPLICATE RESPONSE
# ==================================================

async def duplicate_message(update, script):
    await update.effective_message.reply_text(
        "⚠️ DUPLICATE SCRIPT DETECTED\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Script tidak dapat ditambahkan karena URL "
        "sudah terdaftar.\n\n"
        f"📌 Existing Name:\n{script.get('name', '-')}\n\n"
        f"🏷 Existing Tags:\n{format_tags(script)}\n\n"
        f"🔗 Existing URL:\n{script.get('url', '-')}\n\n"
        f"🆔 Existing ID:\n{script.get('id', '-')}\n\n"
        "Status: ADD REJECTED"
    )


# ==================================================
# SCRIPT LIST
# ==================================================

async def list_scripts(update, context, ids_only=False):
    scripts = await asyncio.to_thread(get_scripts)

    if not scripts:
        await update.message.reply_text("Belum ada script.")
        return

    lines = []

    if ids_only:
        lines.append("🆔 CxW SCRIPT ID LIST")
    else:
        lines.append("📚 CxW ALL SCRIPTS")

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    for index, script in enumerate(scripts, 1):
        if ids_only:
            lines.append(
                f"\n#{index} {script.get('name', '-')}\n"
                f"ID: {script.get('id', '-')}"
            )
        else:
            lines.append(
                f"\n#{index} {script.get('name', '-')}\n"
                f"ID: {script.get('id', '-')}\n"
                f"Tags: {format_tags(script)}\n"
                f"URL: {script.get('url', '-')}"
            )

    await send_chunks(
        update.message,
        "\n".join(lines),
    )


async def list_tags(update):
    scripts = await asyncio.to_thread(get_scripts)

    counts = {}

    for script in scripts:
        for tag in get_tags(script):
            counts[tag] = counts.get(tag, 0) + 1

    output = [
        "🏷 CxW ALL TAGS",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for tag, count in sorted(counts.items()):
        output.append(f"#{tag}  ·  {count} scripts")

    output.append(f"\nTotal Tags: {len(counts)}")

    await send_chunks(update.message, "\n".join(output))


# ==================================================
# SCRIPT DETAILS
# ==================================================

async def check_script(update, value):
    scripts = await asyncio.to_thread(get_scripts)

    index, script = select_number(scripts, value)

    if script is None:
        matches = find_by_name(scripts, value)

        if not matches:
            await update.message.reply_text(
                "❌ Script tidak ditemukan."
            )
            return

        output = ["🔎 SEARCH RESULTS"]

        for number, item in matches:
            output.append(
                f"\n#{number} {item.get('name', '-')}\n"
                f"ID: {item.get('id', '-')}\n"
                f"Tags: {format_tags(item)}\n"
                f"URL: {item.get('url', '-')}"
            )

        await send_chunks(update.message, "\n".join(output))
        return

    await update.message.reply_text(
        "📋 SCRIPT DETAILS\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Number: #{index + 1}\n"
        f"Name: {script.get('name', '-')}\n"
        f"ID: {script.get('id', '-')}\n"
        f"Tags: {format_tags(script)}\n"
        f"URL: {script.get('url', '-')}\n"
        f"Public: {script.get('isPublic', True)}"
    )


# ==================================================
# ADD SCRIPT
# ==================================================

async def add_flow(update, context, value):
    data = context.user_data
    flow = data.get("flow")

    if flow == "add_name":
        if len(value) > 150:
            await update.message.reply_text("Nama maksimal 150 karakter.")
            return

        data["new_name"] = value
        data["flow"] = "add_tags"

        await update.message.reply_text(
            "🏷 Masukkan tag script.\n"
            "Contoh: #sae, #roblox, #universal"
        )

    elif flow == "add_tags":
        data["new_tags"] = parse_tags(value)
        data["flow"] = "add_url"

        await update.message.reply_text(
            "🔗 Masukkan URL script:"
        )

    elif flow == "add_url":
        if not valid_url(value):
            await update.message.reply_text(
                "❌ URL tidak valid. Gunakan HTTP atau HTTPS."
            )
            return

        try:
            scripts = await asyncio.to_thread(get_scripts)

            duplicate = find_duplicate(scripts, value)

            if duplicate:
                await duplicate_message(update, duplicate)
                data["flow"] = None
                return

            result = await asyncio.to_thread(
                add_script,
                data["new_name"],
                data["new_tags"],
                value,
            )

            data["flow"] = None

            await update.message.reply_text(
                "✅ SCRIPT ADDED SUCCESSFULLY\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Name: {data['new_name']}\n"
                f"Tags: {', '.join('#' + t for t in data['new_tags'])}\n"
                f"URL: {value}\n"
                f"ID: {result.get('id', '-')}",
                reply_markup=menu_keyboard(data["role"]),
            )

        except Exception as error:
            await fail_message(update, error)


# ==================================================
# EDIT SCRIPT
# ==================================================

async def edit_flow(update, context, value):
    data = context.user_data
    flow = data.get("flow")

    if flow == "edit_number":
        scripts = await asyncio.to_thread(get_scripts)
        index, script = select_number(scripts, value)

        if script is None:
            await update.message.reply_text(
                "❌ Nomor script tidak ditemukan."
            )
            return

        data["edit_script"] = script
        data["edit_number"] = index + 1
        data["flow"] = "edit_field"

        await update.message.reply_text(
            "✏️ EDIT SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"#{index + 1} {script.get('name', '-')}\n"
            f"Tags: {format_tags(script)}\n"
            f"URL: {script.get('url', '-')}\n\n"
            "Pilih bagian yang ingin diedit:",
            reply_markup=input_keyboard([
                ["📝 Edit Name", "🏷 Edit Tags"],
                ["🔗 Edit URL"],
            ]),
        )

    elif flow == "edit_field":
        fields = {
            "📝 Edit Name": "name",
            "🏷 Edit Tags": "tags",
            "🔗 Edit URL": "url",
        }

        field = fields.get(value)

        if not field:
            await update.message.reply_text(
                "Pilih salah satu tombol edit."
            )
            return

        data["edit_field"] = field
        data["flow"] = "edit_value"

        await update.message.reply_text(
            f"Masukkan nilai baru untuk {field.upper()}:",
            reply_markup=input_keyboard([]),
        )

    elif flow == "edit_value":
        script = data["edit_script"]
        field = data["edit_field"]

        if field == "name":
            if len(value) > 150:
                await update.message.reply_text(
                    "Nama maksimal 150 karakter."
                )
                return
            payload = {"name": value}

        elif field == "tags":
            payload = {"tags": parse_tags(value)}

        else:
            if not valid_url(value):
                await update.message.reply_text("URL tidak valid.")
                return

            scripts = await asyncio.to_thread(get_scripts)

            duplicate = find_duplicate(
                scripts,
                value,
                exclude_id=script["id"],
            )

            if duplicate:
                await duplicate_message(update, duplicate)
                data["flow"] = None
                return

            payload = {"url": value}

        try:
            await asyncio.to_thread(
                update_script,
                script["id"],
                payload,
            )

            data["flow"] = None

            await update.message.reply_text(
                "✅ SCRIPT UPDATED\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Number: #{data['edit_number']}\n"
                f"ID: {script['id']}\n"
                f"Updated: {field.upper()}",
                reply_markup=menu_keyboard(data["role"]),
            )

        except Exception as error:
            await fail_message(update, error)


# ==================================================
# DELETE SCRIPT
# ==================================================

async def delete_flow(update, context, value):
    data = context.user_data

    scripts = await asyncio.to_thread(get_scripts)
    index, script = select_number(scripts, value)

    if script is None:
        await update.message.reply_text(
            "❌ Nomor script tidak ditemukan."
        )
        return

    data["delete_script"] = script
    data["delete_number"] = index + 1
    data["flow"] = "delete_confirm"

    await update.message.reply_text(
        "⚠️ CONFIRM SCRIPT DELETION\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Number: #{index + 1}\n"
        f"Name: {script.get('name', '-')}\n"
        f"ID: {script.get('id', '-')}\n\n"
        "Ketik CONFIRM untuk menghapus.\n"
        "Ketik CANCEL untuk membatalkan.",
        reply_markup=input_keyboard([
            ["CONFIRM", "CANCEL"],
        ]),
    )


# ==================================================
# MAIN MESSAGE ROUTER
# ==================================================

async def handle_message(update, context):
    value = update.message.text.strip()
    data = context.user_data

    if not data.get("authenticated"):
        if data.get("flow") == "login":
            await login(update, context, value)
        return

    if value == "↩️ Main Menu":
        await show_menu(update, context)
        return

    if value == "🚪 Logout":
        data.clear()

        await update.message.reply_text(
            "Logout berhasil.\nGunakan /start untuk login kembali.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    flow = data.get("flow")

    if flow in ("add_name", "add_tags", "add_url"):
        await add_flow(update, context, value)
        return

    if flow in ("edit_number", "edit_field", "edit_value"):
        await edit_flow(update, context, value)
        return

    if flow == "delete_number":
        await delete_flow(update, context, value)
        return

    if flow == "delete_confirm":
        if value.upper() == "CANCEL":
            data["flow"] = None
            await show_menu(update, context)
            return

        if value.upper() != "CONFIRM":
            await update.message.reply_text(
                "Gunakan tombol CONFIRM atau CANCEL."
            )
            return

        script = data.get("delete_script")

        if not script:
            await show_menu(update, context)
            return

        try:
            await asyncio.to_thread(
                remove_script,
                script["id"],
            )

            data["flow"] = None
            data.pop("delete_script", None)

            await update.message.reply_text(
                "✅ SCRIPT DELETED\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Number: #{data['delete_number']}\n"
                f"Name: {script.get('name', '-')}\n"
                f"ID: {script.get('id', '-')}",
                reply_markup=menu_keyboard(data["role"]),
            )

        except Exception as error:
            await fail_message(update, error)

        return

    # MAIN MENU ROUTER

    if value == "➕ Add Script":
        data["flow"] = "add_name"

        await update.message.reply_text(
            "➕ ADD SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nama script:",
            reply_markup=input_keyboard([]),
        )

    elif value == "✏️ Edit Script":
        data["flow"] = "edit_number"

        await update.message.reply_text(
            "✏️ EDIT SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nomor urutan script:",
            reply_markup=input_keyboard([]),
        )

    elif value == "🗑 Delete Script":
        if not can_use(context, "delete"):
            await update.message.reply_text("⛔ Akses ditolak.")
            return

        data["flow"] = "delete_number"

        await update.message.reply_text(
            "🗑 DELETE SCRIPT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Masukkan nomor urutan script:",
            reply_markup=input_keyboard([]),
        )

    elif value == "🔎 Search Script":
        data["flow"] = "search"

        await update.message.reply_text(
            "🔎 SEARCH SCRIPT\n"
            "Masukkan nama atau nomor urutan:"
        )

    elif value == "📋 Check Script":
        data["flow"] = "check"

        await update.message.reply_text(
            "📋 CHECK SCRIPT\n"
            "Masukkan nomor urutan atau nama script:"
        )

    elif value == "📚 All Scripts":
        try:
            await list_scripts(update, context)
        except Exception as error:
            await fail_message(update, error)

    elif value == "🏷 Check All Tag":
        try:
            await list_tags(update)
        except Exception as error:
            await fail_message(update, error)

    elif value == "🆔 Check ID Script":
        try:
            await list_scripts(update, context, True)
        except Exception as error:
            await fail_message(update, error)

    elif value == "🔄 Refresh":
        try:
            scripts = await asyncio.to_thread(get_scripts)

            await update.message.reply_text(
                "🔄 DATA REFRESHED\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Total Scripts: {len(scripts)}",
                reply_markup=menu_keyboard(data["role"]),
            )
        except Exception as error:
            await fail_message(update, error)

    elif flow == "search":
        try:
            scripts = await asyncio.to_thread(get_scripts)

            index, script = select_number(scripts, value)

            if script:
                await check_script(update, value)
            else:
                matches = find_by_name(scripts, value)

                if not matches:
                    await update.message.reply_text(
                        "Script tidak ditemukan."
                    )
                else:
                    output = ["🔎 SEARCH RESULTS"]

                    for number, item in matches:
                        output.append(
                            f"\n#{number} {item.get('name', '-')}\n"
                            f"ID: {item.get('id', '-')}\n"
                            f"Tags: {format_tags(item)}"
                        )

                    await send_chunks(
                        update.message,
                        "\n".join(output),
                    )

            data["flow"] = None

        except Exception as error:
            await fail_message(update, error)

    elif flow == "check":
        try:
            await check_script(update, value)
            data["flow"] = None
        except Exception as error:
            await fail_message(update, error)

    else:
        await update.message.reply_text(
            "Silakan pilih menu dari keyboard."
        )


# ==================================================
# ERROR HANDLER
# ==================================================

async def error_handler(update, context):
    logging.error(
        "Unhandled error",
        exc_info=context.error,
    )


# ==================================================
# MAIN
# ==================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    app.add_error_handler(error_handler)

    logging.info("CxW Script V3 started.")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
