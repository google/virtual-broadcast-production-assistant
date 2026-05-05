#!/usr/bin/env node

import dotenv from 'dotenv';
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

// Load environment variables
dotenv.config();

// Import your tool modules
import { websiteTools } from "./website.js";

class WebsiteMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: "website-mcp-server",
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
          ...websiteTools.getToolDefinitions(),
        ]
      };
    });

    // Register call_tool handler
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        // Route to appropriate tool handler
        if (websiteTools.hasTools(name)) {
          return await websiteTools.callTool(name, args);
        }

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
      console.error("[Website MCP Error]", error);
    };

    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Website MCP server running on stdio");
  }
}

// Start the server
const server = new WebsiteMCPServer();
server.run().catch((error) => {
  console.error("Failed to run website server:", error);
  process.exit(1);
});