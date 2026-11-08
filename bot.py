
import os
import time
import logging
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==================================================
# COCO PRODUCTION - WHATSAPP SCHEDULER
# ==================================================

API_FONNTE = os.getenv("API_FONNTE")
UID_GB = os.getenv("UID_GB")
UID_GB2 = os.getenv("UID_GB2")
OWNER_NUMBER = os.getenv("OWNER_NUMBER")

RUN_START_EPOCH = int(
    os.getenv("RUN_START_EPOCH", str(int(time.time())))
)

TIMEZONE = ZoneInfo("Asia/Jakarta")

FONNTE_URL = "https://api.fonnte.com/send"

HEADERS = {
    "Authorization": API_FONNTE
}

# Stop 5 jam 58 menit 30 detik setelah workflow dimulai
BOT_STOP_EPOCH = RUN_START_EPOCH + 5 * 3600 + 58 * 60 + 30

CHECK_INTERVAL = 10
SEND_TOLERANCE = 180

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Menyimpan event yang sudah dikirim selama proses berjalan
sent_messages = set()


# ==================================================
# VALIDATION
# ==================================================

required_secrets = {
    "API_FONNTE": API_FONNTE,
    "UID_GB": UID_GB,
    "UID_GB2": UID_GB2,
    "OWNER_NUMBER": OWNER_NUMBER,
}

for key, value in required_secrets.items():
    if not value:
        raise SystemExit(f"[ERROR] Secret {key} belum diatur!")


# ==================================================
# FONNTE HANDLER
# ==================================================

def send_message(target, message):

    try:
        response = requests.post(
            FONNTE_URL,
            headers=HEADERS,
            data={
                "target": target,
                "message": message
            },
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if result.get("status") is True:
            logging.info(
                "Message sent successfully: %s",
                target
            )
            return True

        logging.error(
            "Fonnte rejected message: %s",
            result
        )

        return False

    except Exception as error:
        logging.error(
            "Failed sending message to %s: %s",
            target,
            error
        )

        return False


def send_to_groups(message, targets):

    success = True

    for target in targets:
        result = send_message(target, message)

        if not result:
            success = False

    return success


# ==================================================
# ACTIVATION - PRIVATE MESSAGE ONLY
# ==================================================

def activate_bot():

    message = (
        "🟢Bot Activated\n"
        "> CoCo Production"
    )

    logging.info("Sending private activation message...")

    if send_message(OWNER_NUMBER, message):
        logging.info("Private activation sent.")
    else:
        logging.error("Private activation failed.")


# ==================================================
# GROUP CONFIGURATION
# ==================================================

ALL_GROUPS = [
    UID_GB
]

PRAYER_GROUPS = [
    UID_GB,
    UID_GB2
]


# ==================================================
# MESSAGE FORMAT
# ==================================================

def prayer_message(title, clock, description):

    return (
        "╭━━━ 🌙 *JADWAL SHOLAT* ━━━╮\n"
        "\n"
        f"🕌 *{title}*\n"
        f"⏰ *{clock} WIB*\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{description}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "Semoga Allah menerima ibadah kita.\n"
        "\n"
        "© CoCo Production"
    )


def announcement_message(title, content):

    return (
        "╭━━━ 📢 *INFORMASI KELAS 7D* ━━━╮\n"
        "\n"
        f"📌 *{title}*\n"
        "\n"
        f"{content}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Mohon diperhatikan dan dilaksanakan.\n"
        "\n"
        "© CoCo Production"
    )


# ==================================================
# PRAYER SCHEDULE
# ==================================================

def get_prayer_events(now):

    weekday = now.weekday()

    events = []

    # Daily prayers

    events.append((
        "04:16",
        "Subuh",
        prayer_message(
            "SHOLAT SUBUH",
            "04.16",
            "Mari kita tunaikan Sholat Subuh tepat waktu.\n"
            "Awali hari dengan ibadah dan doa."
        ),
        PRAYER_GROUPS
    ))

    # Dzuhur: Monday - Thursday, Saturday - Sunday
    # Friday uses special Friday prayer reminder

    if weekday != 4:

        events.append((
            "11:48",
            "Dzuhur",
            prayer_message(
                "SHOLAT DZUHUR",
                "11.48",
                "Waktunya menunaikan Sholat Dzuhur.\n"
                "Jangan lupa untuk melaksanakan sholat."
            ),
            PRAYER_GROUPS
        ))

    events.append((
        "15:07",
        "Ashar",
        prayer_message(
            "SHOLAT ASHAR",
            "15.07",
            "Mari tunaikan Sholat Ashar tepat waktu."
        ),
        PRAYER_GROUPS
    ))

    events.append((
        "17:57",
        "Maghrib",
        prayer_message(
            "SHOLAT MAGHRIB",
            "17.57",
            "Waktunya Sholat Maghrib.\n"
            "Jangan lupa berdoa dan membaca Al-Qur'an."
        ),
        PRAYER_GROUPS
    ))

    events.append((
        "19:09",
        "Isya",
        prayer_message(
            "SHOLAT ISYA",
            "19.09",
            "Mari tunaikan Sholat Isya.\n"
            "Semoga ibadah kita mendapatkan pahala."
        ),
        PRAYER_GROUPS
    ))

    # Friday special schedules

    if weekday == 4:

        events.append((
            "06:30",
            "Dhuha Jumat",
            prayer_message(
                "SHOLAT DHUHA",
                "06.30",
                "Jangan lupa melaksanakan Sholat Dhuha.\n"
                "Semoga menjadi amal kebaikan dan pahala jariyah."
            ),
            PRAYER_GROUPS
        ))

        events.append((
            "11:30",
            "Sholat Jumat",
            (
                "╭━━━ 🕌 *PENGINGAT SHOLAT JUMAT* ━━━╮\n"
                "\n"
                "🕋 *SHOLAT JUMAT*\n"
                "⏰ *11.30 WIB*\n"
                "\n"
                "Kepada seluruh laki-laki Muslim,\n"
                "jangan lupa menunaikan Sholat Jumat.\n"
                "\n"
                "Persiapkan diri dan berangkatlah ke masjid.\n"
                "\n"
                "Semoga ibadah kita diterima Allah SWT.\n"
                "\n"
                "© CoCo Production"
            ),
            PRAYER_GROUPS
        ))

    return events


# ==================================================
# SCHOOL TIMETABLE
# ==================================================

SCHOOL_SCHEDULE = {
    0: [
        "TIK",
        "Bahasa Lampung",
        "Bahasa Inggris",
        "Bahasa Indonesia"
    ],

    1: [
        "Matematika",
        "IPS",
        "SB",
        "IPA"
    ],

    2: [
        "Bahasa Indonesia",
        "PPKN",
        "PAI"
    ],

    3: [
        "IPS",
        "IPA",
        "Bahasa Inggris",
        "Matematika"
    ],

    4: [
        "PJOK",
        "BK"
    ]
}


def timetable_message(now):

    days = [
        "Senin",
        "Selasa",
        "Rabu",
        "Kamis",
        "Jumat"
    ]

    subjects = SCHOOL_SCHEDULE[now.weekday()]

    lines = []

    for index, subject in enumerate(subjects, 1):
        lines.append(
            f"{index}. {subject}"
        )

    return (
        "╭━━━ 📚 *JADWAL PELAJARAN 7D* ━━━╮\n"
        "\n"
        f"📅 *Hari: {days[now.weekday()]}*\n"
        "⏰ *05.00 WIB*\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "\n"
        + "\n".join(lines)
        + "\n\n"
        "Selamat belajar!\n"
        "Jangan lupa mempersiapkan perlengkapan sekolah.\n"
        "\n"
        "© CoCo Production"
    )


# ==================================================
# CLASS ANNOUNCEMENTS
# ==================================================

def get_class_events(now):

    weekday = now.weekday()

    events = []

    # Tuesday - General duty

    if weekday == 1:

        events.append((
            "06:00",
            "Piket Umum",
            announcement_message(
                "PIKET UMUM KELAS 7D",
                "Hari ini jadwal Piket Umum.\n"
                "Seluruh petugas piket harap melaksanakan "
                "tugasnya dengan baik."
            )
        ))

    # Wednesday - Class cash

    if weekday == 2:

        events.append((
            "06:00",
            "Kas Kelas",
            announcement_message(
                "PEMBAYARAN KAS KELAS 7D",
                "Jangan lupa membayar kas kelas sebesar:\n\n"
                "💰 *Rp2.000*\n\n"
                "Bawalah uang tambahan untuk membayar "
                "kepada bendahara kelas."
            )
        ))

    # Thursday - Nail checking

    if weekday == 3:

        events.append((
            "06:00",
            "Pengecekan Kuku",
            announcement_message(
                "PENGECEKAN KUKU KELAS 7D",
                "Hari ini akan dilakukan pengecekan kuku.\n\n"
                "✂️ Pastikan kuku sudah dipotong dan bersih.\n"
                "💰 Denda kuku panjang: *Rp2.000*"
            )
        ))

    return events


# ==================================================
# EVENT SCHEDULER
# ==================================================

def event_key(now, event_name):

    return (
        now.strftime("%Y-%m-%d"),
        event_name
    )


def is_event_time(now, scheduled_time):

    hour, minute = map(
        int,
        scheduled_time.split(":")
    )

    scheduled = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    difference = (
        now - scheduled
    ).total_seconds()

    return 0 <= difference <= SEND_TOLERANCE


def process_event(now, event_name, scheduled_time, message, targets):

    key = event_key(now, event_name)

    if key in sent_messages:
        return

    if not is_event_time(now, scheduled_time):
        return

    logging.info(
        "Event triggered: %s",
        event_name
    )

    success = send_to_groups(
        message,
        targets
    )

    if success:
        sent_messages.add(key)
        logging.info(
            "Event completed: %s",
            event_name
        )


# ==================================================
# MAIN SCHEDULER
# ==================================================

def run_scheduler():

    logging.info("CoCo Production WhatsApp Scheduler started.")

    activate_bot()

    while time.time() < BOT_STOP_EPOCH:

        now = datetime.now(TIMEZONE)

        # Prayer notifications

        for scheduled_time, name, message, targets in get_prayer_events(now):

            process_event(
                now,
                name,
                scheduled_time,
                message,
                targets
            )

        # School timetable

        if now.weekday() <= 4:

            process_event(
                now,
                "Jadwal Pelajaran",
                "05:00",
                timetable_message(now),
                ALL_GROUPS
            )

        # Class announcements

        for scheduled_time, name, message in get_class_events(now):

            process_event(
                now,
                name,
                scheduled_time,
                message,
                ALL_GROUPS
            )

        remaining = BOT_STOP_EPOCH - time.time()

        if remaining <= 0:
            break

        time.sleep(
            min(CHECK_INTERVAL, remaining)
        )

    logging.info("CoCo Production Scheduler stopped.")
    logging.info("Ready for workflow restart.")


# ==================================================
# ENTRY POINT
# ==================================================

if __name__ == "__main__":

    print("====================================")
    print("       COCO PRODUCTION")
    print("       WHATSAPP SCHEDULER")
    print("====================================")

    run_scheduler()
