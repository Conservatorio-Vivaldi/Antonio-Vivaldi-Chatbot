import os
import asyncio
from packaging import version
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Inizializza FastAPI
app = FastAPI()

# Verifica della versione di OpenAI
import openai
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
if current_version < required_version:
    raise ValueError(f"Error: OpenAI version {openai.__version__} is less than required {required_version}")
else:
    print("✅ OpenAI version is compatible.")

# Legge le chiavi dall'ambiente
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("❌ OPENAI_API_KEY o ASSISTANT_ID mancanti.")

# Inizializza OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello per le richieste
class ChatRequest(BaseModel):
    thread_id: str
    message: str

# Creazione thread
@app.get("/start")
async def start_conversation():
    print("🚀 Starting a new conversation...")
    thread = client.beta.threads.create()
    print(f"✅ New thread created with ID: {thread.id}")
    return {"thread_id": thread.id}

# Generazione risposta
@app.post("/chat")
async def chat(chat_request: ChatRequest):
    try:
        print("📥 Ricevuto payload:", chat_request.dict())

        thread_id = chat_request.thread_id
        user_input = chat_request.message

        if not thread_id or not user_input:
            raise HTTPException(status_code=400, detail="❌ thread_id o message mancanti")

        print(f"✉️ Messaggio: '{user_input}' | Thread ID: {thread_id}")

        # Inserisce il messaggio
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )
        print("📩 Messaggio aggiunto al thread.")

        # Crea la run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        print(f"🏃 Run avviata (ID: {run.id})")

        # Attende completamento
        max_wait = 15
        waited = 0
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            print(f"⏳ Stato run: {run_status.status}")
            if run_status.status == "completed":
                print("✅ Run completata.")
                break
            elif run_status.status in ["failed", "cancelled"]:
                print("❌ Run fallita o annullata.")
                raise HTTPException(status_code=500, detail="Run fallita.")
            await asyncio.sleep(1)
            waited += 1
            if waited >= max_wait:
                raise HTTPException(status_code=504, detail="Timeout attesa run")

        # Recupera i messaggi
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        print(f"📤 Messaggi ricevuti (n={len(messages.data)}):")
        for i, msg in enumerate(messages.data):
            try:
                content = msg.content[0].text.value
                print(f"- [{i}] {msg.role}: {content}")
            except Exception as e:
                print(f"- [{i}] Errore parsing messaggio: {e}")

        # Trova l'ultima risposta dell'assistente
        for msg in messages.data:
            if msg.role == "assistant" and msg.content:
                try:
                    response_text = msg.content[0].text.value.strip()
                    print(f"✅ Assistant response: {response_text}")
                    return {"response": response_text}
                except Exception as e:
                    print(f"⚠️ Errore estrazione testo: {e}")

        print("❌ Nessuna risposta trovata dall’assistente.")
        raise HTTPException(status_code=500, detail="Risposta assistente non disponibile")

    except Exception as e:
        print(f"❗ Errore backend: {e}")
        raise HTTPException(status_code=500, detail="Errore interno durante la generazione della risposta")
