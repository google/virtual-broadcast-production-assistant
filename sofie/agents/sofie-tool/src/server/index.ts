import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { CallToolRequestSchema, CallToolResult, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js'
import { logger } from '../config/log.js'
import { RundownTools } from '../tools/rundown/index.js'
import { Config } from '../typings/config/index.js'
import { logError } from '../util/index.js'

export class SofieMCPServer {
	private readonly server: Server

	private readonly rundownTools: RundownTools

	constructor(config: Config) {
		this.server = new Server(
			{
				name: 'sofie-mcp-server',
				version: '1.0.0',
			},
			{
				capabilities: {
					tools: {},
				},
			},
		)
		this.rundownTools = new RundownTools(config)

		this.setupToolHandlers()
		this.setupErrorHandling()
	}

	setupToolHandlers() {
		// Register list_tools handler
		this.server.setRequestHandler(ListToolsRequestSchema, async () => {
			return {
				tools: [
					...this.rundownTools.getToolDefinitions(),
					// Add other tool modules here as you build them
					// ...playoutTools.getToolDefinitions(),
					// ...systemTools.getToolDefinitions(),
				],
			}
		})

		// Register call_tool handler
		this.server.setRequestHandler(CallToolRequestSchema, async (request): Promise<CallToolResult> => {
			const { name, arguments: args } = request.params

			try {
				// Route to appropriate tool handler
				if (this.rundownTools.hasTools(name)) {
					return await this.rundownTools.callTool(name, args)
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

	setupErrorHandling() {
		this.server.onerror = (e) => {
			logError(logger, 'error', 'MCP Error', e)
		}
	}

	async open() {
		const transport = new StdioServerTransport()
		await this.server.connect(transport)
		logger.info('Sofie MCP server running on stdio')
	}

	async close() {
		await this.server.close()
	}
}
