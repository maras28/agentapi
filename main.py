from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import MessageRole
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

project_endpoint = os.environ["PROJECT_ENDPOINT"]
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]
agent_id = os.environ["AZURE_AI_AGENT_ID"]

app = FastAPI(title="Chat API")

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=project_endpoint,
)

agent = project.agents.get_agent(agent_id)
connection_string = project.telemetry.get_connection_string()

if not connection_string:
    print("Application Insights is not enabled. Enable by going to Tracing in your Azure AI Foundry project.")
    exit()

configure_azure_monitor(connection_string=connection_string) #enable telemetry collection

tracer = trace.get_tracer(__name__)

# Define the request and response models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, httpRequest: Request) -> Dict:
    """
    Process a chat message and return a response.
    
    Args:
        request: The chat request containing the user's message
        
    Returns:
        A dictionary with the bot's response
    """
    try:

        with tracer.start_as_current_span("hotel-agent-api-tracing"):

            # Get thread_id from HTTP header 'THREAD_ID', fallback to default if not provided
            thread_id = None
            if hasattr(httpRequest, "headers"):
                thread_id = httpRequest.headers.get("THREAD_ID")
                print(f"Received thread id in the request, ID: {thread_id}")

            if not thread_id:
                thread = project.agents.threads.create()
                thread_id = thread.id
                print(f"Created thread, ID: {thread.id}")

            message = project.agents.messages.create(
                thread_id=thread_id,
                role="user",
                content= request.message,
            )
            print(f"Created message, ID: {message.id}")

            # Create and process agent run in thread with tools
            run = project.agents.runs.create_and_process(thread_id=thread_id, agent_id=agent.id)
            print(f"Run finished with status: {run.status}")

            if run.status == "failed":
                print(f"Run failed: {run.last_error}")

            response = project.agents.messages.get_last_message_text_by_role(thread_id=thread_id,role=MessageRole.AGENT)

            response_obj = JSONResponse(content={"response": response.text.value})
            #response_obj = JSONResponse(content={"response": f"agentbot: {response}"})
            response_obj.headers["THREAD_ID"] = thread_id
            return response_obj
            #return {"response": f"agentbot: {response}"}
        
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
