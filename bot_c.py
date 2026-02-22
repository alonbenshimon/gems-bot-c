import os
import time
import requests

BOT_TOKEN = os.environ.get("BOT_C_TOKEN", "").strip()
BASE_OKX = "https://www.okx.com"

def tg_api(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    requests.post(url, data=data, timeout=20)

def get_spot_instruments():
    try:
        r = requests.get(f"{BASE_OKX}/api/v5/public/instruments?instType=SPOT", timeout=20)
        return r.json().get("data", [])
    except:
        return []

def get_base_quote(base):
    instruments = get_spot_instruments()
    quotes = []
    for inst in instruments:
        inst_id = inst.get("instId", "")
        if inst_id.startswith(base + "-"):
            quotes.append(inst_id.split("-")[1])
    return sorted(set(quotes))

def get_quote_base(base):
    instruments = get_spot_instruments()
    bases = []
    for inst in instruments:
        inst_id = inst.get("instId", "")
        if inst_id.endswith("-" + base):
            bases.append(inst_id.split("-")[0])
    return sorted(set(bases))

def handle_message(text):
    parts = text.strip().lower().split()
    if not parts:
        return None

    base = parts[0].upper()

    # מצב 1: btc
    if len(parts) == 1:
        return f"OKX STATUS – {base}\n\n• Spot: live"

    # מצב 2: btc pairs
    if len(parts) == 2 and parts[1] == "pairs":
        quotes = get_base_quote(base)
        if not quotes:
            return f"No spot pairs found for {base}"
        return f"{base} Spot Pairs:\n" + ", ".join(quotes)

    # מצב 3: btc all
    if len(parts) == 2 and parts[1] == "all":
        quotes = get_base_quote(base)
        bases = get_quote_base(base)

        if not quotes and not bases:
            return f"No spot data found for {base}"

        reply = f"{base} Spot Market Overview\n\n"

        if quotes:
            reply += "Base → Quote:\n"
            reply += ", ".join(quotes) + "\n\n"

        if bases:
            reply += "Quote → Base:\n"
            reply += ", ".join(bases)

        return reply

    return None

def main():
    if not BOT_TOKEN:
        print("Missing BOT_C_TOKEN")
        return

    offset = 0
    while True:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"timeout": 25, "offset": offset},
            timeout=35
        )
        data = r.json()

        for upd in data.get("result", []):
            offset = max(offset, upd.get("update_id", 0) + 1)
            msg = upd.get("message") or {}
            chat_id = msg.get("chat", {}).get("id")
            text = (msg.get("text") or "").strip()

            if not chat_id or not text:
                continue

            reply = handle_message(text)
            if reply:
                tg_api("sendMessage", {"chat_id": chat_id, "text": reply})

        time.sleep(0.5)

if __name__ == "__main__":
    main()

# ================= PRIVATE OKX TEST =================

import base64
import hmac
import hashlib
import datetime

OKX_API_KEY = os.environ.get("OKX_API_KEY", "").strip()
OKX_SECRET = os.environ.get("OKX_SECRET", "").strip()
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE", "").strip()

def okx_private_headers(method, path, body=""):
    timestamp = datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    message = timestamp + method + path + body
    mac = hmac.new(OKX_SECRET.encode(), message.encode(), hashlib.sha256)
    sign = base64.b64encode(mac.digest()).decode()

    return {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "Content-Type": "application/json"
    }

def test_okx_private_connection():
    path = "/api/v5/account/balance"
    headers = okx_private_headers("GET", path)
    r = requests.get(BASE_OKX + path, headers=headers, timeout=20)
    return r.status_code


if __name__ == "__main__":
    print("Bot-C started...")
    while True:
        try:
            status = test_okx_private_connection()
            print("OKX status:", status)
        except Exception as e:
            print("Error:", e)
        time.sleep(30)

