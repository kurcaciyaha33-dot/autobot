
import os
import re
import asyncio
import logging
from collections import deque

import discord
import requests

# ==========================================
# CoCo Discord -> WhatsApp Forwarder
# Created By: CoCo x Who?
# ==========================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
API_FONNTE = os.getenv("API_FONNTE")
UID_GB2 = os.getenv("UID_GB2")

FONNTE_URL = "https://api.fonnte.com/send"

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================
# VALIDATE CONFIG
# ==========================================

required = {
    "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN,
    "DISCORD_CHANNEL_ID": DISCORD_CHANNEL_ID,
    "API_FONNTE": API_FONNTE,
    "UID_GB2": UID_GB2
}

missing = [
    key for key, value in required.items()
    if not value or not value.strip()
]

if missing:
    raise RuntimeError(
        "GitHub Secrets belum lengkap: " + ", ".join(missing)
    )

try:
    CHANNEL_ID = int(DISCORD_CHANNEL_ID)
except ValueError:
    raise RuntimeError("DISCORD_CHANNEL_ID harus berupa angka.")

# ==========================================
# DISCORD CLIENT
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(
    intents=intents,
    max_messages=1000
)

# Pesan diproses satu per satu agar urut.
message_queue = asyncio.Queue()

# Cache ID pesan yang sudah berhasil dikirim.
processed_ids = set()
processed_order = deque(maxlen=5000)

# ==========================================
# MESSAGE FORMATTER
# ==========================================

def clean_message(message):
    parts = []

    # Isi pesan utama
    if message.content:
        parts.append(message.content)

    # Isi embed dari Discord Webhook
    for embed in message.embeds:
        if embed.title:
            parts.append(embed.title)

        if embed.description:
            parts.append(embed.description)

        for field in embed.fields:
            if field.name:
                parts.append(field.name)

            if field.value:
                parts.append(field.value)

    # Lampiran
    for attachment in message.attachments:
        parts.append(attachment.url)

    text = "\n".join(parts).strip()

    # Hapus mention user, role, dan channel.
    text = re.sub(r"<@!?[0-9]+>", "", text)
    text = re.sub(r"<@&[0-9]+>", "", text)
    text = re.sub(r"<#[0-9]+>", "", text)

    # Rapikan baris kosong.
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)

    return text.strip()


# ==========================================
# FONNTE SENDER
# ==========================================

def send_to_whatsapp(text):
    response = requests.post(
        FONNTE_URL,
        headers={
            "Authorization": API_FONNTE
        },
        data={
            "target": UID_GB2,
            "message": text
        },
        timeout=30
    )

    logging.info(
        "Fonnte HTTP status: %s",
        response.status_code
    )

    response.raise_for_status()

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            "Fonnte mengembalikan respons bukan JSON: "
            + response.text[:500]
        )

    logging.info("Fonnte response: %s", result)

    if result.get("status") is not True:
        raise RuntimeError(
            "Fonnte menolak pesan: " + str(result)
        )

    return True


# ==========================================
# MESSAGE QUEUE
# ==========================================

async def message_worker():
    while True:
        message = await message_queue.get()

        try:
            message_id = message.id

            if message_id in processed_ids:
                continue

            text = clean_message(message)

            if not text:
                logging.warning(
                    "Pesan kosong dilewati: %s",
                    message_id
                )
                continue

            logging.info(
                "Pesan baru diterima dari Discord: %s",
                message_id
            )

            # Retry jika pengiriman gagal.
            success = False

            for attempt in range(1, 4):
                try:
                    await asyncio.to_thread(
                        send_to_whatsapp,
                        text
                    )

                    success = True
                    break

                except Exception as error:
                    logging.error(
                        "Pengiriman gagal (%s/3): %s",
                        attempt,
                        error
                    )

                    if attempt < 3:
                        await asyncio.sleep(2)

            if success:
                processed_ids.add(message_id)
                processed_order.append(message_id)

                while len(processed_ids) > 5000:
                    oldest = processed_order.popleft()
                    processed_ids.discard(oldest)

                logging.info(
                    "BERHASIL diteruskan ke WhatsApp: %s",
                    message_id
                )
            else:
                logging.error(
                    "GAGAL meneruskan pesan: %s",
                    message_id
                )

        except Exception:
            logging.exception("Kesalahan saat memproses pesan.")

        finally:
            message_queue.task_done()


# ==========================================
# DISCORD EVENTS
# ==========================================

@client.event
async def on_ready():
    logging.info("================================")
    logging.info("CoCo Forwarder aktif.")
    logging.info("Discord account: %s", client.user)
    logging.info("Channel ID: %s", CHANNEL_ID)
    logging.info("================================")

    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        try:
            channel = await client.fetch_channel(CHANNEL_ID)
        except discord.HTTPException as error:
            logging.error(
                "Channel tidak dapat diakses: %s",
                error
            )
            return

    logging.info(
        "Channel terhubung: %s",
        getattr(channel, "name", CHANNEL_ID)
    )

    if not getattr(client, "_worker_started", False):
        client._worker_started = True
        asyncio.create_task(message_worker())


@client.event
async def on_message(message):
    # Hanya channel tujuan.
    if message.channel.id != CHANNEL_ID:
        return

    # Jangan abaikan pesan webhook atau pesan dari bot lain.
    # Semua pesan baru di channel tujuan akan diperiksa.
    logging.info(
        "Pesan Discord terdeteksi | ID: %s | Webhook: %s",
        message.id,
        message.webhook_id
    )

    if message.id in processed_ids:
        return

    await message_queue.put(message)


@client.event
async def on_disconnect():
    logging.warning("Discord terputus. Mencoba menyambung kembali...")


@client.event
async def on_resumed():
    logging.info("Koneksi Discord berhasil dipulihkan.")


@client.event
async def on_error(event, *args, **kwargs):
    logging.exception("Discord event error: %s", event)


# ==========================================
# START
# ==========================================

async def main():
    logging.info("Memulai CoCo Forwarder...")

    worker = None

    try:
        await client.start(DISCORD_BOT_TOKEN)

    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot dihentikan.")
