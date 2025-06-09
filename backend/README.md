# FastAPI Azure AI Chat Backend

This is a FastAPI backend service that integrates Azure Cognitive Search and Azure OpenAI to provide an AI-powered chat assistant. The backend retrieves relevant knowledge base documents from Azure Search, uses them as context, and generates responses via Azure OpenAI's chat completion API.

---

## Features

- Accepts user prompts and queries Azure Cognitive Search to retrieve knowledge base content.
- Sends content chunks along with the user prompt to Azure OpenAI for contextual answer generation.
- Limits document content chunks to avoid overloading the AI with too much data.
- Handles CORS for integration with any frontend.
- Provides a health check endpoint.

---

## Prerequisites

- Python 3.8+
- Azure Cognitive Search service with an index populated with your knowledge base documents.
- Azure OpenAI service deployed with a chat model.
- Environment variables set in a `.env` file or environment for credentials and configuration.

---

## Environment Variables

Create a `.env` file in the project root or set the following environment variables:


```env
AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_KEY=<your-search-key>
AZURE_SEARCH_INDEX_NAME=<your-search-index-name>

OPENAI_API_BASE=https://<your-openai-endpoint>.openai.azure.com/
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_API_VERSION=2023-05-15  # or your deployed API version
OPENAI_DEPLOYMENT=<your-openai-deployment-name>
Installation
Clone the repository or copy the backend code.

Install dependencies:

bash
Copy
Edit
pip install fastapi uvicorn python-dotenv azure-search-documents azure-ai-openai
Running the Application
Run the FastAPI app locally with:

bash
Copy
Edit
uvicorn main:app --reload --host 0.0.0.0 --port 8000
Replace main:app with your Python filename if different.

API Endpoints
POST /api/prompt
Accepts a JSON body:

json
Copy
Edit
{
  "prompt": "Your question or message here"
}
Returns a JSON response with the AI assistant's reply:

json
Copy
Edit
{
  "response": "The AI-generated answer based on knowledge base documents."
}
GET /
Health check endpoint, returns:

json
Copy
Edit
{
  "message": "Backend is running!"
}
How it Works
The user sends a prompt to /api/prompt.

The backend queries Azure Cognitive Search for up to 9000 documents.

Each document content is truncated to 1500 characters to keep the context size manageable.

The system prompt plus all document chunks are sent as context to Azure OpenAI chat completion.

The AI's response is returned to the user.

Notes
Adjust max_tokens, temperature, and other OpenAI parameters in the code to tune response length and creativity.

For production, restrict CORS origins instead of allowing all.

##Ensure your Azure Search index has a searchable content field.

Large search results may affect performance; consider using Azure Cognitive Search filters or semantic ranking.

Troubleshooting
Ensure all environment variables are correctly set.

Verify your Azure Search endpoint, key, and index name.

Confirm the Azure OpenAI deployment name and API version.

Check network connectivity to Azure services.

Review error logs printed on exceptions for debugging.

License
This project is provided as-is without warranty. Use according to your Azure subscription terms.

