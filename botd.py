
import os
import json
import time
import logging
import requests

from pathlib import Path
from requests.exceptions import RequestException

# ==========================================
# CoCo Discord to WhatsApp Bot
# Created By: CoCo x Who?
# ==========================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

API_FONNTE = os.getenv("API_FONNTE")
UID_GB2 = os.getenv("UID_GB2")

POLL_INTERVAL = 2
STATE_FILE = Path("state.json")

DISCORD_API = "https://discord.com/api/v10"
FONNTE_API = "https://api.fonnte.com/send"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

session = requests.Session()


# ==========================================
# VALIDATION
# ==========================================

def validate_config():
    required = {
        "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN,
        "DISCORD_CHANNEL_ID": DISCORD_CHANNEL_ID,
        "API_FONNTE": API_FONNTE,
        "UID_GB2": UID_GB2,
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise RuntimeError(
            "GitHub Secrets belum lengkap: " + ", ".join(missing)
        )


# ==========================================
# STATE MANAGEMENT
# ==========================================

def load_state():
    if not STATE_FILE.exists():
        return None

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return data.get("last_message_id")

    except (json.JSONDecodeError, OSError):
        logging.warning("State file tidak valid.")
        return None


def save_state(message_id):
    temp_file = STATE_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(
            {"last_message_id": str(message_id)},
            file,
            indent=2
        )

    temp_file.replace(STATE_FILE)


# ==========================================
# DISCORD
# ==========================================

def discord_headers():
    return {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }


def get_discord_messages(after=None, limit=100):
    url = (
        f"{DISCORD_API}/channels/"
        f"{DISCORD_CHANNEL_ID}/messages"
    )

    params = {"limit": limit}

    if after:
        params["after"] = str(after)

    response = session.get(
        url,
        headers=discord_headers(),
        params=params,
        timeout=20
    )

    if response.status_code == 429:
        retry_after = float(
            response.headers.get("Retry-After", 2)
        )
        logging.warning(
            "Discord rate limit. Menunggu %.2f detik.",
            retry_after
        )
        time.sleep(retry_after)
        return []

    response.raise_for_status()

    messages = response.json()

    # Discord API returns newest-first.
    messages.sort(key=lambda msg: int(msg["id"]))

    return messages


def get_latest_message_id():
    messages = get_discord_messages(limit=1)

    if messages:
        return messages[-1]["id"]

    return None


# ==========================================
# MESSAGE FORMATTER
# ==========================================

def format_discord_message(message):
    content = (message.get("content") or "").strip()

    parts = []

    if content:
        parts.append(content)

    # Include embed information if available.
    for embed in message.get("embeds", []):
        title = embed.get("title")
        description = embed.get("description")

        if title:
            parts.append(title)

        if description:
            parts.append(description)

    # Include attachment links.
    for attachment in message.get("attachments", []):
        url = attachment.get("url")

        if url:
            parts.append(url)

    if not parts:
        return None

    return "\n".join(parts)


# ==========================================
# FONNTE
# ==========================================

def send_whatsapp(message):
    headers = {
        "Authorization": API_FONNTE
    }

    payload = {
        "target": UID_GB2,
        "message": message
    }

    response = session.post(
        FONNTE_API,
        headers=headers,
        data=payload,
        timeout=30
    )

    response.raise_for_status()

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError("Respons Fonnte bukan JSON.")

    if result.get("status") is not True:
        raise RuntimeError(
            f"Fonnte gagal mengirim: {result}"
        )

    return True


# ==========================================
# MESSAGE PROCESSOR
# ==========================================

def process_message(message):
    message_id = message["id"]

    text = format_discord_message(message)

    if not text:
        logging.info(
            "Pesan %s kosong, dilewati.",
            message_id
        )
        return True

    author = message.get("author", {})
    username = author.get("global_name") or author.get("username", "Unknown")

    whatsapp_message = (
        "🥚 CoCo Notifier V2\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Discord: {username}"
    )

    send_whatsapp(whatsapp_message)

    logging.info(
        "Pesan Discord %s berhasil diteruskan ke WhatsApp.",
        message_id
    )

    return True


# ==========================================
# MAIN LOOP
# ==========================================

def main():
    validate_config()

    logging.info("CoCo Discord to WhatsApp Bot started.")
    logging.info("Polling interval: %s seconds", POLL_INTERVAL)

    last_message_id = load_state()

    # First run: set a baseline so old messages
    # are not forwarded to WhatsApp.
    if not last_message_id:
        latest_id = get_latest_message_id()

        if latest_id:
            save_state(latest_id)
            last_message_id = latest_id

            logging.info(
                "Baseline saved. Menunggu pesan baru: %s",
                latest_id
            )
        else:
            logging.info("Channel masih kosong.")

    while True:
        try:
            messages = get_discord_messages(
                after=last_message_id,
                limit=100
            )

            for message in messages:
                message_id = message["id"]

                try:
                    process_message(message)

                    # Save only after successful forwarding.
                    last_message_id = message_id
                    save_state(last_message_id)

                except Exception as error:
                    logging.error(
                        "Gagal meneruskan pesan %s: %s",
                        message_id,
                        error
                    )

                    # Stop here so the failed message
                    # can be retried on the next poll.
                    break

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Bot dihentikan.")
            break

        except RequestException as error:
            logging.error("Network/API error: %s", error)
            time.sleep(POLL_INTERVAL)

        except Exception:
            logging.exception("Terjadi kesalahan.")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
