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
    raise ValueError(f"Error: OpenAI version {openai.__version__} "
                     "is less than required version 1.1.1")
else:
    print("OpenAI version is compatible.")

# Legge le chiavi dall'ambiente
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

# Inizializza il client OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello per le richieste di chat
class ChatRequest(BaseModel):
    thread_id: str
    message: str

@app.get("/start")
async def start_conversation():
    print("Starting a new conversation...")
    thread = client.beta.threads.create()
    print(f"New thread created with ID: {thread.id}")
    return {"thread_id": thread.id}

@app.post("/chat")
async def chat(chat_request: ChatRequest):
    try:
        # Debug: stampa il payload ricevuto
        print("Ricevuto payload:")
        print(chat_request.dict())

        thread_id = chat_request.thread_id
        user_input = chat_request.message

        if not thread_id or not user_input:
            raise HTTPException(status_code=400, detail="Missing thread_id or message")

        print(f"Received message: '{user_input}' for thread ID: {thread_id}")

        # Inserisce il messaggio
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )

        # Crea la run dell'assistente
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Attende il completamento della run
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

            print(f"Run status: {run_status.status}")

            if run_status.status in ["completed", "cancelling", "cancelled", "requires_action", "failed"]:
                break

            await asyncio.sleep(1)

        # Recupera la risposta finale dell'assistente
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response = messages.data[0].content[0].text.value
        print(f"Assistant response: {response}")
        return {"response": response}

    except Exception as e:
        print(f"Errore durante la generazione della risposta: {e}")
        raise HTTPException(status_code=500, detail="Errore interno durante la generazione della risposta")
