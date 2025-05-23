import axios from 'axios';

// Configuration from environment variables
const SOFIE_API_BASE = process.env.SOFIE_API_BASE || 'http://localhost:3000/api';
const SOFIE_API_KEY = process.env.SOFIE_API_KEY;
const DEBUG = process.env.DEBUG === 'true';

// Create axios instance with common config
const apiClient = axios.create({
  baseURL: SOFIE_API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    ...(SOFIE_API_KEY && { 'Authorization': `Bearer ${SOFIE_API_KEY}` })
  }
});

// Add request/response interceptors for debugging
if (DEBUG) {
  apiClient.interceptors.request.use(request => {
    console.log('API Request:', request.method?.toUpperCase(), request.url);
    return request;
  });
  
  apiClient.interceptors.response.use(
    response => {
      console.log('API Response:', response.status, response.config.url);
      return response;
    },
    error => {
      console.log('API Error:', error.message);
      return Promise.reject(error);
    }
  );
}

class RundownTools {
  constructor() {
    this.tools = [
      'get_rundown',
      'list_rundowns',
      'get_rundown_status',
      'activate_rundown'
    ];
  }

  getToolDefinitions() {
    return [
      {
        name: "get_rundown",
        description: "Get details about a specific rundown by ID",
        inputSchema: {
          type: "object",
          properties: {
            rundownId: {
              type: "string",
              description: "The ID of the rundown to retrieve"
            }
          },
          required: ["rundownId"]
        }
      },
      {
        name: "list_rundowns",
        description: "List all available rundowns",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Maximum number of rundowns to return (default: 10)"
            }
          }
        }
      },
      {
        name: "get_rundown_status",
        description: "Get the current status of a rundown",
        inputSchema: {
          type: "object",
          properties: {
            rundownId: {
              type: "string",
              description: "The ID of the rundown to check status for"
            }
          },
          required: ["rundownId"]
        }
      },
      {
        name: "activate_rundown",
        description: "Activate a rundown for playout",
        inputSchema: {
          type: "object",
          properties: {
            rundownId: {
              type: "string",
              description: "The ID of the rundown to activate"
            }
          },
          required: ["rundownId"]
        }
      }
    ];
  }

  hasTools(toolName) {
    return this.tools.includes(toolName);
  }

  async callTool(toolName, args) {
    switch (toolName) {
      case 'get_rundown':
        return await this.getRundown(args.rundownId);
      
      case 'list_rundowns':
        return await this.listRundowns(args.limit || 10);
      
      case 'get_rundown_status':
        return await this.getRundownStatus(args.rundownId);
      
      case 'activate_rundown':
        return await this.activateRundown(args.rundownId);
      
      default:
        throw new Error(`Unknown rundown tool: ${toolName}`);
    }
  }

  async getRundown(rundownId) {
    try {
      const response = await apiClient.get(`/rundowns/${rundownId}`);
      
      return {
        content: [
          {
            type: "text",
            text: `Rundown Details:\n${JSON.stringify(response.data, null, 2)}`
          }
        ]
      };
    } catch (error) {
      if (DEBUG) console.error('getRundown error:', error.message);
      
      // For demo purposes, return mock data
      return {
        content: [
          {
            type: "text",
            text: `Mock Rundown Data for ID: ${rundownId}\n` +
                  `Name: Evening News\n` +
                  `Duration: 30:00\n` +
                  `Segments: 8\n` +
                  `Status: Ready\n` +
                  `Created: 2025-05-23T10:00:00Z\n` +
                  `(Using mock data - check SOFIE_API_BASE: ${SOFIE_API_BASE})`
          }
        ]
      };
    }
  }

  async listRundowns(limit) {
    try {
      const response = await apiClient.get(`/rundowns?limit=${limit}`);
      
      return {
        content: [
          {
            type: "text",
            text: `Available Rundowns:\n${JSON.stringify(response.data, null, 2)}`
          }
        ]
      };
    } catch (error) {
      if (DEBUG) console.error('listRundowns error:', error.message);
      
      // For demo purposes, return mock data
      return {
        content: [
          {
            type: "text",
            text: `Mock Rundowns List (limit: ${limit}):\n` +
                  `1. Evening News - Status: Ready\n` +
                  `2. Morning Show - Status: Active\n` +
                  `3. Sports Update - Status: Draft\n` +
                  `4. Weather Report - Status: Ready\n` +
                  `(Using mock data - check SOFIE_API_BASE: ${SOFIE_API_BASE})`
          }
        ]
      };
    }
  }

  async getRundownStatus(rundownId) {
    try {
      const response = await apiClient.get(`/rundowns/${rundownId}/status`);
      
      return {
        content: [
          {
            type: "text",
            text: `Rundown Status:\n${JSON.stringify(response.data, null, 2)}`
          }
        ]
      };
    } catch (error) {
      if (DEBUG) console.error('getRundownStatus error:', error.message);
      
      // For demo purposes, return mock data
      return {
        content: [
          {
            type: "text",
            text: `Mock Status for Rundown ${rundownId}:\n` +
                  `Status: Ready\n` +
                  `Current Segment: 0\n` +
                  `Next Segment: Intro\n` +
                  `On Air: false\n` +
                  `Last Updated: ${new Date().toISOString()}\n` +
                  `(Using mock data - check SOFIE_API_BASE: ${SOFIE_API_BASE})`
          }
        ]
      };
    }
  }

  async activateRundown(rundownId) {
    try {
      const response = await apiClient.post(`/rundowns/${rundownId}/activate`);
      
      return {
        content: [
          {
            type: "text",
            text: `Rundown activated successfully:\n${JSON.stringify(response.data, null, 2)}`
          }
        ]
      };
    } catch (error) {
      if (DEBUG) console.error('activateRundown error:', error.message);
      
      // For demo purposes, return mock success
      return {
        content: [
          {
            type: "text",
            text: `Mock: Rundown ${rundownId} activated successfully!\n` +
                  `Status: Active\n` +
                  `Activated at: ${new Date().toISOString()}\n` +
                  `Ready for playout: true\n` +
                  `(Using mock data - check SOFIE_API_BASE: ${SOFIE_API_BASE})`
          }
        ]
      };
    }
  }
}

export const rundownTools = new RundownTools();