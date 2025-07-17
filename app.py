import os
import json
import logging
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.routing import Route

# Set up logging to catch startup issues
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
            logger.debug(f"Loading data from {PERSIST_FILE}")
            with open(PERSIST_FILE, 'r') as f:
                data = json.load(f)
                wells = {w['id']: w for w in data.get('wells', [])}
                trajectories = {t['id']: t for t in data.get('trajectories', [])}
                casings = {c['id']: c for c in data.get('casings', [])}
        else:
            logger.debug("No persistent file found, initializing sample data")
            init_data()
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
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
        logger.debug(f"Data saved to {PERSIST_FILE}")
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        raise

load_data()  # Load on startup

# Create the MCP server instance with stateless HTTP enabled
try:
    mcp = FastMCP(name="OsduMCPDemo", version="1.0.0", stateless_http=True)
    logger.debug("FastMCP initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP: {e}")
    raise

# Custom endpoint to list resource templates
async def list_resources(request):
    """Lists resource templates for discovery."""
    logger.debug("Handling resources-list request")
    resources = [
        {
            "uri": "greeting://{name}",
            "name": "Greeting Resource",
            "description": "Returns a personalized greeting message. Replace {name} with a name.",
            "mimeType": "text/plain"
        },
        {
            "uri": "osdu:well://{well_id}",
            "name": "OSDU Well Resource",
            "description": "Retrieves OSDU Well data by ID. Replace {well_id} with a well ID (e.g., well1).",
            "mimeType": "application/json"
        },
        {
            "uri": "osdu:trajectory://{traj_id}",
            "name": "OSDU WellboreTrajectory Resource",
            "description": "Retrieves OSDU WellboreTrajectory data by ID. Replace {traj_id} with a trajectory ID (e.g., traj1).",
            "mimeType": "application/json"
        },
        {
            "uri": "osdu:casing://{casing_id}",
            "name": "OSDU Casing Resource",
            "description": "Retrieves OSDU Casing data by ID. Replace {casing_id} with a casing ID (e.g., casing1).",
            "mimeType": "application/json"
        }
    ]
    # Directly return JSON-RPC response
    return JSONResponse({
        "jsonrpc": "2.0",
        "result": {"resources": resources, "nextCursor": None},
        "id": 1
    })

# Create the ASGI app and add custom endpoint
app = mcp.streamable_http_app()
app.routes.append(Route("/resources-list", list_resources, methods=["POST"]))

# Original simple tool
@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Adds two integers together."""
    return a + b

# New OSDU tool: Get all casings for a well
@mcp.tool()
def get_casings_for_well(well_id: str) -> list:
    """Retrieves a list of all casings for a given well ID."""
    result = [c for c in casings.values() if c['well_id'] == well_id]
    if not result:
        raise ValueError(f"No casings found for well {well_id}")
    return result

# Original simple resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Returns a personalized greeting message."""
    return f"Hello, {name}! Welcome to the MCP demo."

# Original simple prompt
@mcp.prompt()
def generate_greeting(name: str, style: str = "friendly") -> str:
    """Generates a prompt for creating a greeting in a specified style."""
    styles = {
        "friendly": "Write a warm and friendly greeting",
        "formal": "Write a professional and formal greeting",
        "casual": "Write a relaxed and casual greeting",
    }
    return f"{styles.get(style, styles['friendly'])} for {name}."

# New OSDU Well resource (retrieve by ID from memory)
@mcp.resource("osdu:well://{well_id}")
def get_well(well_id: str) -> dict:
    """Retrieves OSDU Well data by ID."""
    if well_id in wells:
        return wells[well_id]
    raise ValueError(f"Well {well_id} not found")

# New OSDU WellboreTrajectory resource (retrieve by ID from memory)
@mcp.resource("osdu:trajectory://{traj_id}")
def get_trajectory(traj_id: str) -> dict:
    """Retrieves OSDU WellboreTrajectory data by ID."""
    if traj_id in trajectories:
        return trajectories[traj_id]
    raise ValueError(f"Trajectory {traj_id} not found")

# New OSDU Casing resource (retrieve by ID from memory)
@mcp.resource("osdu:casing://{casing_id}")
def get_casing(casing_id: str) -> dict:
    """Retrieves OSDU Casing data by ID."""
    if casing_id in casings:
        return casings[casing_id]
    raise ValueError(f"Casing {casing_id} not found")

# Add a root route for sanity check
async def root(request):
    status = "Data loaded successfully." if wells or trajectories or casings else "Data failed to load."
    counts = {
        "wells": len(wells),
        "trajectories": len(trajectories),
        "casings": len(casings)
    }
    return JSONResponse({"status": status, "record_counts": counts})

app.add_route("/", root, methods=["GET"])

# Run the server locally for testing
if __name__ == "__main__":
    logger.debug("Starting Uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)
