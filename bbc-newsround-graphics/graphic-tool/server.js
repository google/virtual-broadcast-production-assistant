#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from 'node-fetch';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const API_BASE_URL = process.env.API_BASE_URL;
const API_KEY_VALUE = process.env.API_KEY_VALUE;
const TARGET_IDENTIFIER = process.env.TARGET_IDENTIFIER || "ben";

const FULL_URL = `${API_BASE_URL}/v3/update/test/${TARGET_IDENTIFIER}`;

const HEADERS = {
  "ClientID": TARGET_IDENTIFIER,
  "api-key": API_KEY_VALUE,
  "Content-Type": "application/json",
};

const DEBUG = process.env.DEBUG === 'true';

class BroadcastGraphicsTools {
  constructor() {
    this.tools = [
      'update_name_on_strap',
      'name_off',
      'update_locator',
      'clear_locator',
      'update_headline',
      'clear_headline',
      'update_info_tab',
      'clear_info_tab',
      'update_credit',
      'clear_all_graphics'
    ];
  }

  getToolDefinitions() {
    return [
      {
        name: "update_name_on_strap",
        description: "Updates the name displayed on a digital strap with optional job title",
        inputSchema: {
          type: "object",
          properties: {
            person_name: {
              type: "string",
              description: "The name to be displayed on the strap",
            },
            job_title: {
              type: "string",
              description: "Optional job title to be displayed",
              default: "",
            },
          },
          required: ["person_name"],
        },
      },
      {
        name: "name_off",
        description: "Removes/clears the name displayed on the digital strap",
        inputSchema: {
          type: "object",
          properties: {},
          additionalProperties: false,
        },
      },
      {
        name: "update_locator",
        description: "Updates the locator graphic with location information",
        inputSchema: {
          type: "object",
          properties: {
            location: {
              type: "string",
              description: "The physical location to be displayed",
            },
            position: {
              type: "string",
              description: "Position of the locator (topLeft, topRight, bottomLeft, bottomRight)",
              enum: ["topLeft", "topRight", "bottomLeft", "bottomRight"],
              default: "topRight",
            },
            live: {
              type: "boolean",
              description: "Whether this is a live location",
              default: true,
            },
          },
          required: ["location"],
        },
      },
      {
        name: "clear_locator",
        description: "Removes/clears the locator graphic",
        inputSchema: {
          type: "object",
          properties: {
            position: {
              type: "string",
              description: "Position of the locator to clear",
              enum: ["topLeft", "topRight", "bottomLeft", "bottomRight"],
              default: "topRight",
            },
          },
          additionalProperties: false,
        },
      },
      {
        name: "update_headline",
        description: "Updates the headline/breaking strap with text",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "The headline text to be displayed",
            },
            breaking: {
              type: "boolean",
              description: "Whether this is a breaking news headline",
              default: true,
            },
          },
          required: ["text"],
        },
      },
      {
        name: "clear_headline",
        description: "Removes/clears the headline strap",
        inputSchema: {
          type: "object",
          properties: {},
          additionalProperties: false,
        },
      },
      {
        name: "update_info_tab",
        description: "Updates an info tab with title and information",
        inputSchema: {
          type: "object",
          properties: {
            title: {
              type: "string",
              description: "The title of the info tab",
            },
            info: {
              type: "string",
              description: "The information text to display",
            },
            colour: {
              type: "string",
              description: "Color scheme for the info tab",
              enum: ["teal", "purple", "orange"],
              default: "teal",
            },
          },
          required: ["title", "info"],
        },
      },
      {
        name: "clear_info_tab",
        description: "Removes/clears the info tab",
        inputSchema: {
          type: "object",
          properties: {},
          additionalProperties: false,
        },
      },
      {
        name: "update_credit",
        description: "Updates the credit strap with text",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "The credit text to be displayed",
            },
          },
          required: ["text"],
        },
      },
      {
        name: "clear_all_graphics",
        description: "Clears all graphics from all zones",
        inputSchema: {
          type: "object",
          properties: {},
          additionalProperties: false,
        },
      },
    ];
  }

  validateApiConfig() {
    if (!API_BASE_URL || !API_KEY_VALUE) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "API_BASE_URL or API_KEY_VALUE not configured in environment variables"
      );
    }
  }

  async makeApiRequest(payload) {
    this.validateApiConfig();
    
    try {
      const response = await fetch(FULL_URL, {
        method: 'POST',
        headers: HEADERS,
        body: JSON.stringify(payload),
        timeout: 10000
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const responseText = await response.text();
      return {
        success: true,
        response: responseText,
        payload: JSON.stringify(payload, null, 2)
      };
    } catch (error) {
      if (DEBUG) console.error('API request failed:', error);
      throw new McpError(
        ErrorCode.InternalError,
        `API request failed: ${error.message}`
      );
    }
  }

  hasTools(toolName) {
    return this.tools.includes(toolName);
  }

  async callTool(toolName, args) {
    try {
      switch (toolName) {
        case 'update_name_on_strap':
          return await this.updateNameOnStrap(args.person_name, args.job_title);
        case 'name_off':
          return await this.nameOff();
        case 'update_locator':
          return await this.updateLocator(args.location, args.position, args.live);
        case 'clear_locator':
          return await this.clearLocator(args.position);
        case 'update_headline':
          return await this.updateHeadline(args.text, args.breaking);
        case 'clear_headline':
          return await this.clearHeadline();
        case 'update_info_tab':
          return await this.updateInfoTab(args.title, args.info, args.colour);
        case 'clear_info_tab':
          return await this.clearInfoTab();
        case 'update_credit':
          return await this.updateCredit(args.text);
        case 'clear_all_graphics':
          return await this.clearAllGraphics();
        default:
          throw new Error(`Unknown tool: ${toolName}`);
      }
    } catch (error) {
      if (DEBUG) console.error(`Error in ${toolName}:`, error);
      throw error;
    }
  }

  async updateNameOnStrap(personName, jobTitle = '') {
    const strapProps = {
      style: "name",
      isBreakingMode: false,
      text1: personName
    };

    if (jobTitle && jobTitle.trim() !== '') {
      strapProps.text2 = jobTitle;
    }

    const payload = {
      data: {
        mainStrap: {
          action: "take",
          component: "Strap",
          props: strapProps,
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully updated name strap for '${TARGET_IDENTIFIER}' with name '${personName}'${jobTitle ? ` and job title '${jobTitle}'` : ''}`,
        },
      ],
    };
  }

  async nameOff() {
    const payload = {
      data: {
        mainStrap: {
          action: "clear",
          component: "Strap",
          props: {},
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully cleared name strap for '${TARGET_IDENTIFIER}'`,
        },
      ],
    };
  }

  async updateLocator(location, position = 'topRight', live = true) {
    const locatorProps = {
      mode: live ? 'LIVE' : null,
      label: location
    };

    const payload = {
      data: {
        [position]: {
          action: "take",
          component: "Locator",
          props: locatorProps,
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully updated locator for '${TARGET_IDENTIFIER}' with location '${location}' at position '${position}'${live ? ' (LIVE)' : ''}`,
        },
      ],
    };
  }

  async clearLocator(position = 'topRight') {
    const payload = {
      data: {
        [position]: {
          action: "clear"
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully cleared locator at position '${position}' for '${TARGET_IDENTIFIER}'`,
        },
      ],
    };
  }

  async updateHeadline(text, breaking = true) {
    const headlineProps = {
      style: "banner",
      isBreakingMode: breaking,
      text1: text
    };

    const payload = {
      data: {
        mainStrap: {
          action: "take",
          component: "Strap",
          props: headlineProps,
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully updated ${breaking ? 'breaking ' : ''}headline strap for '${TARGET_IDENTIFIER}' with text '${text}'`,
        },
      ],
    };
  }

  async clearHeadline() {
    const payload = {
      data: {
        mainStrap: {
          action: "clear",
          component: "Strap",
          props: {},
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully cleared headline strap for '${TARGET_IDENTIFIER}'`,
        },
      ],
    };
  }

  async updateInfoTab(title, info, colour = 'teal') {
    const infoTabProps = {
      text1: title,
      text2: info,
      color: colour
    };

    const payload = {
      data: {
        bottomRight: {
          action: "take",
          component: "InfoTab",
          props: infoTabProps,
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully updated info tab for '${TARGET_IDENTIFIER}' with title '${title}' and info '${info}' in ${colour} color`,
        },
      ],
    };
  }

  async clearInfoTab() {
    const payload = {
      data: {
        bottomRight: {
          action: "clear"
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully cleared info tab for '${TARGET_IDENTIFIER}'`,
        },
      ],
    };
  }

  async updateCredit(text) {
    const creditProps = {
      style: "name",
      isBreakingMode: false,
      text1: "",
      text2: text
    };

    const payload = {
      data: {
        mainStrap: {
          action: "take",
          component: "Strap",
          props: creditProps,
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully updated credit strap for '${TARGET_IDENTIFIER}' with text '${text}'`,
        },
      ],
    };
  }

  async clearAllGraphics() {
    const payload = {
      data: {
        fullFrame: {
          action: "clear"
        }
      }
    };

    const result = await this.makeApiRequest(payload);
    return {
      content: [
        {
          type: "text",
          text: `✅ Successfully cleared all graphics for '${TARGET_IDENTIFIER}'`,
        },
      ],
    };
  }
}

class BroadcastGraphicsServer {
  constructor() {
    this.server = new Server(
      {
        name: "broadcast-graphics",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.broadcastTools = new BroadcastGraphicsTools();
    this.setupToolHandlers();
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: this.broadcastTools.getToolDefinitions(),
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        if (!this.broadcastTools.hasTools(name)) {
          throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
        }

        return await this.broadcastTools.callTool(name, args);
      } catch (error) {
        if (error instanceof McpError) {
          throw error;
        }
        throw new McpError(ErrorCode.InternalError, `Tool execution failed: ${error.message}`);
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Broadcast Graphics MCP server running on stdio");
  }
}

const server = new BroadcastGraphicsServer();
server.run().catch(console.error);