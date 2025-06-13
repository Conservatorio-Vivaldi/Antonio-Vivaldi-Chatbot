import os
import asyncio
from packaging import version
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import datetime

# Inizializza FastAPI
app = FastAPI()

# Verifica versione OpenAI
import openai
required_version = version.parse("1.1.1")
current_version = version.parse(openai.__version__)
print(f"[DEBUG] OpenAI versione installata: {openai.__version__}")
if current_version < required_version:
    raise ValueError(f"[ERRORE] Versione OpenAI troppo vecchia: {openai.__version__} < {required_version}")
else:
    print("[OK] Versione OpenAI compatibile.")

# Variabili ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

print(f"[DEBUG] OPENAI_API_KEY presente: {bool(OPENAI_API_KEY)}")
print(f"[DEBUG] ASSISTANT_ID presente: {bool(ASSISTANT_ID)}")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("[FATAL] Variabili d'ambiente mancanti (OPENAI_API_KEY o ASSISTANT_ID)")

# Inizializza OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello per input
class ChatRequest(BaseModel):
    thread_id: str
    message: str

# Nuova conversazione
@app.get("/start")
async def start_conversation():
    print("\n[START] Nuova conversazione richiesta")
    thread = client.beta.threads.create()
    print(f"[OK] Thread creato: {thread.id}")
    return {"thread_id": thread.id}

# Invio messaggio e generazione risposta
@app.post("/chat")
async def chat(chat_request: ChatRequest):
    request_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    print(f"\n[REQUEST] {request_id} @ {timestamp}")
    print(f"[INPUT] thread_id: {chat_request.thread_id}")
    print(f"[INPUT] message: {chat_request.message}")

    if not chat_request.thread_id or not chat_request.message:
        raise HTTPException(status_code=422, detail="Parametri mancanti")

    try:
        print("[STEP 1] Inserimento messaggio...")
        result = client.beta.threads.messages.create(
            thread_id=chat_request.thread_id,
            role="user",
            content=chat_request.message
        )
        print(f"[OK] Messaggio aggiunto con ID: {result.id}")

        print("[STEP 2] Avvio run assistente...")
        run = client.beta.threads.runs.create(
            thread_id=chat_request.thread_id,
            assistant_id=ASSISTANT_ID
        )
        print(f"[OK] Run avviata con ID: {run.id}")

        print("[STEP 3] Attesa completamento...")
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=chat_request.thread_id,
                run_id=run.id
            )
            print(f"[WAIT] Stato attuale run: {run_status.status}")
            if run_status.status == "completed":
                print("[OK] Run completata.")
                break
            elif run_status.status in ["failed", "cancelled"]:
                print("[FAIL] Run fallita o annullata.")
                raise HTTPException(status_code=500, detail="Errore nella generazione")
            await asyncio.sleep(1)

        print("[STEP 4] Recupero messaggi...")
        messages = client.beta.threads.messages.list(thread_id=chat_request.thread_id)
        print(f"[INFO] Numero messaggi nel thread: {len(messages.data)}")

        for idx, msg in enumerate(messages.data):
            try:
                content = msg.content[0].text.value
                print(f"[MSG {idx}] Role: {msg.role}, Content: {content}")
            except Exception as e:
                print(f"[WARN] Impossibile leggere il contenuto del messaggio #{idx}: {e}")

        if not messages.data:
            raise HTTPException(status_code=500, detail="Nessun messaggio generato")

        response_text = messages.data[0].content[0].text.value
        print(f"[RESPONSE] Risposta assistente: {response_text}")
        return {"response": response_text}

    except openai.OpenAIError as oe:
        print(f"[ERR-OPENAI] {oe}")
        raise HTTPException(status_code=500, detail=f"Errore OpenAI: {str(oe)}")

    except Exception as e:
        print(f"[ERR] Errore generico: {e}")
        raise HTTPException(status_code=500, detail="Errore interno nel backend")
