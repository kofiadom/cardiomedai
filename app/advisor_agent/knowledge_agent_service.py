import os
import asyncio
import json
from typing import Optional, Dict, Any, List
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import FilePurpose, FileSearchTool
from toolbox_core import ToolboxClient


class KnowledgeAgentService:
    def __init__(self, project_endpoint: str = None, toolbox_url: str = None):
        self.project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        # Use environment variable or default to toolbox service name
        self.toolbox_url = toolbox_url or os.getenv("TOOLBOX_URL", "http://toolbox:5000") #Docker
        self.project_client = None
        self.toolbox_client = None
        self.vector_store_id = None
        self.file_ids = []
        self.db_tool_definitions = []
        self.db_tool_map = {}
        self.agent_id = None  # Store the agent ID
        self.file_search_tool = None  # Store the FileSearchTool instance

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
            credential=DefaultAzureCredential(exclude_interactive_browser_credential=False)
        )

        # Initialize database tools (optional)
        await self._initialize_database_tools()

        # Initialize file search capabilities
        if knowledge_files:
            await self._initialize_file_search(knowledge_files)

        # Try to get existing agent or create new one
        try:
            self.agent_id = os.getenv("KNOWLEDGE_AGENT_ID")
            if self.agent_id:
                agent = self.project_client.agents.get_agent(self.agent_id)
                print(f"✅ Successfully connected to existing agent: {self.agent_id}")
            else:
                raise Exception("No KNOWLEDGE_AGENT_ID environment variable found")
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
                    # Check file size (max 512MB)
                    file_size = os.path.getsize(file_path)
                    if file_size > 512 * 1024 * 1024:  # 512MB in bytes
                        print(f"⚠️ File too large (>512MB): {file_path}")
                        continue
                        
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
                # Create vector store with uploaded files and ensure it's processed
                vector_store = self.project_client.agents.vector_stores.create_and_poll(
                    file_ids=self.file_ids,
                    name="hypertension_knowledge_base",
                    expires_after={
                        "anchor": "last_active_at",
                        "days": 30  # Set expiration policy to manage costs
                    }
                )
                self.vector_store_id = vector_store.id
                
                # Create FileSearchTool instance
                self.file_search_tool = FileSearchTool(vector_store_ids=[self.vector_store_id])
                
                print(f"✅ Created vector store: {self.vector_store_id}")
                print(f"✅ Vector store status: {vector_store.status}")
                print(f"✅ Vector store file counts: {vector_store.file_counts}")
                
                # Debug: Check what the FileSearchTool contains
                print(f"🔍 FileSearchTool definitions: {self.file_search_tool.definitions}")
                print(f"🔍 FileSearchTool resources: {self.file_search_tool.resources}")
            
            else:
                print("⚠️ No files uploaded - file search will not be available")
                self.file_search_tool = None

        except Exception as e:
            print(f"❌ Error initializing file search: {e}")
            import traceback
            traceback.print_exc()
            self.vector_store_id = None
            self.file_search_tool = None

    async def create_knowledge_agent(self, include_database_tools: bool = False) -> str:
        """Create a knowledge agent with file search and optional database tools."""

        # Prepare tools - start with empty list
        tools = []
        tool_resources = None

        # Add file search tool if available (using FileSearchTool)
        if self.file_search_tool:
            print("✅ File search tool available")
            print(f"🔍 FileSearchTool definitions: {self.file_search_tool.definitions}")
            print(f"🔍 FileSearchTool resources: {self.file_search_tool.resources}")
            
            # Add file search tool definitions to tools list
            tools.extend(self.file_search_tool.definitions)
            tool_resources = self.file_search_tool.resources
        else:
            print("❌ File search tool not available")


        # Add database tools if requested and available
        if include_database_tools and self.db_tool_definitions:
            print(f"✅ Adding {len(self.db_tool_definitions)} database tools")
            tools.extend(self.db_tool_definitions)
        else:
            print("❌ Database tools not added")

        print(f"🛠️ Total tools for agent: {len(tools)}")
        for tool in tools:
            print(f"   - {tool}")

        # Create agent instructions
        instructions = """You are a friendly and knowledgeable hypertension education assistant. Your role is to:

1. **ALWAYS use the file_search tool to search your knowledge base FIRST** when answering questions about hypertension
2. **Search your uploaded files** for relevant information before providing answers
3. **Provide accurate, evidence-based information** from the uploaded files in your knowledge base
4. **Answer questions** about blood pressure, lifestyle, medications, and management
5. **Use a warm, supportive tone** that encourages healthy lifestyle choices
6. **Cite specific information** from your knowledge base files when available
7. **Acknowledge when information is outside your knowledge** and suggest consulting healthcare providers

**Critical Instructions for File Search:**
- The file_search tool should be your PRIMARY source of information
- ALWAYS search your knowledge base files before answering hypertension-related questions
- When you find relevant information in the files, reference it clearly in your response
- If the knowledge base doesn't contain specific information, clearly state this
- Prioritize information from your uploaded files over general knowledge

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

**Additional Context:** You have access to comprehensive user health data through database tools. When relevant to the question, you can:

**Available Database Tools:**

**User & Health Overview:**
- get_user_profile: Complete user profile and health information
- get_health_summary: Comprehensive health activity overview
- get_bp_statistics: Statistical analysis of blood pressure trends

**Blood Pressure Data:**
- get_bp_history: Full blood pressure history with notes
- get_recent_bp_readings: Last 5 BP readings for trend analysis

**Medication Management:**
- get_medication_reminders: All medication schedules
- get_pending_medication_reminders: Medications not yet taken
- get_medication_adherence: Adherence statistics by medication
- get_recent_medication_activity: Recent medication activity

**Health Reminders & Activities:**
- get_upcoming_reminders: All upcoming reminders (next 24 hours)
- get_bp_check_reminders: Blood pressure check schedules
- get_pending_bp_check_reminders: Pending BP checks
- get_doctor_appointment_reminders: All doctor appointments
- get_upcoming_doctor_appointments: Upcoming appointments
- get_workout_reminders: All workout schedules
- get_pending_workout_reminders: Pending workouts

**How to Use These Tools:**
- Use database tools to get the user's personal health context
- Reference their actual data to provide personalized education
- Relate general information from your knowledge base to their specific situation
- Provide targeted advice based on their medication adherence, BP trends, etc.
- Help them understand their data in the context of clinical guidelines

**Tool Usage Priority:**
1. FIRST: Use file_search to get evidence-based information from knowledge base
2. SECOND: Use relevant database tools to get user-specific context
3. THIRD: Combine both sources for comprehensive, personalized educational answers

**Examples of Personalized Responses:**
- "Based on your recent BP readings averaging 135/85, the clinical guidelines suggest..." (combines their data with knowledge base)
- "I see you've been taking your medication consistently - that's excellent! The research shows..." (acknowledges their adherence data)
- "Your upcoming doctor appointment is perfect timing to discuss..." (references their appointment data)"""

        try:
            # Get model deployment name from environment
            model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")
            
            print(f"🤖 Creating agent with model: {model_deployment}")
            print(f"🛠️ Tools count: {len(tools)}")
            print(f"🛠️ Tools: {[tool.get('type', tool.get('function', {}).get('name', 'unknown')) for tool in tools]}")
            print(f"📚 Tool resources: {tool_resources}")
            
            # Create agent with proper tool_resources
            agent = self.project_client.agents.create_agent(
                model=model_deployment,
                name="HypertensionKnowledgeAgent",
                instructions=instructions,
                tools=tools,
                tool_resources=tool_resources if tool_resources else None,   
            )
            print(f"✅ Agent created successfully: {agent.id}")
            print(f"✅ Agent tools: {[tool.get('type', 'unknown') for tool in tools]}")
            
            return agent.id
        except Exception as e:
            print(f"❌ Error creating agent: {e}")
            import traceback
            traceback.print_exc()
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
            else:
                print(f"✅ Using existing agent with ID: {self.agent_id}")

            # Create a thread for communication
            thread = self.project_client.agents.threads.create()

            # Prepare the question (add user context if requested)
            final_question = question
            if include_user_context and user_id:
                final_question = f"""User ID {user_id} asks: {question}
                
            IMPORTANT INSTRUCTIONS FOR YOU:
    1. FIRST: Use file_search to find relevant information in your knowledge base about this topic
    2. SECOND: If relevant, use database tools to get user-specific data  
    3. THIRD: Combine both sources for a comprehensive, personalized answer

    Always use file_search FIRST to search your knowledge base, then use database tools if needed for user context."""

            # Add message to thread
            message = self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=final_question,
            )

            # Create and process the run (using create_and_process for better handling)
            run = self.project_client.agents.runs.create(
                thread_id=thread.id,
                agent_id=self.agent_id,
            )
            
            # Poll the run status until it is completed or requires action 
            while run.status in ["queued", "in_progress", "requires_action"]: 
                await asyncio.sleep(1)  # Use async sleep 
                run = self.project_client.agents.runs.get(thread_id=thread.id, run_id=run.id) 
 
                if run.status == "requires_action": 
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls 
                    tool_outputs = [] 
                    for tool_call in tool_calls: 
                        # Get the actual MCP tool and call it 
                        tool = self.db_tool_map[tool_call.function.name]
                        print(f"✅Calling tool: {tool_call.function.name}")
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

            # Handle the run result
            if run.status == "completed":
                messages = self.project_client.agents.messages.list(thread_id=thread.id)
                # Get the assistant's response (most recent assistant message)
                assistant_response = None
                sources = []

                for msg in messages:
                    role = getattr(msg.role, 'value', msg.role)
                    if role == "assistant":
                        # Extract content properly
                        if hasattr(msg, 'content') and isinstance(msg.content, list) and len(msg.content) > 0:
                            content_item = msg.content[0]
                            if hasattr(content_item, 'text'):
                                assistant_response = content_item.text.value
                                
                                # Extract file citations if available
                                if hasattr(content_item.text, 'annotations'):
                                    for annotation in content_item.text.annotations:
                                        if hasattr(annotation, 'file_citation') and annotation.file_citation:
                                            sources.append(annotation.file_citation.file_id)
                        break

                return {
                    "status": "completed",
                    "answer": assistant_response or "No response generated",
                    "sources": sources,
                    "agent_id": self.agent_id,
                    "thread_id": thread.id,
                    "vector_store_id": self.vector_store_id
                }

            elif run.status == "failed":
                error_message = "Agent run failed"
                if hasattr(run, 'last_error') and run.last_error:
                    error_message += f": {run.last_error}"
                
                return {
                    "status": "failed",
                    "answer": error_message,
                    "error": getattr(run, 'last_error', None),
                    "agent_id": self.agent_id,
                    "thread_id": thread.id
                }
            else:
                return {
                    "status": "incomplete",
                    "answer": f"Agent run finished with status: {run.status}",
                    "agent_id": self.agent_id,
                    "thread_id": thread.id
                }

        except Exception as e:
            print(f"❌ Error in ask_question: {e}")
            return {
                "status": "error",
                "answer": f"An error occurred: {str(e)}",
                "error": str(e)
            }

    async def add_files_to_knowledge_base(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Add additional files to the existing knowledge base.
        
        Args:
            file_paths: List of file paths to add
            
        Returns:
            Dict with results of the operation
        """
        if not self.vector_store_id:
            return {"status": "error", "message": "No vector store available"}
            
        try:
            new_file_ids = []
            for file_path in file_paths:
                if os.path.exists(file_path):
                    # Check file size
                    file_size = os.path.getsize(file_path)
                    if file_size > 512 * 1024 * 1024:  # 512MB
                        print(f"⚠️ File too large: {file_path}")
                        continue
                        
                    file = self.project_client.agents.files.upload_and_poll(
                        file_path=file_path,
                        purpose=FilePurpose.AGENTS
                    )
                    new_file_ids.append(file.id)
                    self.file_ids.append(file.id)
                    print(f"✅ Uploaded: {os.path.basename(file_path)}")
            
            if new_file_ids:
                # Add files to existing vector store using batch operation
                vector_store_file_batch = self.project_client.agents.vector_store_file_batches.create_and_poll(
                    vector_store_id=self.vector_store_id,
                    file_ids=new_file_ids
                )
                
                return {
                    "status": "success",
                    "files_added": len(new_file_ids),
                    "batch_id": vector_store_file_batch.id
                }
            else:
                return {"status": "warning", "message": "No valid files to add"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        """Clean up resources."""
        if self.toolbox_client:
            await self.toolbox_client.close()

        # Note: In production, you might want to keep vector stores and files
        # for reuse rather than deleting them each time

    async def get_vector_store_info(self) -> Dict[str, Any]:
        """Get information about the current vector store."""
        if not self.vector_store_id:
            return {"status": "no_vector_store"}
            
        try:
            vector_store = self.project_client.agents.vector_stores.get(self.vector_store_id)
            return {
                "status": "success",
                "vector_store_id": self.vector_store_id,
                "name": vector_store.name,
                "file_counts": vector_store.file_counts,
                "status": vector_store.status,
                "created_at": vector_store.created_at
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}