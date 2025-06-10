import os
from semantic_kernel.agents import Agent, ChatCompletionAgent, HandoffOrchestration, OrchestrationHandoffs
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import AzureAIAgent
from azure.identity import DefaultAzureCredential
import asyncio

# Define the OpenAI chat completion service
chat_completion_service = AzureChatCompletion(
    deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] ,
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
)

class OrderStatusPlugin:
    @kernel_function
    def check_order_status(self, order_id: str) -> str:
        """Check the status of an order."""
        # Simulate checking the order status
        return f"Order {order_id} is shipped and will arrive in 2-3 days."

class OrderRefundPlugin:
    @kernel_function
    def process_refund(self, order_id: str, reason: str) -> str:
        """Process a refund for an order."""
        # Simulate processing a refund
        print(f"Processing refund for order {order_id} due to: {reason}")
        return f"Refund for order {order_id} has been processed successfully."

class OrderReturnPlugin:
    @kernel_function
    def process_return(self, order_id: str, reason: str) -> str:
        """Process a return for an order."""
        # Simulate processing a return
        print(f"Processing return for order {order_id} due to: {reason}")
        return f"Return for order {order_id} has been processed successfully."

def get_agents() -> tuple[list[Agent], OrchestrationHandoffs]:
    """Return a list of agents that will participate in the Handoff orchestration and the handoff relationships.
    Feel free to add or remove agents and handoff connections.
    """
    support_agent = ChatCompletionAgent(
        name="TriageAgent",
        description="A customer support agent that triages issues.",
        instructions="Handle customer requests.",
        service=chat_completion_service,
    )

    refund_agent = ChatCompletionAgent(
        name="RefundAgent",
        description="A customer support agent that handles refunds.",
        instructions="Handle refund requests.",
        service=chat_completion_service,
        plugins=[OrderRefundPlugin()],
    )
    order_status_agent = ChatCompletionAgent(
        name="OrderStatusAgent",
        description="A customer support agent that checks order status.",
        instructions="Handle order status requests.",
        service=chat_completion_service,
        plugins=[OrderStatusPlugin()],
    )
    order_return_agent = ChatCompletionAgent(
        name="OrderReturnAgent",
        description="A customer support agent that handles order returns.",
        instructions="Handle order return requests.",
        service=chat_completion_service,
        plugins=[OrderReturnPlugin()],
    )

    # Create an Azure AI agent for reseerch
    azurecreds = DefaultAzureCredential()
    azureaiagent_client = AzureAIAgent.create_client(credential=azurecreds, endpoint=os.environ["PROJECT_ENDPOINT"])
    # Wait for the get_agent call to complete if it is asynchronous
    get_agent_result = azureaiagent_client.agents.get_agent(os.environ["AZURE_AI_AGENT_ID"])
    if hasattr(get_agent_result, "__await__"):
        azureaiagent_definition = asyncio.get_event_loop().run_until_complete(get_agent_result)
    else:
        azureaiagent_definition = get_agent_result

    azure_agent_researcher = AzureAIAgent(
        client=azureaiagent_client,
        definition=azureaiagent_definition,
    )

    # Define the handoff relationships between agents
    handoffs = (
        OrchestrationHandoffs()
        .add(
            source_agent=support_agent.name,
            target_agent=azure_agent_researcher.name,
            description="Transfer to this agent if the question/task is related to hotels",
        )
    )
    return [support_agent, azure_agent_researcher], handoffs

def agent_response_callback(message: ChatMessageContent) -> None:
    """Observer function to print the messages from the agents."""
    if message.role == AuthorRole.ASSISTANT:
        edited_content = message.content.replace("\nAI tarafından oluşturulan içerik hatalı olabilir", "")
        # Print the agent's response
        print(f"{message.name}\t: {edited_content}")
    else:
        print(f"{message.name}\t: {message.content}")

def human_response_function() -> ChatMessageContent:
    """Observer function to print the messages from the agents."""
    user_input = input("User\t\t: ")
    return ChatMessageContent(role=AuthorRole.USER, content=user_input)

async def main():
    """Main function to run the agents."""
    # 1. Create a handoff orchestration with multiple agents
    agents, handoffs = await get_agents()
    handoff_orchestration = HandoffOrchestration(
        members=agents,
        handoffs=handoffs,
        agent_response_callback=agent_response_callback,
        human_response_function=human_response_function,
    )
    # 2. Create a runtime and start it
    runtime = InProcessRuntime()
    runtime.start()
    # 3. Invoke the orchestration with a task and the runtime
    orchestration_result = await handoff_orchestration.invoke(
        task="A customer is on the line.",
        runtime=runtime,
    )
    # 4. Wait for the results
    value = await orchestration_result.get()
    print(value)
    # 5. Stop the runtime after the invocation is complete
    await runtime.stop_when_idle()
