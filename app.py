import sqlite3
import json
from mcp.server.fastmcp import FastMCP

# Initialize SQLite DB with OSDU sample data
def init_db():
    conn = sqlite3.connect('osdu.db')
    c = conn.cursor()
    
    # Create tables based on simplified OSDU schemas
    c.execute('''CREATE TABLE IF NOT EXISTS wells 
                 (id TEXT PRIMARY KEY, facility_name TEXT, operator TEXT, location TEXT)''')  # location as JSON string
    
    c.execute('''CREATE TABLE IF NOT EXISTS trajectories 
                 (id TEXT PRIMARY KEY, well_id TEXT, stations TEXT)''')  # stations as JSON string
    
    c.execute('''CREATE TABLE IF NOT EXISTS casings 
                 (id TEXT PRIMARY KEY, well_id TEXT, top_depth REAL, bottom_depth REAL, diameter REAL)''')
    
    # Insert sample data (OSDU-like)
    c.execute("INSERT OR IGNORE INTO wells VALUES ('well1', 'Well A', 'OperatorX', '{\"lat\": 29.75, \"lon\": -95.48}')")
    c.execute("INSERT OR IGNORE INTO wells VALUES ('well2', 'Well B', 'OperatorY', '{\"lat\": 30.12, \"lon\": -96.34}')")
    
    c.execute("INSERT OR IGNORE INTO trajectories VALUES ('traj1', 'well1', '[{\"md\": 0.0, \"tvd\": 0.0, \"incl\": 0.0, \"azi\": 0.0}, {\"md\": 1000.0, \"tvd\": 900.0, \"incl\": 10.0, \"azi\": 45.0}]')")
    c.execute("INSERT OR IGNORE INTO trajectories VALUES ('traj2', 'well2', '[{\"md\": 0.0, \"tvd\": 0.0, \"incl\": 0.0, \"azi\": 0.0}, {\"md\": 1500.0, \"tvd\": 1300.0, \"incl\": 15.0, \"azi\": 90.0}]')")
    
    c.execute("INSERT OR IGNORE INTO casings VALUES ('casing1', 'well1', 0.0, 500.0, 9.625)")
    c.execute("INSERT OR IGNORE INTO casings VALUES ('casing1b', 'well1', 500.0, 1000.0, 7.0)")  # Added extra casing for well1 to demo listing
    c.execute("INSERT OR IGNORE INTO casings VALUES ('casing2', 'well2', 0.0, 700.0, 7.0)")
    
    conn.commit()
    conn.close()

init_db()  # Run DB init on startup

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
    conn = sqlite3.connect('osdu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM casings WHERE well_id=?", (well_id,))
    rows = c.fetchall()
    conn.close()
    if rows:
        return [
            {
                "id": row[0],
                "well_id": row[1],
                "top_depth": row[2],
                "bottom_depth": row[3],
                "diameter": row[4]
            } for row in rows
        ]
    else:
        raise ValueError(f"No casings found for well {well_id}")

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

# New OSDU Well resource (retrieve by ID)
@mcp.resource("osdu:well://{well_id}")
def get_well(well_id: str) -> dict:
    """Retrieves OSDU Well data by ID."""
    conn = sqlite3.connect('osdu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM wells WHERE id=?", (well_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "facility_name": row[1],
            "operator": row[2],
            "location": json.loads(row[3])
        }
    else:
        raise ValueError(f"Well {well_id} not found")

# New OSDU WellboreTrajectory resource (retrieve by ID)
@mcp.resource("osdu:trajectory://{traj_id}")
def get_trajectory(traj_id: str) -> dict:
    """Retrieves OSDU WellboreTrajectory data by ID."""
    conn = sqlite3.connect('osdu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM trajectories WHERE id=?", (traj_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "well_id": row[1],
            "stations": json.loads(row[2])
        }
    else:
        raise ValueError(f"Trajectory {traj_id} not found")

# New OSDU Casing resource (retrieve by ID)
@mcp.resource("osdu:casing://{casing_id}")
def get_casing(casing_id: str) -> dict:
    """Retrieves OSDU Casing data by ID."""
    conn = sqlite3.connect('osdu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM casings WHERE id=?", (casing_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "well_id": row[1],
            "top_depth": row[2],
            "bottom_depth": row[3],
            "diameter": row[4]
        }
    else:
        raise ValueError(f"Casing {casing_id} not found")

# Expose the streamable HTTP ASGI app (mounted at /mcp by default)
app = mcp.streamable_http_app()
