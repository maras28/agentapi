from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import os
import asyncio
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import AzureAISearchTool, AzureAISearchQueryType
from azure.ai.agents import AgentsClient

from semantic_kernel.agents import Agent, ChatCompletionAgent, HandoffOrchestration, OrchestrationHandoffs
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings
from agentsutil import get_agents


project_endpoint = os.environ["PROJECT_ENDPOINT"]
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]
agent_id = os.environ["AZURE_AI_AGENT_ID"]

runtime = InProcessRuntime()

app = FastAPI(title="Chat API")

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=project_endpoint,
)

agents, handoffs = get_agents()
handoff_orchestration = HandoffOrchestration(
        members=agents,
        handoffs=handoffs,
        #agent_response_callback=agent_response_callback,
        #human_response_function=human_response_function,
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
        runtime.start()

        orchestration_result = await handoff_orchestration.invoke(
            task=request.message,
            runtime=runtime,
        )

        response = await orchestration_result.get()

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
