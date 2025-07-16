import os
import json
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

# Persistent file path (use /home in Azure App Service for persistence)
PERSIST_FILE = os.path.join('/home', 'osdu_data.json') if os.getenv('WEBSITE_HOSTNAME') else 'osdu_data.json'  # Local fallback

# In-memory data stores (replacing SQLite for simplicity)
wells = {}
trajectories = {}
casings = {}

# Load data from persistent JSON file into memory on startup
def load_data():
    global wells, trajectories, casings
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, 'r') as f:
            data = json.load(f)
            wells = {w['id']: w for w in data.get('wells', [])}
            trajectories = {t['id']: t for t in data.get('trajectories', [])}
            casings = {c['id']: c for c in data.get('casings', [])}
    else:
        # If no file, initialize sample data and save
        init_data()

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

# Save in-memory data to persistent JSON file (call on any write operations)
def save_data():
    data = {
        'wells': list(wells.values()),
        'trajectories': list(trajectories.values()),
        'casings': list(casings.values())
    }
    with open(PERSIST_FILE, 'w') as f:
        json.dump(data, f)

load_data()  # Load on startup (init and save if no file)

# Create the MCP server instance with stateless HTTP enabled
mcp = FastMCP(name="OsduMCPDemo", version="1.0.0", stateless_http=True)

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

# Expose the streamable HTTP ASGI app (mounted at /mcp by default)
app = mcp.streamable_http_app()

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
