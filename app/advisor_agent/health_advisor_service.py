import os
import asyncio
import json
from typing import Optional, Dict, Any
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from toolbox_core import ToolboxClient
from .datetime_tool import datetime_tool_def
from .datetime_tool import get_current_datetime


class HealthAdvisorService:
    """
    Service class for managing health advisor agent interactions.
    Provides a reusable interface for creating agents and processing health advice requests.
    """

    def __init__(self, project_endpoint: str = None, toolbox_url: str = None):
        self.project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        # Use environment variable or default to toolbox service name
        self.toolbox_url = toolbox_url or os.getenv("TOOLBOX_URL", "http://toolbox:5000") #Docker
        self.project_client = None
        self.toolbox_client = None
        self.tool_definitions = []
        self.tool_map = {}
        self.agent_id = None  # Store the agent ID
    
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
        """Initialize the Azure AI client, load MCP tools, and create/get agent."""
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
            
        # Add datetime tool
        datetime_tool_dict = {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Get the current date and time in YYYY-MM-DD HH:MM:SS format",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        self.tool_definitions.append(datetime_tool_dict)
        
        # Store MCP tools for later use
        self.tool_map = {tool._name: tool for tool in mcp_tools}
        
        # Add datetime function to the tool map
        self.tool_map["get_current_datetime"] = get_current_datetime

        print(f"✅ Total tools for agent: {len(self.tool_definitions)}")
        for i, tool in enumerate(self.tool_definitions):
            print(f"   - Tool {i}: {tool.get('function', {}).get('name', 'unknown')} (type: {type(tool)})")

        # Debug: Check if all tools are properly formatted
        for i, tool in enumerate(self.tool_definitions):
            if not isinstance(tool, dict) or 'type' not in tool or 'function' not in tool:
                print(f"❌ Invalid tool format at index {i}: {tool}")
                raise ValueError(f"Tool at index {i} is not properly formatted: {tool}")

        # Try to get existing agent or create new one with better error handling
        # Use environment variable or fallback to known working agent ID
        self.agent_id = os.getenv("HEALTH_ADVISOR_AGENT_ID") or "asst_phjVsezosQqDE3XCufhu1oZd"
        
        if self.agent_id:
            print(f"🔍 Attempting to connect to agent: {self.agent_id}")
            if self.agent_id == "asst_phjVsezosQqDE3XCufhu1oZd":
                print("📌 Using hardcoded fallback agent ID")
            else:
                print("📌 Using agent ID from environment variable")
            # Try to connect to existing agent with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    agent = self.project_client.agents.get_agent(self.agent_id)
                    print(f"✅ Successfully connected to existing agent: {self.agent_id}")
                    break
                except Exception as e:
                    print(f"⚠️ Attempt {attempt + 1}/{max_retries} failed to connect to agent {self.agent_id}: {e}")
                    if attempt == max_retries - 1:
                        print(f"❌ Failed to connect to existing agent after {max_retries} attempts")
                        print(f"🔄 Creating new agent as fallback...")
                        agent = await self.create_agent()
                        self.agent_id = agent
                        print(f"✅ Created new agent: {self.agent_id}")
                    else:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
        else:
            print("⚠️ No HEALTH_ADVISOR_AGENT_ID environment variable found")
            print("🔄 Creating new agent...")
            agent = await self.create_agent()
            self.agent_id = agent
            print(f"✅ Created new agent: {self.agent_id}")
            print(f"💡 Consider setting HEALTH_ADVISOR_AGENT_ID={self.agent_id} in your .env file")

    async def create_agent(self) -> str:
        """Create a health advisor agent and return its ID."""
        print("🔄 Creating new health advisor agent...")
        agent = self.project_client.agents.create_agent(
            model="gpt-4o-mini",
            name="CommunityHealthWorker",
            instructions="""You are a friendly community health worker who checks in on people with hypertension.
            Your role is to provide SHORT, ENCOURAGING, and PERSONAL daily check-ins using their complete health data.

            **Your Communication Style:**
            - Keep messages under 3-4 sentences
            - Be warm, friendly, and encouraging like a caring friend
            - Use simple, everyday language (not medical jargon)
            - Focus on positive progress and motivation
            - Give ONE simple tip or reminder per message
            - Use encouraging emojis occasionally

            **Available Database Tools - Use These to Personalize Your Messages:**

            **User & Health Data:**
            - get_user_profile: Get complete user profile and health info
            - get_bp_history: Full blood pressure history with notes
            - get_recent_bp_readings: Last 5 BP readings for trends
            - get_bp_statistics: Statistical analysis (averages, counts)
            - get_health_summary: Comprehensive health activity overview

            **Medication Management:**
            - get_medication_reminders: All medication schedules
            - get_pending_medication_reminders: Medications not yet taken
            - get_medication_adherence: Adherence statistics by medication
            - get_recent_medication_activity: Recent medication activity

            **Reminders & Appointments:**
            - get_upcoming_reminders: All upcoming reminders (next 24 hours)
            - get_bp_check_reminders: BP check schedules
            - get_pending_bp_check_reminders: Pending BP checks
            - get_doctor_appointment_reminders: All doctor appointments
            - get_upcoming_doctor_appointments: Upcoming appointments
            - get_workout_reminders: All workout schedules
            - get_pending_workout_reminders: Pending workouts

            **What to do:**
            1. Check their recent BP readings and trends
            2. Look at medication adherence and upcoming doses
            3. Check for pending reminders (BP checks, workouts, appointments)
            4. Notice patterns, improvements, or areas needing encouragement
            5. Give personalized feedback based on their complete health picture
            6. Provide ONE relevant tip or gentle reminder

            **BP Categories (for your reference only):**
            - Great: <120/80 - Celebrate this!
            - Good: 120-129/<80 - Encourage to maintain
            - Watch: 130-139/80-89 - Gentle motivation needed
            - Concern: ≥140/≥90 - Supportive but suggest medical check

            **Example Personalized Messages:**
            - "Amazing! Your 118/75 this morning is fantastic! 🎉 I see you have your evening medication reminder at 8pm - you're doing great!"
            - "Your BP is staying steady around 125/80, and I love that you've been taking your medications on time! Don't forget your workout reminder for this afternoon."
            - "Your readings have improved so much this week! I see you have a doctor's appointment coming up - perfect timing to share this progress! 👩‍⚕️"
            - "Great job on yesterday's workout! Your BP readings show the benefits. Remember your morning medication in 2 hours."

            **Important:** Always be encouraging, never lecture. Use their actual data to make messages personal and relevant.

            You also have **get_current_datetime** tool to know the current date and time.

            **Process:** First get their health summary and recent activity, then give a short, personal, encouraging message based on their actual data.""",
            tools=self.tool_definitions,
        )
        
        print(f"✅ Successfully created new agent with ID: {agent.id}")
        print(f"💡 To avoid recreating agents, add this to your .env file:")
        print(f"💡 HEALTH_ADVISOR_AGENT_ID={agent.id}")
        
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
            # Use existing agent with recovery logic
            if not self.agent_id:
                print("⚠️ No agent ID found, attempting to recover...")
                # Try environment variable first, then fallback to hardcoded ID
                self.agent_id = os.getenv("HEALTH_ADVISOR_AGENT_ID") or "asst_phjVsezosQqDE3XCufhu1oZd"
                
                if self.agent_id:
                    if self.agent_id == "asst_phjVsezosQqDE3XCufhu1oZd":
                        print("📌 Using hardcoded fallback agent ID for recovery")
                    else:
                        print("📌 Using environment variable for recovery")
                    try:
                        # Verify the agent still exists
                        agent = self.project_client.agents.get_agent(self.agent_id)
                        print(f"✅ Recovered existing agent with ID: {self.agent_id}")
                    except Exception as e:
                        print(f"⚠️ Failed to recover agent {self.agent_id}: {e}")
                        print("🔄 Creating new agent as fallback...")
                        agent = await self.create_agent()
                        self.agent_id = agent
                        print(f"✅ Created new agent: {self.agent_id}")
                else:
                    print("🔄 Creating new agent...")
                    agent = await self.create_agent()
                    self.agent_id = agent
                    print(f"✅ Created new agent: {self.agent_id}")
            else:
                print(f"✅ Using existing agent with ID: {self.agent_id}")

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
                agent_id=self.agent_id
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
                        print(f"✅Calling tool: {tool_call.function.name}")
                        
                        # Handle datetime tool differently (it's a regular function, not async)
                        if tool_call.function.name == "get_current_datetime":
                            result = tool()  # Call without await
                        else:
                            result = await tool()  # MCP tools are async
                        
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
                    "agent_id": self.agent_id,
                    "thread_id": thread.id
                }
            else:
                return {
                    "status": "failed",
                    "response": f"Agent run failed with status: {run.status}",
                    "error": getattr(run, 'last_error', None),
                    "agent_id": self.agent_id,
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