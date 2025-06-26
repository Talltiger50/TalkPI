from tinydb import TinyDB, Query

db = TinyDB('.memory.json')
Memory = Query()
tools = [
    {
        "name": "get_time",
        "description": "Get the current time",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "memory",
        "description": "Save or load a memory value. If only a key is provided, it will load the value. If both key and value are provided, it will save the value.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key or name of the memory slot"
                },
                "value": {
                    "type": "string",
                    "description": "The value to store in memory (optional for loading)"
                }
            },
            "required": ["key"]  # only "key" is required, so it can be used for both save/load
        }
    }
]
def error_no_arg(args:list[str]):
    return {"error": f"tool requires {args} args"}
def call_tool(tool_name, args: dict):
    if tool_name == "get_time":
        from datetime import datetime
        return {"current_time": datetime.now().isoformat()}

    elif tool_name == "memory":
        key = args.get("key")
        if not key:
            return error_no_arg("key")

        value = args.get("value")
        if value is not None:
            # Use upsert to overwrite existing key or insert new
            db.upsert({key: value}, Memory[key].exists())
            return {"status": "ok", "set": {key: value}}
        else:
            # Lookup case
            result = db.get(Memory[key].exists())
            if result and key in result:
                return {"value": result[key]}
            else:
                # Report missing key and list known keys
                unique_keys = sorted({k for doc in db.all() for k in doc.keys()})
                return {
                    "error": f"Key '{key}' not found",
                    "known_keys": unique_keys
                }
    return {"error": "Unknown tool"}
