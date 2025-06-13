import os
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
    raise ValueError(f"Error: OpenAI version {openai.__version__} "
                     "is less than required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# Legge le chiavi dall'ambiente
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Inizializza il client OpenAI (non ancora usato in questa versione di test)
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello per le richieste
class ChatRequest(BaseModel):
    thread_id: str
    message: str

# Endpoint di prova per la root (facoltativo)
@app.get("/")
def root():
    return {"status": "API online"}

# Endpoint per iniziare una nuova conversazione
@app.get("/start")
async def start_conversation():
    print("Starting a new conversation...")
    thread = client.beta.threads.create()
    print(f"New thread created with ID: {thread.id}")
    return {"thread_id": thread.id}

# Endpoint di test per ricevere e confermare i dati
@app.post("/chat")
async def chat(chat_request: ChatRequest):
    print("DEBUG >> Richiesta ricevuta da Voiceflow:")
    print(chat_request.dict())

    return {
        "response": f"Ricevuto correttamente: {chat_request.message}"
    }
