import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import {
	CallToolRequestSchema,
	CallToolResult,
	isInitializeRequest,
	ListResourcesRequestSchema,
	ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js'
import { randomUUID } from 'crypto'
import fastify, { FastifyBaseLogger, FastifyInstance, FastifyReply, FastifyRequest } from 'fastify'
import { logger } from '../config/log.js'
import { RundownTools } from '../tools/rundown/index.js'
import { Config } from '../typings/config/index.js'
import { logError } from '../util/index.js'

interface Session {
	[sessionId: string]: {
		transport: StreamableHTTPServerTransport
		rundownTools: RundownTools
		server: Server
	}
}

export class SofieMCPServer {
	private sessions: Session = {}

	private fastify?: FastifyInstance

	constructor(config: Config) {
		this.fastify = fastify({
			trustProxy: true,
			loggerInstance: logger.child(
				{},
				{
					msgPrefix: 'server - ',
					serializers: {
						req(req) {
							return {
								host: req.headers['x-forwarded-host'] ?? req.hostname,
								path: req.headers['x-forwarded-uri'] ?? req.url,
								clientIp: req.headers['x-forwarded-for'] ?? req.ip,
							}
						},
						res(res) {
							return {
								statusCode: res.statusCode,
							}
						},
					},
				},
			) as FastifyBaseLogger,
			genReqId: () => randomUUID(),
		})

		this.fastify.post('/mcp', async (req, reply) => {
			// Check for existing session ID
			const sessionId = req.headers['mcp-session-id'] as string | undefined
			let transport: StreamableHTTPServerTransport

			if (sessionId && this.sessions[sessionId]) {
				// Reuse existing transport
				transport = this.sessions[sessionId].transport
			} else if (!sessionId && isInitializeRequest(req.body)) {
				// New initialization request
				const server = new Server(
					{
						name: 'sofie-mcp-server',
						version: '1.0.0',
					},
					{
						capabilities: {
							tools: {},
							resources: {
								listChanged: true,
								subscribe: true,
							},
						},
					},
				)
				const rundownTools = new RundownTools(config, server)

				this.setupToolHandlers(server, rundownTools)
				this.setupErrorHandling(server)

				transport = new StreamableHTTPServerTransport({
					sessionIdGenerator: () => randomUUID(),
					onsessioninitialized: (sessionId) => {
						// Store the transport by session ID
						this.sessions[sessionId] = {
							server,
							rundownTools,
							transport,
						}
					},
					// DNS rebinding protection is disabled by default for backwards compatibility. If you are running this server
					// locally, make sure to set:
					// enableDnsRebindingProtection: true,
					// allowedHosts: ['127.0.0.1'],
				})

				// Clean up transport when closed
				transport.onclose = async () => {
					if (transport.sessionId) {
						if (this.sessions[transport.sessionId]) {
							await this.sessions[transport.sessionId].rundownTools?.close()
							await this.sessions[transport.sessionId].server?.close()
						}
						delete this.sessions[transport.sessionId]
					}
				}

				// ... set up server resources, tools, and prompts ...

				// Connect to the MCP server
				await server.connect(transport)
			} else {
				// Invalid request
				reply.status(400).send({
					jsonrpc: '2.0',
					error: {
						code: -32000,
						message: 'Bad Request: No valid session ID provided',
					},
					id: null,
				})
				return
			}

			// Handle the request
			await transport.handleRequest(req.raw, reply.raw, req.body)
		})

		// Reusable handler for GET and DELETE requests
		const handleSessionRequest = async (req: FastifyRequest, reply: FastifyReply) => {
			const sessionId = req.headers['mcp-session-id'] as string | undefined
			if (!sessionId || !this.sessions[sessionId]) {
				reply.status(400).send('Invalid or missing session ID')
				return
			}

			const session = this.sessions[sessionId]
			await session.transport.handleRequest(req.raw, reply.raw)
		}

		// Handle GET requests for server-to-client notifications via SSE
		this.fastify.get('/mcp', handleSessionRequest)

		// Handle DELETE requests for session termination
		this.fastify.delete('/mcp', handleSessionRequest)
	}

	private setupToolHandlers(server: Server, rundownTools: RundownTools) {
		// Register list_tools handler
		logger.info('ADK requested tools')
		server.setRequestHandler(ListToolsRequestSchema, async () => {
			return {
				tools: [
					...rundownTools.getToolDefinitions(),
					// Add other tool modules here as you build them
					// ...playoutTools.getToolDefinitions(),
					// ...systemTools.getToolDefinitions(),
				],
			}
		})

		server.setRequestHandler(ListResourcesRequestSchema, async () => {
			logger.info('ADK requested resources')
			return {
				resources: [
					{
						name: 'Active Playlist',
						uri: 'http://localhost/active-playlist',
					},
				],
			}
		})

		// Register call_tool handler
		server.setRequestHandler(CallToolRequestSchema, async (request): Promise<CallToolResult> => {
			const { name, arguments: args } = request.params

			try {
				// Route to appropriate tool handler
				if (rundownTools.hasTools(name)) {
					return await rundownTools.callTool(name, args)
				}

				// Add other tool routing here
				// if (playoutTools.hasTools(name)) {
				//   return await playoutTools.callTool(name, args);
				// }

				throw new Error(`Unknown tool: ${name}`)
			} catch (error) {
				let text: string
				if (error instanceof Error) {
					text = `Error executing tool ${name}: ${error.message}`
				} else {
					text = `Error executing tool ${name}`
				}

				return {
					content: [
						{
							type: 'text',
							text,
						},
					],
					isError: true,
				}
			}
		})
	}

	private setupErrorHandling(server: Server) {
		server.onerror = (e) => {
			logError(logger, 'error', 'MCP Error', e)
		}
	}

	async open() {
		await this.fastify?.listen({
			host: '0.0.0.0',
			port: 3000,
		})
		logger.info('Web Server Started')
	}

	async close() {
		await this.fastify?.close()
	}
}
