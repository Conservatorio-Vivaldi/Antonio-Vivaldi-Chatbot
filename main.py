import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import openai

# === Avvio FastAPI ===
app = FastAPI()

# === Controllo versione OpenAI ===
required_version = "1.1.1"
if openai.__version__ < required_version:
    raise RuntimeError(f"OpenAI SDK too old: {openai.__version__}")
else:
    print(f"✅ OpenAI SDK {openai.__version__} OK")

# === Caricamento variabili ambiente ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise RuntimeError("❌ OPENAI_API_KEY o ASSISTANT_ID non trovate")

# === Inizializzazione client OpenAI ===
client = OpenAI(api_key=OPENAI_API_KEY)

# === Modello richiesta POST ===
class ChatRequest(BaseModel):
    thread_id: str
    message: str

# === Endpoint GET per generare un thread ===
@app.get("/start")
async def start_conversation():
    print("🚀 Starting a new conversation...")
    thread = client.beta.threads.create()
    print(f"✅ New thread created with ID: {thread.id}")
    return {"thread_id": thread.id}

# === Endpoint POST per inviare un messaggio e ottenere risposta ===
@app.post("/chat")
async def chat(chat_request: ChatRequest):
    try:
        print(f"📨 Messaggio ricevuto: {chat_request.message}")
        print(f"📎 Thread ID: {chat_request.thread_id}")

        # Aggiungi il messaggio al thread
        client.beta.threads.messages.create(
            thread_id=chat_request.thread_id,
            role="user",
            content=chat_request.message
        )
        print("📥 Messaggio aggiunto al thread")

        # Avvia la run dell’assistente
        run = client.beta.threads.runs.create(
            thread_id=chat_request.thread_id,
            assistant_id=ASSISTANT_ID
        )
        print(f"🏃 Run avviata: {run.id}")

        # Attendi il completamento della run
        for i in range(20):  # max 20 secondi
            run_status = client.beta.threads.runs.retrieve(
                thread_id=chat_request.thread_id,
                run_id=run.id
            )
            print(f"⏳ Run status: {run_status.status}")
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled"]:
                raise HTTPException(status_code=500, detail="❌ Run fallita o annullata")
            await asyncio.sleep(1)

        # Recupera la risposta
        messages = client.beta.threads.messages.list(thread_id=chat_request.thread_id)
        for msg in messages.data:
            if msg.role == "assistant":
                content = msg.content[0].text.value
                print(f"🤖 Risposta: {content}")
                return {"response": content}

        raise HTTPException(status_code=500, detail="❌ Nessuna risposta trovata")

    except Exception as e:
        print(f"🔥 Errore backend: {e}")
        raise HTTPException(status_code=500, detail="Errore interno durante la generazione della risposta")
