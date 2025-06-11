from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from openai import AzureOpenAI
import os
import traceback

# Load environment variables from a .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Allow requests from any frontend (CORS policy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the data format expected from the user
class PromptRequest(BaseModel):
    prompt: str

# Load Azure Search credentials and settings
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

# Connect to Azure Search
search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX_NAME,
    credential=AzureKeyCredential(AZURE_SEARCH_KEY)
)

# Set up connection to Azure OpenAI
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION")
)

# Base instruction to guide the AI assistant's behavior
BASE_SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful assistant. Use the provided knowledge chunks to answer the user's question. "
        "If the chunks are insufficient, respond with your best possible answer based on context and general knowledge. "
        "Always provide a complete, informative response."
    )
}

@app.post("/api/prompt")
async def chat_with_ai(data: PromptRequest):
    prompt = data.prompt.strip()

    if not prompt:
        return JSONResponse({"error": "Prompt cannot be empty"}, status_code=400)

    try:
        # Retrieve all documents from Azure Search using by_page to handle >1000
        all_docs = []
        pages = search_client.search(
            search_text="*",
            query_type=QueryType.SIMPLE,
            search_mode="all",
            top=1000,
            order_by=["chunk_id asc"]  # sort by a stable field
        ).by_page()

        for page in pages:
            for doc in page:
                all_docs.append(doc)

        print(f"✅ Retrieved {len(all_docs)} documents from index\n")

        # Limit each document to 1500 characters
        content_chunks = []
        for i, doc in enumerate(all_docs):
            content = doc.get("content", "")
            title = doc.get("title", f"Document {i+1}")
            if content:
                chunk = f"[{title}]\n{content.strip()[:1500]}"
                content_chunks.append(chunk)

        # Build the message history for the AI
        messages = [BASE_SYSTEM_PROMPT]

        if content_chunks:
            for i, chunk in enumerate(content_chunks):
                messages.append({
                    "role": "user",
                    "content": f"Please consider the following information (chunk {i+1}):\n{chunk}"
                })

        # Add user's prompt to the conversation
        messages.append({"role": "user", "content": prompt})

        # Call Azure OpenAI to get a response
        completion = openai_client.chat.completions.create(
            model=os.getenv("OPENAI_DEPLOYMENT"),
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            top_p=0.9
        )

        reply = completion.choices[0].message.content
        return {"response": reply}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {"error": "Internal Server Error", "details": str(e)},
            status_code=500
        )

@app.get("/")
async def root():
    return {"message": "Backend is running!"}
