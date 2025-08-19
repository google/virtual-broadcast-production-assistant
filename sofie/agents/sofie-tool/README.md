Sofie MCP Server
A Model Context Protocol (MCP) server for interacting with the Sofie Automation System. This server provides tools for managing rundowns, segments, parts, and connecting to live status updates via WebSocket.
Features

REST API Integration: Full integration with Sofie's REST API
WebSocket Live Status: Real-time updates from Sofie Live Status Gateway
Consistent Headers: All API calls use the same configured headers
Automatic Reconnection: WebSocket connection with automatic reconnection logic
Comprehensive Tools: Tools for rundown management, activation, and control

Installation

Clone or download the source files
Create the project structure:

```bash
mkdir sofie-mcp-server
cd sofie-mcp-server
mkdir src
```

Copy the main TypeScript file to src/index.ts
Install dependencies:

```bash
npm install
```

Configuration
Before using the server, you need to configure the headers in the SOFIE_CONFIG object:
typescriptconst SOFIE_CONFIG = {
  liveStatusUrl: 'wss://sofie-live-status.justingrayston.com',
  apiBaseUrl: 'https://ibc-sofie.justingrayston.com/api/v1.0',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': 'Bearer YOUR_ACTUAL_TOKEN', // Replace with your auth token
    'X-Client-ID': 'sofie-mcp-client', // Your custom headers
    // Add any other required headers here
  }
};
Building and Running
bash# Build the TypeScript
npm run build

# Run the server
npm start

# Or run in development mode
npm run dev
Available Tools
Connection Management

connect_live_status - Connect to Sofie Live Status Gateway WebSocket
disconnect_live_status - Disconnect from WebSocket

Rundown Management

get_rundowns - Get all rundowns
get_rundown - Get a specific rundown by ID
activate_rundown - Activate a rundown
deactivate_rundown - Deactivate a rundown

Content Management

get_segments - Get segments for a rundown
get_parts - Get parts for a segment

Playback Control

take_next - Take the next part in the rundown
move_next - Move to a specific part in the rundown

System Information

get_show_style_bases - Get all show style bases
get_studios - Get all studios

Usage with MCP Clients
This server can be used with any MCP-compatible client. The server communicates via stdio and provides structured responses for all operations.
Example Tool Calls
javascript// Get all rundowns
{
  "method": "tools/call",
  "params": {
    "name": "get_rundowns",
    "arguments": {}
  }
}

// Activate a specific rundown
{
  "method": "tools/call",
  "params": {
    "name": "activate_rundown",
    "arguments": {
      "rundownId": "your-rundown-id"
    }
  }
}

// Connect to live status updates
{
  "method": "tools/call",
  "params": {
    "name": "connect_live_status",
    "arguments": {}
  }
}
Error Handling
The server includes comprehensive error handling:

API request failures are caught and returned as structured errors
WebSocket connection failures trigger automatic reconnection
Invalid tool calls return appropriate MCP error responses

WebSocket Live Status
The WebSocket connection provides real-time updates from Sofie. Messages are automatically parsed and logged. The connection includes:

Automatic reconnection with exponential backoff
Configurable maximum reconnection attempts
Proper error handling and logging

Security Considerations

Replace placeholder tokens and authentication headers with real values
Ensure your headers include proper authentication for your Sofie instance
Consider using environment variables for sensitive configuration data

Dependencies

@modelcontextprotocol/sdk - MCP SDK for server implementation
ws - WebSocket client for live status connection
node-fetch - HTTP client for API requests

License
MIT License