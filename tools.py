import json
from datetime import datetime
from tinydb import TinyDB, Query
from typing import Optional

# --- Database Setup ---
db = TinyDB('.memory.json')
Memory = Query()


# --- Tool Functions ---
# We define our tools as standard Python functions.
# The ollama library will automatically convert the docstrings and type hints into the JSON schema the model needs.

def get_time() -> str:
    """
    Get the current date and time.

    Returns:
        str: The current date and time in ISO 8601 format.
    """
    return json.dumps({"current_time": datetime.now().isoformat()})

def memory(key: str, value: Optional[str] = None) -> str:
    """
    Save or load a memory value.
    If only a key is provided, it will load the value.
    If both key and value are provided, it will save or update the value.

    Args:
        key (str): The name of the memory to save or retrieve.
        value (Optional[str]): The information to store. Omit this to retrieve a memory.

    Returns:
        str: A JSON string indicating the result of the operation.
    """
    # Saving or updating a memory
    if value is not None:
        db.upsert({'key': key, 'value': value}, Memory.key == key)
        return json.dumps({"status": "ok", "set": {key: value}})
    
    # Retrieving a memory
    else:
        result = db.get(Memory.key == key)
        if result:
            return json.dumps({"key": key, "value": result.get('value')})
        else:
            # If key not found, it's helpful to tell the model what keys are available.
            known_keys = [doc['key'] for doc in db.all()]
            return json.dumps({
                "error": f"Key '{key}' not found in memory.",
                "known_keys": known_keys
            })

# --- Tool Registry ---
# This dictionary maps the function names to the actual function objects.
# Your main script will use this to execute the correct function.
available_tools = {
    "get_time": get_time,
    "memory": memory,
}

# This is the list you will pass to the ollama.chat function.
# It contains the function objects themselves, not the manual JSON definitions.
tools_list = [get_time, memory]
