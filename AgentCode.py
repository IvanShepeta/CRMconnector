import asyncio
import os
from agent_framework import ChatAgent, MCPStdioTool, MCPStreamableHTTPTool, ToolProtocol
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI
from azure.identity.aio import DefaultAzureCredential
# Observability / Tracing setup (use agent framework helper)
from agent_framework.observability import setup_observability
from dotenv import load_dotenv

load_dotenv()

# Configure OTLP endpoint and whether to capture sensitive data via env vars
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# Initialize tracing and instrumentation. When running locally, start the AI Toolkit trace collector:
# - VS Code command: `ai-mlstudio.tracing.open`
setup_observability(otlp_endpoint=OTLP_ENDPOINT, enable_sensitive_data="true")

# Microsoft Foundry Agent Configuration
ENDPOINT = os.getenv("ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")

AGENT_NAME = "mcp-agent"
AGENT_INSTRUCTIONS = os.getenv("AGENT_INSTRUCTIONS")

# User inputs for the conversation
USER_INPUTS = [
    "Привіт, чи є зараз курси по Python ?",
]


def create_mcp_tools() -> list[ToolProtocol]:
    return [
        MCPStreamableHTTPTool(
            name="local-server-crmconnector".replace("-", "_"),
            description="MCP server for local-server-crmconnector",
            url="http://localhost:3001/mcp",
            headers={
            }
        ),
    ]


async def main() -> None:
    async with (
        DefaultAzureCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=ENDPOINT,
                model_deployment_name=MODEL_DEPLOYMENT_NAME,
                async_credential=credential,
                agent_name=AGENT_NAME,
                agent_id=None,
                # Since no Agent ID is provided, the agent will be automatically created and deleted after getting response
            ),
            instructions=AGENT_INSTRUCTIONS,
            max_completion_tokens=2048,
            tools=[
                *create_mcp_tools(),
            ],
        ) as agent
    ):
        # Create a new thread that will be reused
        thread = agent.get_new_thread()

        # Process user messages
        for user_input in USER_INPUTS:
            print(f"\n# User: '{user_input}'")
            async for chunk in agent.run_stream([user_input], thread=thread):
                if chunk.text:
                    print(chunk.text, end="")
                elif (
                        chunk.raw_representation
                        and chunk.raw_representation.raw_representation
                        and hasattr(chunk.raw_representation.raw_representation, "status")
                        and hasattr(chunk.raw_representation.raw_representation, "type")
                        and chunk.raw_representation.raw_representation.status == "completed"
                        and hasattr(chunk.raw_representation.raw_representation, "step_details")
                        and hasattr(chunk.raw_representation.raw_representation.step_details, "tool_calls")
                ):
                    print("")
                    print("Tool calls: ", chunk.raw_representation.raw_representation.step_details.tool_calls)
            print("")

        print("\n--- All tasks completed successfully ---")

    # Give additional time for all async cleanup to complete
    await asyncio.sleep(1.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Program finished.")
