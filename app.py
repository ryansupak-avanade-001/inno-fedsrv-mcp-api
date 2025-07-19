#app.py
#OsduMCPDemo
import os
import json
import logging
import asyncio
# Ensure mcp[server]>=1.8.0 and hypercorn>=0.17.3 are installed in requirements.txt
try:
    from mcp.server import Server
except ImportError as e:
    logger.error("Failed to import mcp.server: " + str(e))
    raise
try:
    import hypercorn.asyncio
    from hypercorn.config import Config
except ImportError as e:
    logger.error("Hypercorn not found: " + str(e))
    raise
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

# Set up logging to catch startup and request issues
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Persistent file path (use /home in Azure App Service for persistence)
PERSIST_FILE = os.path.join('/home', 'osdu_data.json') if os.getenv('WEBSITE_HOSTNAME') else 'osdu_data.json'  # Local fallback

# In-memory data stores
wells = {}
trajectories = {}
casings = {}

# Load data from persistent JSON file into memory on startup
def load_data():
    global wells, trajectories, casings
    try:
        if os.path.exists(PERSIST_FILE):
            logger.debug("Loading data from " + PERSIST_FILE)
            with open(PERSIST_FILE, 'r') as f:
                data = json.load(f)
                wells = {w['id']: w for w in data.get('wells', [])}
                trajectories = {t['id']: t for t in data.get('trajectories', [])}
                casings = {c['id']: c for c in data.get('casings', [])}
        else:
            logger.debug("No persistent file found, initializing sample data")
            init_data()
    except Exception as e:
        logger.error("Failed to load data: " + str(e))
        raise

# Initialize sample OSDU data and save to file
def init_data():
    global wells, trajectories, casings
    wells = {
        'well1': {"id": "well1", "facility_name": "Well A", "operator": "OperatorX", "location": {"lat": 29.75, "lon": -95.48}},
        'well2': {"id": "well2", "facility_name": "Well B", "operator": "OperatorY", "location": {"lat": 30.12, "lon": -96.34}}
    }
    trajectories = {
        'traj1': {"id": "traj1", "well_id": "well1", "stations": [{"md": 0.0, "tvd": 0.0, "incl": 0.0, "azi": 0.0}, {"md": 1000.0, "tvd": 900.0, "incl": 10.0, "azi": 45.0}]},
        'traj2': {"id": "traj2", "well_id": "well2", "stations": [{"md": 0.0, "tvd": 0.0, "incl": 0.0, "azi": 0.0}, {"md": 1500.0, "tvd": 1300.0, "incl": 15.0, "azi": 90.0}]}
    }
    casings = {
        'casing1': {"id": "casing1", "well_id": "well1", "top_depth": 0.0, "bottom_depth": 500.0, "diameter": 9.625},
        'casing1b': {"id": "casing1b", "well_id": "well1", "top_depth": 500.0, "bottom_depth": 1000.0, "diameter": 7.0},
        'casing2': {"id": "casing2", "well_id": "well2", "top_depth": 0.0, "bottom_depth": 700.0, "diameter": 7.0}
    }
    save_data()

# Save in-memory data to persistent JSON file
def save_data():
    try:
        data = {
            'wells': list(wells.values()),
            'trajectories': list(trajectories.values()),
            'casings': list(casings.values())
        }
        with open(PERSIST_FILE, 'w') as f:
            json.dump(data, f)
        logger.debug("Data saved to " + PERSIST_FILE)
    except Exception as e:
        logger.error("Failed to save data: " + str(e))
        raise

load_data()  # Load on startup

# Define custom MCP server
class OsduMCPServer(Server):
    async def handle_request(self, request: dict) -> dict:
        method = request.get("method")
        params = request.get("params", {})
        logger.debug("Received request: method=" + method + ", params=" + str(params))
        if method == "initialize":
            response = {"jsonrpc": "2.0", "result": {"protocolVersion": "2024-11-05", "capabilities": {"resources": {"supported": True}, "tools": {"supported": True}, "prompts": {"supported": True}}, "serverInfo": {"name": "OsduMCPDemo", "version": "1.0.0"}}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "notifications/initialized":
            response = {"jsonrpc": "2.0", "result": {}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "resources/list":
            resources = [
                {"uri": "greeting://{name}", "name": "Greeting Resource", "description": "Returns a personalized greeting message. Replace {name} with a name.", "mimeType": "text/plain"},
                {"uri": "osdu:wells", "name": "OSDU Wells Resource", "description": "Retrieves all OSDU Well data.", "mimeType": "application/json"},
                {"uri": "osdu:trajectories", "name": "OSDU WellboreTrajectories Resource", "description": "Retrieves all OSDU WellboreTrajectory data.", "mimeType": "application/json"},
                {"uri": "osdu:casings", "name": "OSDU Casings Resource", "description": "Retrieves all OSDU Casing data.", "mimeType": "application/json"}
            ]
            response = {"jsonrpc": "2.0", "result": {"resources": resources, "nextCursor": None}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri.startswith("greeting://"):
                name = uri.split("://")[1]
                response = {"jsonrpc": "2.0", "result": "Hello, " + name + "! Welcome to the MCP demo.", "id": request.get("id", 1)}
                logger.debug("Returning response for " + method + ": " + json.dumps(response))
                return response
            resource_handlers = {
                "osdu:wells": lambda: list(wells.values()),
                "osdu:trajectories": lambda: list(trajectories.values()),
                "osdu:casings": lambda: list(casings.values())
            }
            handler = resource_handlers.get(uri)
            if handler:
                try:
                    result = handler()
                    response = {"jsonrpc": "2.0", "result": result, "id": request.get("id", 1)}
                    logger.debug("Returning response for " + method + ": " + json.dumps(response))
                    return response
                except Exception as e:
                    logger.error("Resource read error for " + uri + ": " + str(e))
                    response = {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Resource read error: " + str(e)}, "id": request.get("id", 1)}
                    logger.debug("Returning response for " + method + ": " + json.dumps(response))
                    return response
            response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid resource URI: " + uri}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "tools/list":
            tools = [
                {"name": "add_numbers", "description": "Adds two integers together.", "inputSchema": {"properties": {"a": {"title": "A", "type": "integer"}, "b": {"title": "B", "type": "integer"}}, "required": ["a", "b"], "title": "add_numbersArguments", "type": "object"}, "outputSchema": {"properties": {"result": {"title": "Result", "type": "integer"}}, "required": ["result"], "title": "add_numbersOutput", "type": "object"}},
                {"name": "get_casings_for_well", "description": "Retrieves a list of all casings for a given well ID.", "inputSchema": {"properties": {"well_id": {"title": "Well Id", "type": "string"}}, "required": ["well_id"], "title": "get_casings_for_wellArguments", "type": "object"}},
                {"name": "list_all_wells", "description": "Lists all wells from the osdu:wells Resource.", "inputSchema": {}, "outputSchema": {"type": "array"}}
            ]
            response = {"jsonrpc": "2.0", "result": {"tools": tools}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "tools/call":
            tool_id = params.get("name", "")
            tool_params = params.get("params", {})
            tool_handlers = {
                "add_numbers": lambda: tool_params["a"] + tool_params["b"],
                "get_casings_for_well": lambda: [c for c in casings.values() if c['well_id'] == tool_params["well_id"]],
                "list_all_wells": lambda: list(wells.values())
            }
            handler = tool_handlers.get(tool_id)
            if handler:
                try:
                    result = handler()
                    if tool_id == "get_casings_for_well" and not result:
                        raise ValueError("No casings found for well " + tool_params["well_id"])
                    response = {"jsonrpc": "2.0", "result": result, "id": request.get("id", 1)}
                    logger.debug("Returning response for " + method + ": " + json.dumps(response))
                    return response
                except Exception as e:
                    logger.error("Tool call error for " + tool_id + ": " + str(e))
                    response = {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Tool call error: " + str(e)}, "id": request.get("id", 1)}
                    logger.debug("Returning response for " + method + ": " + json.dumps(response))
                    return response
            response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid tool name: " + tool_id}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "prompts/list":
            prompts = [
                {"name": "generate_greeting", "description": "Generates a prompt for creating a greeting in a specified style.", "arguments": [{"name": "name", "required": True}, {"name": "style", "required": False}]}
            ]
            response = {"jsonrpc": "2.0", "result": {"prompts": prompts}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        elif method == "prompts/get":
            prompt_id = params.get("name", "")
            prompt_params = params.get("params", {})
            if prompt_id == "generate_greeting":
                styles = {
                    "friendly": "Write a warm and friendly greeting",
                    "formal": "Write a professional and formal greeting",
                    "casual": "Write a relaxed and casual greeting"
                }
                style = prompt_params.get("style", "friendly")
                response = {"jsonrpc": "2.0", "result": styles.get(style, styles['friendly']) + " for " + prompt_params.get("name", "") + ".", "id": request.get("id", 1)}
                logger.debug("Returning response for " + method + ": " + json.dumps(response))
                return response
            response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid prompt name: " + prompt_id}, "id": request.get("id", 1)}
            logger.debug("Returning response for " + method + ": " + json.dumps(response))
            return response
        response = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found: " + method}, "id": request.get("id", 1)}
        logger.debug("Returning response for " + method + ": " + json.dumps(response))
        return response

# Create MCP server
mcp = OsduMCPServer(name="OsduMCPDemo", version="1.0.0")

# Add HTTP routes
async def mcp_handler(request: Request):
    try:
        payload = await request.body()
        logger.debug("Received MCP request: " + payload.decode())
        message = json.loads(payload.decode())
        response = await mcp.handle_request(message)
        logger.debug("Sending MCP response: " + json.dumps(response))
        return JSONResponse(response, headers={"Content-Type": "application/json"})
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in request: " + str(e))
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        logger.error("MCP handler error: " + str(e))
        return JSONResponse({"error": "Internal Server Error"}, status_code=500)

async def root(request):
    status = "Data loaded successfully." if wells or trajectories or casings else "Data failed to load."
    counts = {
        "wells": len(wells),
        "trajectories": len(trajectories),
        "casings": len(casings)
    }
    return JSONResponse({"status": status, "record_counts": counts})

app = Starlette(routes=[
    Route("/mcp/", mcp_handler, methods=["POST"]),
    Route("/", root, methods=["GET"])
])

# Run the server
if __name__ == "__main__":
    logger.debug("Starting Hypercorn server")
    asyncio.run(hypercorn.asyncio.serve(app, Config.from_mapping({"bind": "0.0.0.0:8000"})))
