
import os
import re
import asyncio
import logging

import discord
import requests

# ==========================================
# CoCo Discord -> WhatsApp
# Created By: CoCo x Who?
# ==========================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

API_FONNTE = os.getenv("API_FONNTE")
UID_GB2 = os.getenv("UID_GB2")

FONNTE_URL = "https://api.fonnte.com/send"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==========================================
# VALIDATION
# ==========================================

required = {
    "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN,
    "DISCORD_CHANNEL_ID": DISCORD_CHANNEL_ID,
    "API_FONNTE": API_FONNTE,
    "UID_GB2": UID_GB2,
}

missing = [key for key, value in required.items() if not value]

if missing:
    raise RuntimeError(
        "Missing GitHub Secrets: " + ", ".join(missing)
    )

# ==========================================
# DISCORD CLIENT
# ==========================================

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

processed_messages = set()

# ==========================================
# CLEAN MESSAGE
# ==========================================

def clean_message(message):
    parts = []

    # Normal Discord message
    if message.content:
        parts.append(message.content)

    # Embed messages from Lua webhook
    for embed in message.embeds:
        if embed.title:
            parts.append(embed.title)

        if embed.description:
            parts.append(embed.description)

        for field in embed.fields:
            parts.append(f"{field.name}\n{field.value}")

    # Attachments
    for attachment in message.attachments:
        parts.append(attachment.url)

    text = "\n".join(parts).strip()

    # Remove Discord mention syntax
    text = re.sub(r"<@!?[0-9]+>", "", text)
    text = re.sub(r"<@&[0-9]+>", "", text)
    text = re.sub(r"<#[0-9]+>", "", text)

    # Remove empty lines caused by removed mentions
    text = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", text)

    return text.strip()


# ==========================================
# SEND TO FONNTE
# ==========================================

def send_whatsapp(message):
    response = requests.post(
        FONNTE_URL,
        headers={
            "Authorization": API_FONNTE
        },
        data={
            "target": UID_GB2,
            "message": message
        },
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if result.get("status") is not True:
        raise RuntimeError(f"Fonnte error: {result}")

    return result


# ==========================================
# DISCORD EVENTS
# ==========================================

@client.event
async def on_ready():
    logging.info("CoCo Bot connected.")
    logging.info("Bot: %s", client.user)
    logging.info("Channel ID: %s", DISCORD_CHANNEL_ID)
    logging.info("Waiting for new Discord messages...")


@client.event
async def on_message(message):
    # Only read the configured channel
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    # Ignore duplicate events
    if message.id in processed_messages:
        return

    processed_messages.add(message.id)

    # Keep the cache limited
    if len(processed_messages) > 5000:
        processed_messages.clear()
        processed_messages.add(message.id)

    # Do not require a bot mention.
    # Messages from webhooks are also accepted.
    text = clean_message(message)

    if not text:
        logging.info("Empty message skipped: %s", message.id)
        return

    try:
        await asyncio.to_thread(send_whatsapp, text)

        logging.info(
            "Forwarded message %s to WhatsApp.",
            message.id
        )

    except Exception as error:
        logging.error(
            "Failed forwarding message %s: %s",
            message.id,
            error
        )


# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    logging.info("Starting CoCo Discord to WhatsApp...")

    client.run(DISCORD_BOT_TOKEN)
