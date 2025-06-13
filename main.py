import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI, OpenAIError
import datetime

# Inizializza FastAPI
app = FastAPI()

# Leggi le variabili d'ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise RuntimeError("❌ OPENAI_API_KEY o ASSISTANT_ID non trovati.")

# Inizializza il client OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello della richiesta
class ChatRequest(BaseModel):
    thread_id: str
    message: str

@app.get("/start")
async def start_conversation():
    print("🚀 [START] Richiesta nuovo thread")
    try:
        thread = client.beta.threads.create()
        print(f"✅ [THREAD] ID generato: {thread.id}")
        return {"thread_id": thread.id}
    except Exception as e:
        print(f"❌ [ERRORE THREAD] {e}")
        raise HTTPException(status_code=500, detail="Errore nella creazione del thread")

@app.post("/chat")
async def chat(chat_request: ChatRequest):
    now = datetime.datetime.now().isoformat()
    print(f"\n💬 [RICHIESTA] {now}")
    print(f"📎 Thread ID: {chat_request.thread_id}")
    print(f"✉️ Messaggio: {chat_request.message}")

    if not chat_request.thread_id or not chat_request.message:
        raise HTTPException(status_code=400, detail="thread_id e message sono obbligatori")

    try:
        client.beta.threads.messages.create(
            thread_id=chat_request.thread_id,
            role="user",
            content=chat_request.message
        )
        print("📥 [MESSAGGIO] Inviato al thread")

        run = client.beta.threads.runs.create(
            thread_id=chat_request.thread_id,
            assistant_id=ASSISTANT_ID
        )
        print(f"🏃 [RUN] Avviata con ID: {run.id}")

        for i in range(30):  # Attendi fino a 30 secondi
            status = client.beta.threads.runs.retrieve(
                thread_id=chat_request.thread_id,
                run_id=run.id
            )
            print(f"⏳ [{i+1}s] Stato: {status.status}")
            if status.status == "completed":
                print("✅ [RUN] Completata")
                break
            elif status.status in ["failed", "cancelled"]:
                raise HTTPException(status_code=500, detail="Run fallita o annullata")
            await asyncio.sleep(1)

        messages = client.beta.threads.messages.list(thread_id=chat_request.thread_id)
        if not messages.data:
            raise HTTPException(status_code=500, detail="Nessuna risposta trovata")

        risposta = messages.data[0].content[0].text.value
        print(f"🤖 [RISPOSTA] {risposta}")
        return {"response": risposta}

    except OpenAIError as oe:
        print(f"❌ [OpenAI ERROR] {oe}")
        raise HTTPException(status_code=500, detail="Errore OpenAI")

    except Exception as e:
        print(f"❌ [GENERIC ERROR] {e}")
        raise HTTPException(status_code=500, detail="Errore interno nel backend")
