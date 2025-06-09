from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import os
import traceback

# Load environment variables from a .env file (for security and configuration)
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

# Load Azure Search credentials and settings from environment
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
        "You are a helpful assistant. Use the provided content chunks from the knowledge base to generate the best possible answer. "
        "If you cannot find an exact answer, summarize or infer based on the most relevant information available."
    )
}

@app.post("/api/prompt")
async def chat_with_ai(data: PromptRequest):
    prompt = data.prompt.strip()

    # Reject empty prompts
    if not prompt:
        return JSONResponse({"error": "Prompt cannot be empty"}, status_code=400)

    try:
        # Retrieve all documents from Azure Search (up to 9000)
        all_docs = []
        results = search_client.search(search_text="*", top=9000)

        for doc in results:
            all_docs.append(doc)

        # Limit each document to 1500 characters to avoid overloading the AI
        content_chunks = []
        for doc in all_docs:
            content = doc.get("content", "")
            if content:
                chunk = content.strip()[:1500]
                content_chunks.append(chunk)

        # Build the message history for the AI
        messages = [BASE_SYSTEM_PROMPT]

        if content_chunks:
            for i, chunk in enumerate(content_chunks):
                messages.append({
                    "role": "system",
                    "content": f"Document chunk {i+1}:\n{chunk}"
                })
        else:
            messages.append({
                "role": "system",
                "content": "No documents found in the knowledge base."
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

        # Return the assistant's reply
        reply = completion.choices[0].message.content
        return {"response": reply}

    except Exception as e:
        # Return detailed error message in case of failure
        traceback.print_exc()
        return JSONResponse(
            {"error": "Internal Server Error", "details": str(e)},
            status_code=500
        )

@app.get("/")
async def root():
    # Health check endpoint
    return {"message": "Backend is running!"}
