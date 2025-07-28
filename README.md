Filename: README.md

# OsduMCPDemo - MCP Server Component

The `OsduMCPDemo` is a fully-compliant MCP (Model Context Protocol) Server that implements all official core requirements. While designed as an extension for use with FedSrv, it can operate independently as a standalone MCP server. It provides access to OSDU (Open Subsurface Data Universe) data, including wells, wellbore trajectories, and casings, stored in a JSON file and served through a JSON-RPC interface over HTTP.

This README provides detailed instructions for installing and running the server both locally and on Azure App Service, including startup commands and environment variables.

## Features

- **MCP Compliance**: Implements core MCP methods (`initialize`, `resources/list`, `resources/read`, `tools/list`, `tools/call`, `prompts/list`, `prompts/get`).
- **OSDU Data Management**: Handles wells, wellbore trajectories, and casings data stored in a persistent JSON file.
- **Resources**: Exposes OSDU data as resources (`osdu:wells`, `osdu:trajectories`, `osdu:casings`) and a greeting resource for demonstration.
- **Tools**: Provides tools like `add_numbers`, `get_casings_for_well`, and `list_all_wells` for data manipulation.
- **Prompts**: Supports a `generate_greeting` prompt with customizable styles (friendly, formal, casual).
- **FastAPI Integration**: Uses FastAPI for HTTP endpoints and JSON-RPC request handling.
- **Persistence**: Stores data in a JSON file with automatic loading and saving.
- **Logging**: Comprehensive logging for debugging and monitoring.

## What is the Model Context Protocol (MCP)?

The Model Context Protocol (MCP) is an open standard introduced by Anthropic in November 2024. It provides a standardized client-server architecture for connecting AI assistants, such as large language models (LLMs), to external data sources, tools, and systems. MCP enables secure and efficient access to resources like databases, APIs, files, and more, allowing AI models to retrieve context dynamically without embedding everything in prompts.

An MCP Server is a program that implements this protocol, exposing capabilities such as resources, tools, and prompts via a JSON-RPC interface over HTTP. This demo implements an MCP Server using the `mcp` Python library, making OSDU data accessible to AI assistants.

For the full standards and specifications, refer to [Anthropic's MCP Documentation](https://docs.anthropic.com/en/docs/mcp).

## Prerequisites

- **Python**: Version 3.13.5 or later.
- **Operating System**: Compatible with Windows, macOS, or Linux for local development; Azure App Service for cloud deployment.
- **Dependencies**: Listed in `requirements.txt` (see Installation section).

## Installation

### Local Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd inno-fedsrv-mcp-api
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   Ensure `requirements.txt` is present in the project root:
   ```bash
   pip install -r requirements.txt
   ```
   The `requirements.txt` includes:
   - `mcp[server]>=1.8.0`: MCP server library.
   - `fastapi>=0.115.0`: FastAPI framework for HTTP endpoints.
   - `uvicorn>=0.30.6`: ASGI server for running FastAPI.
   - `python-dotenv>=1.0.1`: For loading environment variables.

4. **Prepare the Data File**:
   Ensure `osdu_data.json` is in the project root or specify a custom path via the `PERSIST_FILE` environment variable (see Environment Variables).

5. **Run the Server**:
   ```bash
   python app.py
   ```
   The server will start on `http://0.0.0.0:8000`. Access the root endpoint at `http://localhost:8000/` to verify the server status and record counts.

### Azure App Service Installation

1. **Set Up Azure App Service**:
   - Create an Azure App Service plan and web app in the Azure Portal.
   - Choose a Python 3.13 runtime stack (ensure version 3.13.5 or later).

2. **Deploy the Application**:
   - **Option 1: Git Deployment**:
     - Configure the repository in Azure App Service for continuous deployment.
     - Push the code to the linked repository.
   - **Option 2: Manual Deployment**:
     - Zip the project directory (including `app.py`, `requirements.txt`, `osdu_data.json`, etc.).
     - Use the Azure Portal or CLI to deploy the zip file:
       ```bash
       az webapp deployment source config-zip --resource-group <resource-group> --name <app-name> --src <zip-file>
       ```

3. **Configure Environment Variables**:
   In the Azure Portal, navigate to the web app’s **Configuration** > **Application Settings** and add:
   - `WEBSITE_HOSTNAME`: Set to the Azure App Service hostname (e.g., `<app-name>.azurewebsites.net`). This ensures the persistent file path uses `/home/osdu_data.json`.
   - `SCM_DO_BUILD_DURING_DEPLOYMENT`: Set to `1` to enable dependency installation during deployment.
   - Optionally, set `PERSIST_FILE` to a custom path (default is `/home/osdu_data.json` in Azure).

4. **Set Startup Command**:
   In the Azure Portal, under **Configuration** > **General Settings**, set the startup command:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
   ```
   This uses Gunicorn with Uvicorn workers for production-grade performance. Ensure `gunicorn` is added to `requirements.txt` if not already included:
   ```text
   gunicorn>=22.0.0
   ```

5. **Verify Deployment**:
   - Access the app at `https://<app-name>.azurewebsites.net/` to check the status.
   - Use the `/mcp/` endpoint to send JSON-RPC requests (e.g., via `curl` or Postman).

### Environment Variables

| Variable                     | Description                                                                 | Default Value                | Required |
|-----------------------------|-----------------------------------------------------------------------------|------------------------------|----------|
| `WEBSITE_HOSTNAME`          | Indicates the Azure App Service environment to set the persistent file path. | None                         | Optional |
| `PERSIST_FILE`              | Path to the JSON file for data persistence.                                  | `osdu_data.json` (local) or `/home/osdu_data.json` (Azure) | Optional |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | Enables dependency installation during Azure deployment.                | `1`                          | Optional (Azure) |

### Startup Commands

- **Local**:
  ```bash
  python app.py
  ```
  Runs the server using Uvicorn directly on `http://0.0.0.0:8000`.

- **Azure**:
  ```bash
  gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
  ```
  Uses Gunicorn with 4 Uvicorn workers for better performance in production.

## Usage

- **Root Endpoint** (`GET /`):
  Returns the server status and counts of wells, trajectories, and casings.
  ```json
  {
    "status": "Data loaded successfully.",
    "record_counts": {
      "wells": 2,
      "trajectories": 2,
      "casings": 3
    }
  }
  ```

- **MCP Endpoint** (`POST /mcp/`):
  Handles JSON-RPC requests. Example request to list resources:
  ```json
  {
    "jsonrpc": "2.0",
    "method": "resources/list",
    "id": 1
  }
  ```
  Response:
  ```json
  {
    "jsonrpc": "2.0",
    "result": {
      "resources": [
        {"uri": "greeting://{name}", "name": "Greeting Resource", ...},
        {"uri": "osdu:wells", "name": "OSDU Wells Resource", ...},
        ...
      ],
      "nextCursor": null
    },
    "id": 1
  }
  ```

- **Example Tool Call** (`tools/call`):
  Retrieve casings for a well:
  ```json
  {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_casings_for_well",
      "params": {"well_id": "well1"}
    },
    "id": 1
  }
  ```

## Testing

- **Local Testing**:
  Use `curl`, Postman, or a similar tool to send JSON-RPC requests to `http://localhost:8000/mcp/`.
  Example:
  ```bash
  curl -X POST http://localhost:8000/mcp/ -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"resources/list","id":1}'
  ```

- **Azure Testing**:
  Replace `localhost:8000` with `https://<app-name>.azurewebsites.net`.

## Logging

- Logs are configured at the `DEBUG` level and output to the console.
- Key events (e.g., data loading, request handling, errors) are logged for troubleshooting.
- In Azure, logs can be viewed via the **Log Stream** or **Diagnostic Logs** in the Azure Portal.

## Notes

- **FedSrv Compatibility**: While designed for FedSrv, the server is a standalone MCP implementation and can be used with any MCP-compliant client.
- **Data Persistence**: The `osdu_data.json` file is loaded on startup and saved after modifications. Ensure write permissions for the file path.
- **Scalability**: For production, consider scaling the Azure App Service plan or increasing Gunicorn workers based on load.

## Troubleshooting

- **Dependency Errors**: Ensure Python 3.13.5+ and all `requirements.txt` dependencies are installed.
- **File Permission Issues**: Verify write access to the `PERSIST_FILE` path, especially in Azure (`/home` directory).
- **Port Conflicts**: Ensure port 8000 is free for local development.
- **Azure Deployment Issues**: Check the Azure deployment logs for errors and verify the startup command and environment variables.

For further assistance, contact the repository maintainer or refer to the MCP specification for JSON-RPC details.
