#!/usr/bin/env node
// This file should be saved as src/index.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ErrorCode, ListToolsRequestSchema, McpError, } from '@modelcontextprotocol/sdk/types.js';
import WebSocket from 'ws';
import fetch from 'node-fetch';
// Configuration
const SOFIE_CONFIG = {
    liveStatusUrl: 'wss://sofie-live-status.justingrayston.com',
    apiBaseUrl: 'https://ibc-sofie.justingrayston.com/api/v1.0',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        // Add your specific headers here
        'Authorization': 'Bearer YOUR_TOKEN_HERE', // Replace with actual auth
        'X-Client-ID': 'sofie-mcp-client', // Example custom header
    }
};
class SofieWebSocketClient {
    ws = null;
    reconnectAttempts = 0;
    maxReconnectAttempts = 5;
    reconnectDelay = 1000;
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(SOFIE_CONFIG.liveStatusUrl, {
                    headers: SOFIE_CONFIG.headers
                });
                this.ws.on('open', () => {
                    console.log('Connected to Sofie Live Status Gateway');
                    this.reconnectAttempts = 0;
                    resolve();
                });
                this.ws.on('message', (data) => {
                    try {
                        const message = JSON.parse(data.toString());
                        console.log('Received live status update:', message);
                    }
                    catch (error) {
                        console.error('Failed to parse WebSocket message:', error);
                    }
                });
                this.ws.on('close', () => {
                    console.log('WebSocket connection closed');
                    this.attemptReconnect();
                });
                this.ws.on('error', (error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                });
            }
            catch (error) {
                reject(error);
            }
        });
    }
    async attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(async () => {
                try {
                    await this.connect();
                }
                catch (error) {
                    console.error('Reconnection failed:', error);
                }
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }
    async sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
        else {
            throw new Error('WebSocket is not connected');
        }
    }
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
class SofieApiClient {
    async makeRequest(endpoint, method = 'GET', body) {
        const url = `${SOFIE_CONFIG.apiBaseUrl}${endpoint}`;
        const options = {
            method,
            headers: SOFIE_CONFIG.headers,
        };
        if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(body);
        }
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            else {
                return await response.text();
            }
        }
        catch (error) {
            throw new Error(`Failed to make API request to ${url}: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async getRundowns() {
        return this.makeRequest('/rundowns');
    }
    async getRundown(rundownId) {
        return this.makeRequest(`/rundowns/${rundownId}`);
    }
    async getSegments(rundownId) {
        return this.makeRequest(`/rundowns/${rundownId}/segments`);
    }
    async getParts(rundownId, segmentId) {
        return this.makeRequest(`/rundowns/${rundownId}/segments/${segmentId}/parts`);
    }
    async activateRundown(rundownId) {
        return this.makeRequest(`/rundowns/${rundownId}/activate`, 'POST');
    }
    async deactivateRundown(rundownId) {
        return this.makeRequest(`/rundowns/${rundownId}/deactivate`, 'POST');
    }
    async takeNext(rundownId) {
        return this.makeRequest(`/rundowns/${rundownId}/take`, 'POST');
    }
    async moveNext(rundownId, partId) {
        return this.makeRequest(`/rundowns/${rundownId}/moveNext`, 'POST', { partId });
    }
    async getShowStyleBases() {
        return this.makeRequest('/showStyleBases');
    }
    async getStudios() {
        return this.makeRequest('/studios');
    }
}
// Initialize clients
const wsClient = new SofieWebSocketClient();
const apiClient = new SofieApiClient();
// Create MCP server
const server = new Server({
    name: 'sofie-automation-mcp',
    version: '0.1.0',
    capabilities: {
        tools: {},
    },
});
;
// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'connect_live_status',
                description: 'Connect to Sofie Live Status Gateway WebSocket',
                inputSchema: {
                    type: 'object',
                    properties: {},
                },
            },
            {
                name: 'disconnect_live_status',
                description: 'Disconnect from Sofie Live Status Gateway WebSocket',
                inputSchema: {
                    type: 'object',
                    properties: {},
                },
            },
            {
                name: 'get_rundowns',
                description: 'Get all rundowns from Sofie',
                inputSchema: {
                    type: 'object',
                    properties: {},
                },
            },
            {
                name: 'get_rundown',
                description: 'Get a specific rundown by ID',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown to retrieve',
                        },
                    },
                    required: ['rundownId'],
                },
            },
            {
                name: 'get_segments',
                description: 'Get segments for a specific rundown',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown',
                        },
                    },
                    required: ['rundownId'],
                },
            },
            {
                name: 'get_parts',
                description: 'Get parts for a specific segment in a rundown',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown',
                        },
                        segmentId: {
                            type: 'string',
                            description: 'The ID of the segment',
                        },
                    },
                    required: ['rundownId', 'segmentId'],
                },
            },
            {
                name: 'activate_rundown',
                description: 'Activate a rundown',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown to activate',
                        },
                    },
                    required: ['rundownId'],
                },
            },
            {
                name: 'deactivate_rundown',
                description: 'Deactivate a rundown',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown to deactivate',
                        },
                    },
                    required: ['rundownId'],
                },
            },
            {
                name: 'take_next',
                description: 'Take the next part in the rundown',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown',
                        },
                    },
                    required: ['rundownId'],
                },
            },
            {
                name: 'move_next',
                description: 'Move to the next part in the rundown',
                inputSchema: {
                    type: 'object',
                    properties: {
                        rundownId: {
                            type: 'string',
                            description: 'The ID of the rundown',
                        },
                        partId: {
                            type: 'string',
                            description: 'The ID of the part to move to',
                        },
                    },
                    required: ['rundownId', 'partId'],
                },
            },
            {
                name: 'get_show_style_bases',
                description: 'Get all show style bases',
                inputSchema: {
                    type: 'object',
                    properties: {},
                },
            },
            {
                name: 'get_studios',
                description: 'Get all studios',
                inputSchema: {
                    type: 'object',
                    properties: {},
                },
            },
        ],
    };
});
// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
        switch (name) {
            case 'connect_live_status':
                await wsClient.connect();
                return {
                    content: [
                        {
                            type: 'text',
                            text: 'Successfully connected to Sofie Live Status Gateway',
                        },
                    ],
                };
            case 'disconnect_live_status':
                wsClient.disconnect();
                return {
                    content: [
                        {
                            type: 'text',
                            text: 'Disconnected from Sofie Live Status Gateway',
                        },
                    ],
                };
            case 'get_rundowns':
                const rundowns = await apiClient.getRundowns();
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(rundowns, null, 2),
                        },
                    ],
                };
            case 'get_rundown':
                if (!args || typeof args !== 'object' || !('rundownId' in args) || typeof args.rundownId !== 'string') {
                    throw new Error('rundownId is required and must be a string');
                }
                const rundown = await apiClient.getRundown(args.rundownId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(rundown, null, 2),
                        },
                    ],
                };
            case 'get_segments':
                if (!args || typeof args !== 'object' || !('rundownId' in args) || typeof args.rundownId !== 'string') {
                    throw new Error('rundownId is required and must be a string');
                }
                const segments = await apiClient.getSegments(args.rundownId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(segments, null, 2),
                        },
                    ],
                };
            case 'get_parts':
                if (!args || typeof args !== 'object' ||
                    !('rundownId' in args) || typeof args.rundownId !== 'string' ||
                    !('segmentId' in args) || typeof args.segmentId !== 'string') {
                    throw new Error('rundownId and segmentId are required and must be strings');
                }
                const parts = await apiClient.getParts(args.rundownId, args.segmentId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(parts, null, 2),
                        },
                    ],
                };
            case 'activate_rundown':
                if (!args || typeof args !== 'object' || !('rundownId' in args) || typeof args.rundownId !== 'string') {
                    throw new Error('rundownId is required and must be a string');
                }
                const activateResult = await apiClient.activateRundown(args.rundownId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `Rundown activated: ${JSON.stringify(activateResult, null, 2)}`,
                        },
                    ],
                };
            case 'deactivate_rundown':
                if (!args || typeof args !== 'object' || !('rundownId' in args) || typeof args.rundownId !== 'string') {
                    throw new Error('rundownId is required and must be a string');
                }
                const deactivateResult = await apiClient.deactivateRundown(args.rundownId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `Rundown deactivated: ${JSON.stringify(deactivateResult, null, 2)}`,
                        },
                    ],
                };
            case 'take_next':
                if (!args || typeof args !== 'object' || !('rundownId' in args) || typeof args.rundownId !== 'string') {
                    throw new Error('rundownId is required and must be a string');
                }
                const takeResult = await apiClient.takeNext(args.rundownId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `Took next: ${JSON.stringify(takeResult, null, 2)}`,
                        },
                    ],
                };
            case 'move_next':
                if (!args || typeof args !== 'object' ||
                    !('rundownId' in args) || typeof args.rundownId !== 'string' ||
                    !('partId' in args) || typeof args.partId !== 'string') {
                    throw new Error('rundownId and partId are required and must be strings');
                }
                const moveResult = await apiClient.moveNext(args.rundownId, args.partId);
                return {
                    content: [
                        {
                            type: 'text',
                            text: `Moved to next: ${JSON.stringify(moveResult, null, 2)}`,
                        },
                    ],
                };
            case 'get_show_style_bases':
                const showStyleBases = await apiClient.getShowStyleBases();
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(showStyleBases, null, 2),
                        },
                    ],
                };
            case 'get_studios':
                const studios = await apiClient.getStudios();
                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(studios, null, 2),
                        },
                    ],
                };
            default:
                throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
        }
    }
    catch (error) {
        throw new McpError(ErrorCode.InternalError, `Error executing tool ${name}: ${error instanceof Error ? error.message : String(error)}`);
    }
});
// Start the server
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Sofie MCP server started');
}
main().catch(console.error);
