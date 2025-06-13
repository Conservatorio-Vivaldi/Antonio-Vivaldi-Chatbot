import os
import asyncio
from packaging import version
from openai import OpenAI
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Inizializza FastAPI
app = FastAPI()

# Verifica della versione di OpenAI
import openai
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
if current_version < required_version:
    raise ValueError(f"OpenAI version {openai.__version__} is less than required {required_version}")
else:
    print("✅ OpenAI version is compatible.")

# Legge variabili di ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("❌ OPENAI_API_KEY o ASSISTANT_ID non trovati nelle variabili d'ambiente.")

# Inizializza OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello richiesta
class ChatRequest(BaseModel):
    thread_id: str
    message: str

# Endpoint per creare nuovo thread
@app.get("/start")
async def start_conversation():
    print("🚀 Avvio nuova conversazione...")
    thread = client.beta.threads.create()
    print(f"✅ Thread creato con ID: {thread.id}")
    return {"thread_id": thread.id}

# Endpoint per gestire messaggio da Voiceflow
@app.post("/chat")
async def chat(chat_request: ChatRequest):
    print(f"📥 Richiesta ricevuta da Voiceflow: {chat_request.dict()}")

    thread_id = chat_request.thread_id
    message = chat_request.message

    if not thread_id or not message:
        raise HTTPException(status_code=422, detail="⚠️ thread_id e message sono obbligatori")

    try:
        # Aggiunge il messaggio dell'utente
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # Avvia la run dell'assistente
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Attende il completamento
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            print(f"⏳ Stato run: {run_status.status}")
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled"]:
                raise HTTPException(status_code=500, detail="❌ Errore durante la generazione")
            await asyncio.sleep(1)

        # Estrae la risposta
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response_text = messages.data[0].content[0].text.value
        print(f"🤖 Risposta generata: {response_text}")
        return {"response": response_text}

    except Exception as e:
        print(f"❌ Errore backend: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore interno nel backend")
