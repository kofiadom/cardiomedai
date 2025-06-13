from datetime import datetime
from azure.ai.agents.models import FunctionTool

def get_current_datetime():
    """
    Get the current date and time in YYYY-MM-DD HH:MM:SS format.
    
    Returns:
        str: Current date and time as a string in YYYY-MM-DD HH:MM:SS format
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

datetime_tool_def = FunctionTool(functions=get_current_datetime)

