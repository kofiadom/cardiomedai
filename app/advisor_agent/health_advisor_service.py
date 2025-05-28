import os
import asyncio
import json
from typing import Optional, Dict, Any
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from toolbox_core import ToolboxClient


class HealthAdvisorService:
    """
    Service class for managing health advisor agent interactions.
    Provides a reusable interface for creating agents and processing health advice requests.
    """

    def __init__(self, project_endpoint: str = None, toolbox_url: str = "http://127.0.0.1:5000"):
        self.project_endpoint = project_endpoint or "https://azure-ai-agent-test-resource.services.ai.azure.com/api/projects/azure-ai-agent-test"
        self.toolbox_url = toolbox_url
        self.project_client = None
        self.toolbox_client = None
        self.tool_definitions = []
        self.tool_map = {}

        # Ensure we're using the correct database path
        self._ensure_database_path()

    def _ensure_database_path(self):
        """Ensure the YAML file points to the correct database path."""
        import os

        # Get the absolute path to the main database
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        main_db_path = os.path.join(project_root, "hypertension.db")

        # Path to the YAML file
        yaml_path = os.path.join(os.path.dirname(__file__), "tools.yaml")

        # Read current YAML content
        try:
            with open(yaml_path, 'r') as f:
                yaml_content = f.read()

            # Check if the database path needs updating
            if main_db_path.replace('\\', '/') not in yaml_content:
                # Update the database path in YAML content
                lines = yaml_content.split('\n')
                for i, line in enumerate(lines):
                    if 'database:' in line and 'my-sqlite-db' in yaml_content[:yaml_content.find(line)]:
                        # Update the database path with forward slashes for cross-platform compatibility
                        lines[i] = f'    database: "{main_db_path.replace(chr(92), "/")}"'
                        break

                # Write back the updated content
                with open(yaml_path, 'w') as f:
                    f.write('\n'.join(lines))

                print(f"✅ Updated database path in YAML to: {main_db_path}")
            else:
                print(f"✅ Database path already correct in YAML")

        except Exception as e:
            print(f"⚠️ Could not update YAML database path: {e}")

    async def initialize(self):
        """Initialize the Azure AI client and load MCP tools."""
        # Create an AIProjectClient instance
        self.project_client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=DefaultAzureCredential(),
        )

        # Get tools from MCP server and convert to Azure AI format
        self.toolbox_client = ToolboxClient(self.toolbox_url)
        mcp_tools = await self.toolbox_client.load_toolset("my_toolset")

        # Convert MCP tools to Azure AI format
        self.tool_definitions = []
        for tool in mcp_tools:
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool._name,
                    "description": tool._description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            self.tool_definitions.append(tool_def)

        # Store MCP tools for later use
        self.tool_map = {tool._name: tool for tool in mcp_tools}

    async def create_agent(self) -> str:
        """Create a health advisor agent and return its ID."""
        agent = self.project_client.agents.create_agent(
            model="gpt-4o-mini",
            name="CommunityHealthWorker",
            instructions="""You are a friendly community health worker who checks in on people with hypertension.
            Your role is to provide SHORT, ENCOURAGING, and PERSONAL daily check-ins.

            **Your Communication Style:**
            - Keep messages under 3-4 sentences
            - Be warm, friendly, and encouraging like a caring friend
            - Use simple, everyday language (not medical jargon)
            - Focus on positive progress and motivation
            - Give ONE simple tip or reminder per message
            - Use encouraging emojis occasionally

            **What to do:**
            1. Check their recent BP readings (last 3-7 days)
            2. Notice trends, improvements, or concerns
            3. Give encouraging feedback about their progress
            4. Provide ONE simple daily tip (water, walking, medication reminder, etc.)
            5. Keep it personal and motivational

            **BP Categories (for your reference only):**
            - Great: <120/80 - Celebrate this!
            - Good: 120-129/<80 - Encourage to maintain
            - Watch: 130-139/80-89 - Gentle motivation needed
            - Concern: ≥140/≥90 - Supportive but suggest medical check

            **Example Messages:**
            - "Amazing! Your 118/75 this morning is fantastic! 🎉 Remember to take a 10-minute walk after lunch today."
            - "I see your BP is staying steady around 125/80 - you're doing great! Don't forget your evening medication."
            - "Your readings have improved so much this week! Treat yourself to a healthy smoothie today. 🥤"

            **Important:** Always be encouraging, never lecture. Act like a supportive friend who cares about their wellbeing.

            First get their profile and recent readings, then give a short, personal, encouraging message.""",
            tools=self.tool_definitions,
        )
        return agent.id

    async def process_health_advice_request(self, user_id: int, message: str) -> Dict[str, Any]:
        """
        Process a health advice request for a specific user.

        Args:
            user_id: The ID of the user requesting advice
            message: The user's message/question

        Returns:
            Dict containing the response and metadata
        """
        try:
            # Create an agent
            agent_id = await self.create_agent()

            # Create a thread for communication
            thread = self.project_client.agents.threads.create()

            # Add a message to the thread
            message_obj = self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=message,
            )

            # Create a run for the agent to process the message
            run = self.project_client.agents.runs.create(
                thread_id=thread.id,
                agent_id=agent_id
            )

            # Poll the run status until it is completed or requires action
            while run.status in ["queued", "in_progress", "requires_action"]:
                await asyncio.sleep(1)
                run = self.project_client.agents.runs.get(
                    thread_id=thread.id,
                    run_id=run.id
                )

                if run.status == "requires_action":
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    for tool_call in tool_calls:
                        tool = self.tool_map[tool_call.function.name]
                        result = await tool()
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })

                    run = self.project_client.agents.runs.submit_tool_outputs(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )

            # Get the final response
            if run.status == "completed":
                messages = self.project_client.agents.messages.list(thread_id=thread.id)
                # Get the assistant's response (last message)
                assistant_response = None
                for msg in messages:
                    role = msg.role.value if hasattr(msg.role, 'value') else msg.role
                    if role == "assistant":
                        content = msg.content[0]['text']['value'] if isinstance(msg.content, list) else msg.content
                        assistant_response = content
                        break

                return {
                    "status": "completed",
                    "response": assistant_response or "No response generated",
                    "agent_id": agent_id,
                    "thread_id": thread.id
                }
            else:
                return {
                    "status": "failed",
                    "response": f"Agent run failed with status: {run.status}",
                    "error": getattr(run, 'last_error', None),
                    "agent_id": agent_id,
                    "thread_id": thread.id
                }

        except Exception as e:
            return {
                "status": "error",
                "response": f"An error occurred: {str(e)}",
                "error": str(e)
            }

    async def cleanup(self):
        """Clean up resources."""
        if self.toolbox_client:
            await self.toolbox_client.close()
