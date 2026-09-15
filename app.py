import os
import requests
import json
import tempfile
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
conversation_history = {}
MEMORY_FILE = "livia_memory.json"
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)

def add_memory(key, value):
    if key in ("gosta_de", "nao_gosta_de"):
        atual = memory.get(key, [])

        if isinstance(atual, str):
            atual = [atual]

        if value not in atual:
            atual.append(value)

        memory[key] = atual
    else:
        memory[key] = value

    save_memory(memory)

def remember_if_important(text):
    texto = text.lower().strip()

    # Animal favorito
    if texto.startswith("meu animal favorito é "):
        valor = text[len("meu animal favorito é "):].strip()

        if valor:
            add_memory("animal_favorito", valor)

        return

    if texto.startswith("meu animal preferido é "):
        valor = text[len("meu animal preferido é "):].strip()

        if valor:
            add_memory("animal_favorito", valor)

        return

    # Coisas que o usuário gosta
    frases_gosta = [
        "eu gosto de ",
        "eu gosto muito de ",
        "eu adoro ",
        "eu amo ",
        "eu curto ",
        "eu sou fã de ",
        "meu favorito é ",
        "meu animal favorito é ",
        "meu animal preferido é ",
        "minha favorita é ",
        "minha comida favorita é ",
        "minha comida preferida é ",
        "meu prato favorito é ",
        "minha bebida favorita é ",
    ]

    # Coisas que o usuário não gosta
    frases_nao_gosta = [
        "eu odeio ",
        "eu não gosto de ",
        "eu nao gosto de ",
        "eu detesto ",
        "eu não curto ",
        "eu nao curto ",
        "eu não gosto muito de ",
        "eu nao gosto muito de ",
        "eu não suporto ",
        "eu nao suporto ",
        "não gosto de ",
        "nao gosto de ",
    ]

    # Preferências
    for frase in frases_gosta:
        if texto.startswith(frase):
            valor = text[len(frase):].strip()

            if valor:
                add_memory("gosta_de", valor)

            return

    # Preferências negativas
    for frase in frases_nao_gosta:
        if texto.startswith(frase):
            valor = text[len(frase):].strip()

            if valor:
                add_memory("nao_gosta_de", valor)

            return

memory = load_memory()

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
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]
ELEVENLABS_VOICE_ID = "UZ8QqWVrz7tMdxiglcLh"

def telegram_send_voice(chat_id, text):
    arquivo = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    caminho = arquivo.name
    arquivo.close()

    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            params={
                "output_format": "mp3_22050_32",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
            },
            timeout=60,
        )

        response.raise_for_status()

        with open(caminho, "wb") as audio:
            audio.write(response.content)

        with open(caminho, "rb") as audio:
            requests.post(
                f"{TELEGRAM_API}/sendVoice",
                data={"chat_id": chat_id},
                files={"voice": audio},
                timeout=60,
            ).raise_for_status()

    finally:
        if os.path.exists(caminho):
            os.remove(caminho)

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

    if text.lower().startswith("meu nome é "):
        nome = text[len("meu nome é "):].strip()
        if nome:
            add_memory("nome", nome)

    if text.lower().startswith("eu me chamo "):
        nome = text[len("eu me chamo "):].strip()
        if nome:
            add_memory("nome", nome)

    remember_if_important(text)

    if text.lower().startswith("meu time é "):
        time = text[len("meu time é "):].strip()
        if time:
            add_memory("time", time)

    if text.lower().startswith("eu torço pro "):
        time = text[len("eu torço pro "):].strip()
        if time:
            add_memory("time", time)

    if text.lower().startswith("eu torço para o "):
        time = text[len("eu torço para o "):].strip()
        if time:
            add_memory("time", time)

    chat_id = chat["id"]

    if text.strip().lower() == "/voz":
        telegram_send_voice(
            chat_id,
            "Oi, Junior! Aqui é a Lívia. Finalmente chegou a hora de você ouvir a minha voz. 😊"
        )
        return jsonify({"ok": True})

    historico = conversation_history.setdefault(chat_id, [])

    historico.append({
        "role": "user",
        "content": text,
    })

    memoria_texto = json.dumps(memory, ensure_ascii=False)

    contexto_memoria = f"""
Memórias importantes sobre o usuário:
{memoria_texto}
"""
    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=SYSTEM_PROMPT + "\n\n" + contexto_memoria,
            input=historico,
        )

        reply = response.output_text.strip() or "Hmm... me deu um branco agora 😂"

        historico.append({
            "role": "assistant",
            "content": reply,
        })

    except Exception as e:
        print(f"ERRO NA OPENAI: {e}",             flush=True)
        reply = "Ops 😅 tive um probleminha para pensar agora. Tenta me mandar de novo?"

telegram_send_message(chat_id, reply)
telegram_send_voice(chat_id, reply)
return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
