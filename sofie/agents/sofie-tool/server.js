#!/usr/bin/env node

import dotenv from 'dotenv';
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

// Load environment variables
dotenv.config();

// Import your tool modules
import { rundownTools } from "./tools/rundown.js";

class SofieMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: "sofie-mcp-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  setupToolHandlers() {
    // Register list_tools handler
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          ...rundownTools.getToolDefinitions(),
          // Add other tool modules here as you build them
          // ...playoutTools.getToolDefinitions(),
          // ...systemTools.getToolDefinitions(),
        ]
      };
    });

    // Register call_tool handler
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        // Route to appropriate tool handler
        if (rundownTools.hasTools(name)) {
          return await rundownTools.callTool(name, args);
        }
        
        // Add other tool routing here
        // if (playoutTools.hasTools(name)) {
        //   return await playoutTools.callTool(name, args);
        // }

        throw new Error(`Unknown tool: ${name}`);
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error executing tool ${name}: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error("[MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Sofie MCP server running on stdio");
  }
}

// Start the server
const server = new SofieMCPServer();
server.run().catch((error) => {
  console.error("Failed to run server:", error);
  process.exit(1);
});