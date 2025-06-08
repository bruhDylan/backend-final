from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Enable CORS (adjust allow_origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure Blob Storage config
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

# Azure OpenAI client config
client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
)

# System prompt for context
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a helpful assistant. Use the provided file contents to answer questions accurately. "
            "If the information is not in the provided content, say 'I don't know.'"
        )
    }
]

# Request body model
class PromptRequest(BaseModel):
    prompt: str

# Fetch blobs separately and return as a dictionary
def fetch_all_blobs_separately():
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

    blobs_list = container_client.list_blobs()
    blobs_data = {}

    for blob in blobs_list:
        blob_name = blob.name
        blob_client = container_client.get_blob_client(blob_name)
        downloaded_blob = blob_client.download_blob().readall().decode("utf-8")
        # Optional: Limit size of each blob's content to avoid overwhelming the AI
        blobs_data[blob_name] = downloaded_blob[:2000]

    return blobs_data

@app.post("/api/prompt")
async def chat_with_ai(data: PromptRequest):
    prompt = data.prompt.strip()

    if not prompt:
        return JSONResponse({"error": "No prompt provided"}, status_code=400)

    # Fetch all blobs separately
    blobs_data = fetch_all_blobs_separately()

    # Prepare conversation with knowledge base structure
    conversation = conversation_history.copy()

    # Let the AI know which files are available
    file_list = list(blobs_data.keys())
    conversation.append({
        "role": "system",
        "content": f"The following files are available in the knowledge base:\n{file_list}"
    })

    # Add each blob's content as a separate system message
    for blob_name, content in blobs_data.items():
        conversation.append({
            "role": "system",
            "content": f"File: {blob_name}\nContent:\n{content}"
        })

    # Add user's actual prompt
    conversation.append({"role": "user", "content": prompt})

    try:
        # Get the AI's response
        completion = client.chat.completions.create(
            model="ttss-copilot-gpt4-chat",
            messages=conversation,
            max_tokens=800,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.0
        )

        reply = completion.choices[0].message.content

        # Update conversation history
        conversation_history.append({"role": "user", "content": prompt})
        conversation_history.append({"role": "assistant", "content": reply})

        return {"response": reply}

    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg:
            return JSONResponse(
                {
                    "error": "Rate limit exceeded. Please wait and try again.",
                    "details": str(e)
                },
                status_code=429
            )
        return JSONResponse(
            {"error": "An unexpected error occurred.", "details": str(e)},
            status_code=500
        )

@app.get("/")
async def root():
    return {"message": "Backend is running!"}
