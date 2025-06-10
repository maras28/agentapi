from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import AzureAISearchTool, AzureAISearchQueryType
from azure.ai.agents import AgentsClient

project_endpoint = os.environ["PROJECT_ENDPOINT"]
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]
agent_id = os.environ["AZURE_AI_AGENT_ID"]

app = FastAPI(title="Chat API")

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=project_endpoint,
)

agent = project.agents.get_agent(agent_id)

# Define the request and response models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> Dict:
    """
    Process a chat message and return a response.
    
    Args:
        request: The chat request containing the user's message
        
    Returns:
        A dictionary with the bot's response
    """
    try:

        thread = project.agents.threads.create()
        print(f"Created thread, ID: {thread.id}")

        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content= request.message,
        )
        print(f"Created message, ID: {message.id}")


        # Create and process agent run in thread with tools
        run = project.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        messages = project.agents.messages.list(thread_id=thread.id)
        response = ""
        for message in messages:
            if message.role == "assistant":
                response = message.content
                break
            print(f"Role: {message.role}, Content: {message.content}")

        # For demonstration purposes, just echo the message back with a prefix
        # Replace this with your actual processing logic
        return {"response": f"agentbot: {response}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint to verify the API is running."""
    return {"status": "API is running", "endpoints": ["/chat"]}

if __name__ == "__main__":
    import uvicorn
    # Run the server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
