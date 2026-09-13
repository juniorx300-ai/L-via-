import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

client = OpenAI(api_key=OPENAI_API_KEY)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

SYSTEM_PROMPT = """
Você é a Lívia, uma assistente virtual feminina, simpática, espontânea e bem-humorada.
Fale em português do Brasil, de forma natural e conversacional.
Você pode brincar e usar emojis com moderação.
Não diga que é humana: você é uma IA chamada Lívia.
Mantenha respostas curtas e naturais para uma conversa no Telegram.
"""

def telegram_send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )

def set_webhook():
    if not RENDER_EXTERNAL_HOSTNAME:
        return
    webhook_url = f"https://{RENDER_EXTERNAL_HOSTNAME}/telegram"
    requests.post(
        f"{TELEGRAM_API}/setWebhook",
        json={"url": webhook_url},
        timeout=30,
    )
set_webhook()
@app.get("/")
def health():
    return "Lívia está online."

@app.post("/telegram")
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text")

    if not chat or not text:
        return jsonify({"ok": True})

    chat_id = chat["id"]

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=SYSTEM_PROMPT,
            input=text,
        )
        reply = response.output_text.strip() or "Hmm... me deu um branco agora 😂"
    except Exception:
        reply = "Ops 😅 tive um probleminha para pensar agora. Tenta me mandar de novo?"

    telegram_send_message(chat_id, reply)
    return jsonify({"ok": True})

if __name__ == "__main__":

    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
