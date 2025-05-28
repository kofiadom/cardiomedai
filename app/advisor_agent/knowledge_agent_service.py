import os
import asyncio
import json
from typing import Optional, Dict, Any, List
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import FilePurpose
from toolbox_core import ToolboxClient


class KnowledgeAgentService:
    """
    Service class for managing knowledge agent interactions with RAG capabilities.
    Provides hypertension education through file search and optional database context.
    """

    def __init__(self, project_endpoint: str = None, toolbox_url: str = "http://127.0.0.1:5000"):
        self.project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        self.toolbox_url = toolbox_url
        self.project_client = None
        self.toolbox_client = None
        self.vector_store_id = None
        self.file_ids = []
        self.db_tool_definitions = []
        self.db_tool_map = {}
        self.agent_id = None  # Store the agent ID

        # Knowledge base files directory
        self.knowledge_base_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")

    async def initialize(self, knowledge_files: List[str] = None):
        """
        Initialize the knowledge agent with file search and database tools.

        Args:
            knowledge_files: List of file paths to upload to the knowledge base
        """
        # Create an AIProjectClient instance
        self.project_client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=DefaultAzureCredential(exclude_interactive_browser_credential=False),
        )

        # Initialize database tools (optional)
        await self._initialize_database_tools()

        # Initialize file search capabilities
        if knowledge_files:
            await self._initialize_file_search(knowledge_files)

        # Try to get existing agent or create new one
        try:
            self.agent_id = os.getenv("KNOWLEDGE_AGENT_ID")
            agent = self.project_client.agents.get_agent(self.agent_id)
            print(f"✅ Successfully connected to existing agent: {self.agent_id}")
        except Exception as e:
            print(f"Creating new agent as existing agent not found: {e}")
            agent_id = await self.create_knowledge_agent(include_database_tools=True)
            self.agent_id = agent_id
            print(f"✅ Created new agent: {self.agent_id}")

    async def _initialize_database_tools(self):
        """Initialize database tools for user context (optional)."""
        try:
            self.toolbox_client = ToolboxClient(self.toolbox_url)
            mcp_tools = await self.toolbox_client.load_toolset("my_toolset")

            # Convert MCP tools to Azure AI format
            self.db_tool_definitions = []
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
                self.db_tool_definitions.append(tool_def)

            # Store MCP tools for later use
            self.db_tool_map = {tool._name: tool for tool in mcp_tools}
            print(f"✅ Initialized {len(self.db_tool_definitions)} database tools")

        except Exception as e:
            print(f"⚠️ Could not initialize database tools: {e}")
            self.db_tool_definitions = []
            self.db_tool_map = {}

    async def _initialize_file_search(self, knowledge_files: List[str]):
        """Initialize file search with knowledge base files."""
        try:
            # Upload files to Azure AI
            uploaded_files = []
            for file_path in knowledge_files:
                if os.path.exists(file_path):
                    file = self.project_client.agents.files.upload_and_poll(
                        file_path=file_path,
                        purpose=FilePurpose.AGENTS
                    )
                    uploaded_files.append(file)
                    self.file_ids.append(file.id)
                    print(f"✅ Uploaded file: {os.path.basename(file_path)} (ID: {file.id})")
                else:
                    print(f"⚠️ File not found: {file_path}")

            if uploaded_files:
                # Create vector store with uploaded files
                vector_store = self.project_client.agents.vector_stores.create_and_poll(
                    file_ids=self.file_ids,
                    name="hypertension_knowledge_base"
                )
                self.vector_store_id = vector_store.id
                print(f"✅ Created vector store: {self.vector_store_id}")
            else:
                print("⚠️ No files uploaded - file search will not be available")

        except Exception as e:
            print(f"❌ Error initializing file search: {e}")
            self.vector_store_id = None

    async def create_knowledge_agent(self, include_database_tools: bool = False) -> str:
        """Create a knowledge agent with file search and optional database tools."""

        # Prepare tools
        tools = []
        tool_resources = {}

        # Add file search tool if vector store is available
        if self.vector_store_id:
            tools.append({"type": "file_search"})
            tool_resources["file_search"] = {"vector_store_ids": [self.vector_store_id]}

        # Add database tools if requested and available
        if include_database_tools and self.db_tool_definitions:
            tools.extend(self.db_tool_definitions)

        # Create agent instructions
        instructions = """You are a friendly and knowledgeable hypertension education assistant. Your role is to:

1. **Provide accurate, evidence-based information** about hypertension from your knowledge base
2. **Answer questions** about blood pressure, lifestyle, medications, and management
3. **Use a warm, supportive tone** that encourages healthy lifestyle choices
4. **Search your knowledge base** to provide detailed, referenced answers
5. **Acknowledge when information is outside your knowledge** and suggest consulting healthcare providers

**Guidelines:**
- Always prioritize safety - recommend medical consultation for serious concerns
- Provide practical, actionable advice when appropriate
- Use simple, easy-to-understand language
- Include relevant information from your knowledge base files
- Be encouraging and supportive about lifestyle changes

**Important:** You are an educational resource, not a replacement for professional medical advice."""

        # Add database context instructions if database tools are included
        if include_database_tools and self.db_tool_definitions:
            instructions += """

**Additional Context:** You also have access to the user's blood pressure data and profile. When relevant to the question, you can:
- Reference their recent readings to provide personalized context
- Relate general information to their specific situation
- Provide more targeted educational content based on their data"""

        try:
            # Create agent without tool_resources (this format works with current SDK)
            agent = self.project_client.agents.create_agent(
                model="gpt-4o-mini",
                name="HypertensionKnowledgeAgent",
                instructions=instructions,
                tools=tools,
            )
            return agent.id
        except Exception as e:
            print(f"❌ Error creating agent: {e}")
            raise

    async def ask_question(self, question: str, user_id: Optional[int] = None, include_user_context: bool = False) -> Dict[str, Any]:
        """
        Ask a question to the knowledge agent.

        Args:
            question: The user's question about hypertension
            user_id: Optional user ID for personalized context
            include_user_context: Whether to include user's BP data for context

        Returns:
            Dict containing the response and metadata
        """
        try:
            # Use existing agent or create new one if needed
            if not self.agent_id:
                print("⚠️ No agent ID found, creating new agent")
                agent_id = await self.create_knowledge_agent(include_database_tools=include_user_context)
                self.agent_id = agent_id

            # Create a thread for communication
            thread = self.project_client.agents.threads.create()

            # Prepare the question (add user context if requested)
            final_question = question
            if include_user_context and user_id:
                final_question = f"User ID {user_id} asks: {question}\n\nPlease provide educational information and, if relevant, relate it to their blood pressure data."

            # Add message to thread
            message = self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=final_question,
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
                        if tool_call.function.name in self.db_tool_map:
                            # Execute database tool
                            tool = self.db_tool_map[tool_call.function.name]
                            result = await tool()
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(result)
                            })

                    if tool_outputs:
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
                sources = []

                for msg in messages:
                    role = msg.role.value if hasattr(msg.role, 'value') else msg.role
                    if role == "assistant":
                        # Use the same approach as health_advisor_service.py
                        content = msg.content[0]['text']['value'] if isinstance(msg.content, list) else msg.content
                        assistant_response = content

                        # Try to extract file citations if available
                        try:
                            if isinstance(msg.content, list):
                                for content_item in msg.content:
                                    if hasattr(content_item, 'text') and hasattr(content_item.text, 'annotations'):
                                        for annotation in content_item.text.annotations:
                                            if hasattr(annotation, 'file_citation'):
                                                sources.append(annotation.file_citation.file_id)
                        except:
                            pass  # Citations are optional
                        break

                return {
                    "status": "completed",
                    "answer": assistant_response or "No response generated",
                    "sources": sources,
                    "agent_id": self.agent_id,
                    "thread_id": thread.id,
                    "vector_store_id": self.vector_store_id
                }
            else:
                return {
                    "status": "failed",
                    "answer": f"Agent run failed with status: {run.status}",
                    "error": getattr(run, 'last_error', None),
                    "agent_id": self.agent_id,
                    "thread_id": thread.id
                }

        except Exception as e:
            return {
                "status": "error",
                "answer": f"An error occurred: {str(e)}",
                "error": str(e)
            }

    async def cleanup(self):
        """Clean up resources."""
        if self.toolbox_client:
            await self.toolbox_client.close()

        # Note: In production, you might want to keep vector stores and files
        # for reuse rather than deleting them each time
