import os 
import time 
from azure.ai.projects import AIProjectClient 
from azure.identity import DefaultAzureCredential 
from toolbox_core import ToolboxClient 
import asyncio 
import json 
 
# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project. 
project_endpoint = "https://azure-ai-agent-test-resource.services.ai.azure.com/api/projects/azure-ai-agent-test" 
 
async def main(): 
    # Create an AIProjectClient instance 
    project_client = AIProjectClient( 
        endpoint=project_endpoint, 
        credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication 
    ) 
 
    # Get tools from MCP server and convert to Azure AI format 
    client = ToolboxClient("http://127.0.0.1:5000") 
    try: 
        mcp_tools = await client.load_toolset("my_toolset") 
         
        # Convert MCP tools to Azure AI format 
        tool_definitions = [] 
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
            tool_definitions.append(tool_def)
            print(tool_def)
 
        # Store MCP tools for later use 
        tool_map = {tool._name: tool for tool in mcp_tools} 
 
        with project_client: 
            # Create an agent with our database tools 
            agent = project_client.agents.create_agent( 
                model="gpt-4o-mini",  # Model deployment name 
                name="DatabaseAgentTest",  # Name of the agent 
                instructions="""You are a helpful agent that can query a SQLite database for user and product information. 
                You have access to database tools that allow you to: 
                - Read all users from the database 
                - Read all products from the database 
                Use these tools to help answer questions about the database contents. 
                When displaying results, use a simple text format without markdown.""", 
                tools=tool_definitions,  # Use converted tool definitions 
            ) 
            print(f"Created agent, ID: {agent.id}") 
 
            # Create a thread for communication 
            thread = project_client.agents.threads.create() 
            print(f"Created thread, ID: {thread.id}") 
 
            # Add a message to the thread 
            message = project_client.agents.messages.create( 
                thread_id=thread.id, 
                role="user",  # Role of the message sender 
                content="Which product has the largest price?",  # Message content 
            ) 
            print(f"Created message, ID: {message['id']}") 
 
            # Create a run for the agent to process the message 
            run = project_client.agents.runs.create(thread_id=thread.id, agent_id=agent.id) 
            print(f"Created run, ID: {run.id}") 
 
            # Poll the run status until it is completed or requires action 
            while run.status in ["queued", "in_progress", "requires_action"]: 
                await asyncio.sleep(1)  # Use async sleep 
                run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id) 
 
                if run.status == "requires_action": 
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls 
                    tool_outputs = [] 
                    for tool_call in tool_calls: 
                        # Get the actual MCP tool and call it 
                        tool = tool_map[tool_call.function.name] 
                        result = await tool() 
                        tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(result)}) 
                     
                    run = project_client.agents.runs.submit_tool_outputs( 
                        thread_id=thread.id, 
                        run_id=run.id, 
                        tool_outputs=tool_outputs 
                    ) 
 
            print(f"\nRun finished with status: {run.status}") 
            print("\nConversation:") 
            print("-" * 50) 
 
            # Fetch and log all messages 
            messages = project_client.agents.messages.list(thread_id=thread.id) 
            for message in messages: 
                role = message.role.value if hasattr(message.role, 'value') else message.role 
                content = message.content[0]['text']['value'] if isinstance(message.content, list) else message.content 
                print(f"\n{role.upper()}:") 
                print(content) 
                print("-" * 50) 
 
            # Delete the agent when done 
            # project_client.agents.delete_agent(agent.id) 
            # print("Deleted agent") 
    finally: 
        await client.close() 
 
if __name__ == "__main__": 
    asyncio.run(main()) 