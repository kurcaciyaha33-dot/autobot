import os
import time
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# CONFIG
# ==========================================

WIB = ZoneInfo("Asia/Jakarta")

API_FONNTE = os.getenv("API_FONNTE")
UID_GB = os.getenv("UID_GB")

FONNTE_URL = "https://api.fonnte.com/send"

CHECK_INTERVAL = 10
SEND_TOLERANCE = 180

# Waktu mulai workflow dicatat oleh run.yml
RUN_START_EPOCH = int(os.getenv("RUN_START_EPOCH", time.time()))

# Bot berhenti 30 detik sebelum Step 4 selesai
BOT_STOP_EPOCH = RUN_START_EPOCH + (5 * 3600) + (58 * 60) + 30

# ==========================================
# VALIDASI
# ==========================================

if not API_FONNTE:
    raise SystemExit("API_FONNTE belum diatur!")

if not UID_GB:
    raise SystemExit("UID_GB belum diatur!")

# ==========================================
# FONNTE SENDER
# ==========================================

def send_message(message):
    try:
        response = requests.post(
            FONNTE_URL,
            headers={
                "Authorization": API_FONNTE
            },
            data={
                "target": UID_GB,
                "message": message
            },
            timeout=30
        )

        result = response.json()

        if response.ok and result.get("status") is True:
            print("[SUCCESS] Pesan berhasil dikirim.")
            return True

        print("[FAILED]", result)
        return False

    except Exception as error:
        print("[ERROR]", str(error))
        return False

# ==========================================
# ACTIVATION MESSAGE
# ==========================================

def activate_bot():
    print("[INFO] Mengirim pesan aktivasi...")

    send_message(
        "🟢Bot Activated\n"
        "> CoCo Production"
    )

# ==========================================
# SHOLAT MESSAGE
# ==========================================

def sholat_message(nama, waktu, sholat):
    return (
        f"Jadwal Sholat {nama}\n\n"
        f"Pukul:\n"
        f"{waktu} WIB\n\n"
        f"*Segeralah Berwudhu dan menunaikan Shalat {sholat}*\n"
        f"*Karena sesiapa yang sholat akan mendapat pahala dan nikmat*"
    )

def get_messages(now):

    weekday = now.weekday()
    messages = []

    # ======================================
    # SUBUH - SETIAP HARI
    # ======================================

    messages.append((
        "04:00",
        "Jadwal Sholat Subuh\n\n"
        "Pukul:\n"
        "04.00 WIB\n\n"
        "*Segeralah bangun dan Berwudhu lalu menunaikan Shalat Subuh*\n"
        "*Karena sesiapa yang sholat akan mendapat pahala dan nikmat*"
    ))

    # ======================================
    # DUHUR - KECUALI JUMAT
    # ======================================

    if weekday != 4:
        messages.append((
            "12:00",
            sholat_message("Duhur", "12.00", "Duhur")
        ))

    # ======================================
    # JUMAT
    # ======================================

    if weekday == 4:

        messages.append((
            "06:30",
            "Jadwal Sholat Dhuha 7D\n\n"
            "Pukul:\n"
            "06.30 WIB\n\n"
            "*Segeralah berangkat dan menunaikan Shalat Dhuha bersama*\n"
            "*Karena sesiapa yang sholat akan mendapat pahala dan nikmat*"
        ))

        messages.append((
            "11:30",
            "Jadwal Sholat Jumat bagi para laki-laki\n\n"
            "Pukul:\n"
            "11.30 WIB\n\n"
            "*Segeralah Mandi dan menunaikan Shalat Jumat*\n"
            "*Karena sesiapa yang sholat akan mendapat pahala dan nikmat*"
        ))

    # ======================================
    # ASHAR
    # ======================================

    messages.append((
        "15:00",
        sholat_message("Ashar", "15.00", "Ashar")
    ))

    # ======================================
    # MAGHRIB
    # ======================================

    messages.append((
        "18:00",
        sholat_message("Maghrib", "18.00", "Maghrib")
    ))

    # ======================================
    # ISYA
    # ======================================

    messages.append((
        "19:00",
        sholat_message("Isya", "19.00", "Isya")
    ))

    # ======================================
    # SELASA - PIKET UMUM
    # ======================================

    if weekday == 1:
        messages.append((
            "06:00",
            "Diinformasikan bahwasanya hari ini adalah jadwal piket umum Kelas 7D\n\n"
            "*Segeralah berangkat dan melaksanakan Piket Umum*\n"
            "*Sesiapa yang melakukan tugas lebih cepat, akan mendapatkan pahal jariyah*"
        ))

    # ======================================
    # RABU - KAS
    # ======================================

    if weekday == 2:
        messages.append((
            "06:00",
            "Diinformasikan bahwasanya hari ini adalah jadwal kas Kelas 7D\n\n"
            "*Biaya sekitar Rp2.000*\n"
            "*Membawa uang lebih untuk membayarnya pada Bendahara kelas*"
        ))

    # ======================================
    # KAMIS - PENGECEKAN KUKU
    # ======================================

    if weekday == 3:
        messages.append((
            "06:00",
            "Diinformasikan bahwasanya hari ini adalah jadwal pengecekan kuku Kelas 7D\n\n"
            "*Potonglah kuku mu sesuai Sunnah Rasulullah Saw.*\n"
            "*Jangan panjangkan kuku mu, karena dapat menjadi sarang iblis*\n"
            "*Sesiapa yang kukunya panjang akan dikenakan denda sebesar Rp2.000 dibayarkan pada Bendahara*"
        ))

    # ======================================
    # JADWAL PELAJARAN
    # SETIAP HARI JAM 05.00
    # ======================================

    lessons = {
        0: {
            "day": "Senin",
            "subjects": [
                "TIK",
                "B.Lampung",
                "B.Inggris",
                "B.Indonesia"
            ]
        },
        1: {
            "day": "Selasa",
            "subjects": [
                "MTK",
                "IPS",
                "SB",
                "IPA"
            ]
        },
        2: {
            "day": "Rabu",
            "subjects": [
                "B.Indonesia",
                "PPKN",
                "PAI"
            ]
        },
        3: {
            "day": "Kamis",
            "subjects": [
                "IPS",
                "IPA",
                "B.Inggris",
                "MTK"
            ]
        },
        4: {
            "day": "Jumat",
            "subjects": [
                "PJOK",
                "BK"
            ]
        }
    }

    if weekday in lessons:

        data = lessons[weekday]

        subject_text = "\n".join(
            f"• {subject}"
            for subject in data["subjects"]
        )

        lesson_message = (
            "Jadwal Pelajaran Kelas 7D\n\n"
            f"*Hari: {data['day']}*\n"
            "Mata Pelajaran:\n"
            f"{subject_text}"
        )

        messages.append((
            "05:00",
            lesson_message
        ))

    return messages

# ==========================================
# SCHEDULER
# ==========================================

def scheduler():

    sent_messages = set()

    print("[INFO] Scheduler aktif.")
    print("[INFO] Timezone: Asia/Jakarta")

    while time.time() < BOT_STOP_EPOCH:

        now = datetime.now(WIB)
        today = now.strftime("%Y-%m-%d")

        for scheduled_time, message in get_messages(now):

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

            message_id = f"{today}_{scheduled_time}"

            if (
                0 <= difference <= SEND_TOLERANCE
                and message_id not in sent_messages
            ):

                print(
                    f"[SENDING] {scheduled_time} WIB"
                )

                if send_message(message):
                    sent_messages.add(message_id)

        time.sleep(CHECK_INTERVAL)

    print("[INFO] Waktu bot selesai.")
    print("[INFO] Melanjutkan ke Step 4 dan Step 5.")

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print("====================================")
    print("       WHATSAPP MESSAGE BOT")
    print("          COCO PRODUCTION")
    print("====================================")

    activate_bot()

    scheduler()