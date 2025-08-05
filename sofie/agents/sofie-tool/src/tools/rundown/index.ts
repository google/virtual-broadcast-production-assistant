import { CallToolResult, ListToolsResultSchema } from '@modelcontextprotocol/sdk/types.js'
import { DeviceItem, PlaylistItem, ShowStyleBaseItem, StudioItem } from '@sofie-automation/openapi'
import { GoogleAuth } from 'google-auth-library'
import { Dispatcher, EnvHttpProxyAgent, request } from 'undici'
import { logger } from '../../config/log.js'
import { version } from '../../config/version.js'
import { Config } from '../../typings/config/index.js'
import { logError } from '../../util/index.js'
import { toolDefinitions } from './definitions.js'
import { SofieWebsocket } from './websocket.js'

type Tools = (typeof ListToolsResultSchema)['_output']['tools']

export class RundownTools {
	private readonly tools: Tools

	private readonly config: Config

	private readonly auth: GoogleAuth

	private readonly dispatcher = new EnvHttpProxyAgent()

	private readonly ws: SofieWebsocket

	constructor(config: Config) {
		this.config = config
		this.tools = this.getToolDefinitions()
		this.auth = new GoogleAuth({
			keyFile: this.config.serviceAccountPath,
		})
		this.ws = new SofieWebsocket(config)
	}

	async open() {
		await this.ws.open()
	}

	async close() {
		this.ws.close()
	}

	private async request(
		endpoint: string,
		body?: Record<string, any>,
		method?: Dispatcher.RequestOptions['method'],
	): Promise<Record<string, any> | undefined> {
		const token = await this.getToken()
		const url = new URL(this.config.sofieApiBase + endpoint)
		const reqBody = body ? JSON.stringify(body) : undefined

		logger.debug(`Sending request to ${url} - Method: ${method} - Body: ${reqBody}`)

		const result = await request(url, {
			dispatcher: this.dispatcher,
			body: reqBody,
			method,
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json',
				Accept: 'application/json',
				'User-Agent': `Sofie-MCP-Client/${version}`,
			},
		})

		if (result.statusCode < 200 || result.statusCode > 299) {
			const resultBody = await result.body.text()
			logger.debug(`Error response from API - Code: ${result.statusCode} - Body: ${resultBody}`)
			throw new Error(`Error response from API - Code: ${result.statusCode} - Body: ${resultBody}`)
		}
		const resultBody = await result.body.text()
		if (!resultBody) {
			return undefined
		}
		logger.debug(`Success response from API - Body: ${resultBody}`)
		return JSON.parse(resultBody)
	}

	private async getToken() {
		const client = await this.auth.getIdTokenClient(this.config.iapClientId)
		return await client.idTokenProvider.fetchIdToken(this.config.iapClientId)
	}

	private getResponse(text: string, error?: unknown): CallToolResult {
		if (error instanceof Error) {
			text += `: ${error.message}`
		}
		const result: CallToolResult = {
			content: [
				{
					type: 'text',
					text,
				},
			],
		}
		logger.debug(`Sending result: ${JSON.stringify(result)}`)
		return result
	}

	getToolDefinitions(): Tools {
		return toolDefinitions
	}

	hasTools(toolName: string) {
		return this.tools.find((t) => t.name === toolName)
	}

	async callTool(toolName: string, args: Record<string, any>) {
		logger.debug(`Tool: '${toolName}' called with ${JSON.stringify(args)}`)
		try {
			switch (toolName) {
				// Basic playlist operations
				case 'list_playlists':
					return await this.listPlaylists()
				case 'get_playlist':
					return await this.getPlaylist(args.playlistId)
				case 'get_playlist_status':
					return await this.getPlaylistStatus(args.playlistId)

				// Playlist lifecycle management
				case 'activate_playlist':
					return await this.activatePlaylist(args.playlistId, args.rehearsal)
				case 'deactivate_playlist':
					return await this.deactivatePlaylist(args.playlistId)
				case 'reload_playlist':
					return await this.reloadPlaylist(args.playlistId)
				case 'reset_playlist':
					return await this.resetPlaylist(args.playlistId)

				// Playout control
				case 'take':
					return await this.take(args.playlistId, args.fromPartInstanceId)
				case 'set_next_part':
					return await this.setNextPart(args.playlistId, args.partId)
				case 'set_next_segment':
					return await this.setNextSegment(args.playlistId, args.segmentId)
				case 'move_next_part':
					return await this.moveNextPart(args.playlistId, args.delta)
				case 'move_next_segment':
					return await this.moveNextSegment(args.playlistId, args.delta, args.ignoreQuickLoop)
				case 'queue_next_segment':
					return await this.queueNextSegment(args.playlistId, args.segmentId)

				// AdLib operations
				case 'execute_adlib':
					return await this.executeAdLib(args.playlistId, args.adLibId, args.actionType, args.adLibOptions)
				case 'execute_bucket_adlib':
					return await this.executeBucketAdLib(args.playlistId, args.bucketId, args.externalId, args.actionType)

				// Source layer control
				case 'clear_source_layers':
					return await this.clearSourceLayers(args.playlistId, args.sourceLayerIds)
				case 'clear_source_layer':
					return await this.clearSourceLayer(args.playlistId, args.sourceLayerId)
				case 'recall_sticky':
					return await this.recallSticky(args.playlistId, args.sourceLayerId)

				// System information
				case 'get_studios':
					return await this.getStudios()
				case 'get_showstyles':
					return await this.getShowStyles()
				case 'get_devices':
					return await this.getDevices()
				case 'get_system_status':
					return await this.getSystemStatus()

				default:
					throw new Error(`Unknown tool: ${toolName}`)
			}
		} catch (error) {
			logError(logger, 'error', `Error in ${toolName}`, error)
			if (error instanceof Error) {
				throw new Error(`Error in ${toolName}`, {
					cause: error,
				})
			} else {
				throw new Error(`Error in ${toolName}`)
			}
		}
	}

	// Basic playlist operations
	private async listPlaylists() {
		try {
			const response = await this.request('/playlists')

			if (!response || !response.result) {
				throw new Error('Invalid response format')
			}

			const playlists: PlaylistItem[] = response.result
			return this.getResponse(
				`Found ${playlists.length} playlist(s):\n\n` +
					playlists.map((playlist, index) => `${index + 1}. Playlist ID: ${playlist.id}`).join('\n'),
			)
		} catch (error) {
			return this.getResponse('❌ Failed to list playlists', error)
		}
	}

	// THIS DOESN'T EXIST
	private async getPlaylist(playlistId: string) {
		try {
			const response = await this.request(`/playlists/${playlistId}`)
			return this.getResponse(`Playlist Details:\n\n${JSON.stringify(response, null, 2)}`)
		} catch (error) {
			return this.getResponse(`❌ Failed to get playlist ${playlistId}`, error)
		}
	}

	// NEITHER DOES THIS # lol
	private async getPlaylistStatus(playlistId: string) {
		try {
			const response = await this.request(`/playlists/${playlistId}/status`)
			return this.getResponse(`Playlist Status:\n\n${JSON.stringify(response, null, 2)}`)
		} catch (error) {
			return this.getResponse('❌ Failed to get playlist status', error)
		}
	}

	// Playlist lifecycle management
	private async activatePlaylist(playlistId: string, rehearsal = false) {
		try {
			await this.request(`/playlists/${playlistId}/activate`, {
				rehearsal,
			})
			return this.getResponse(
				`✅ Playlist ${playlistId} activated successfully!\nMode: ${rehearsal ? 'Rehearsal' : 'Live'}`,
			)
		} catch (error) {
			return this.getResponse(`❌ Failed to activate playlist ${playlistId}`, error)
		}
	}

	private async deactivatePlaylist(playlistId: string) {
		try {
			await this.request(`/playlists/${playlistId}/deactivate`, undefined, 'PUT')
			return this.getResponse(`✅ Playlist ${playlistId} deactivated successfully!`)
		} catch (error) {
			return this.getResponse(`❌ Failed to deactivate playlist ${playlistId}`, error)
		}
	}

	private async reloadPlaylist(playlistId: string) {
		try {
			await this.request(`/playlists/${playlistId}/reload`, undefined, 'PUT')
			return this.getResponse(`✅ Playlist ${playlistId} reloaded successfully!`)
		} catch (error) {
			return this.getResponse(`❌ Failed to reload playlist ${playlistId}`, error)
		}
	}

	private async resetPlaylist(playlistId: string) {
		try {
			await this.request(`/playlists/${playlistId}/reset`, undefined, 'PUT')
			return this.getResponse(`✅ Playlist ${playlistId} reset successfully!`)
		} catch (error) {
			return this.getResponse(`❌ Failed to reset playlist ${playlistId}`, error)
		}
	}

	// Playout control
	private async take(playlistId: string, fromPartInstanceId?: string) {
		try {
			const requestBody = fromPartInstanceId ? { fromPartInstanceId } : {}
			await this.request(`/playlists/${playlistId}/take`, requestBody, 'POST')
			return this.getResponse(`✅ Take executed successfully for playlist ${playlistId}!`)
		} catch (error) {
			return this.getResponse('❌ Failed to take', error)
		}
	}

	private async setNextPart(playlistId: string, partId: string) {
		try {
			await this.request(`/playlists/${playlistId}/set-next-part`, {
				partId,
			})
			return this.getResponse(`✅ Next part set to ${partId} for playlist ${playlistId}`)
		} catch (error) {
			return this.getResponse('❌ Failed to set next part', error)
		}
	}

	private async setNextSegment(playlistId: string, segmentId: string) {
		try {
			const response = await this.request(
				`/playlists/${playlistId}/set-next-segment`,
				{
					segmentId,
				},
				'POST',
			)
			return this.getResponse(`✅ Next segment set to ${segmentId}. Result: ${JSON.stringify(response?.result)}`)
		} catch (error) {
			return this.getResponse('❌ Failed to set next segment', error)
		}
	}

	private async moveNextPart(playlistId: string, delta: number) {
		try {
			const response = await this.request(
				`/playlists/${playlistId}/move-next-part`,
				{
					delta,
				},
				'POST',
			)
			return this.getResponse(`✅ Next part moved by ${delta}. New part: ${response?.result}`)
		} catch (error) {
			return this.getResponse('❌ Failed to move next part', error)
		}
	}

	private async moveNextSegment(playlistId: string, delta: number, ignoreQuickLoop?: boolean) {
		try {
			const requestBody: Record<string, any> = { delta }
			if (ignoreQuickLoop !== undefined) {
				requestBody.ignoreQuickLoop = ignoreQuickLoop
			}
			const response = await this.request(`/playlists/${playlistId}/move-next-segment`, requestBody, 'POST')
			return this.getResponse(`✅ Next segment moved by ${delta}. New part: ${response?.result}`)
		} catch (error) {
			return this.getResponse('❌ Failed to move next segment', error)
		}
	}

	private async queueNextSegment(playlistId: string, segmentId: string) {
		try {
			const response = await this.request(
				`/playlists/${playlistId}/queue-next-segment`,
				{
					segmentId,
				},
				'POST',
			)
			return this.getResponse(`✅ Segment queued. Result: ${JSON.stringify(response?.result)}`)
		} catch (error) {
			return this.getResponse('❌ Failed to queue segment', error)
		}
	}

	// AdLib operations
	private async executeAdLib(
		playlistId: string,
		adLibId: string,
		actionType?: string,
		adLibOptions?: Record<string, any>,
	) {
		try {
			const requestBody: Record<string, any> = { adLibId }
			if (actionType) {
				requestBody.actionType = actionType
			}
			if (adLibOptions) {
				requestBody.adLibOptions = adLibOptions
			}
			const response = await this.request(`/playlists/${playlistId}/execute-adlib`, requestBody, 'POST')
			return this.getResponse(`✅ AdLib executed. Result: ${JSON.stringify(response?.result)}`)
		} catch (error) {
			return this.getResponse('❌ Failed to execute AdLib', error)
		}
	}

	private async executeBucketAdLib(playlistId: string, bucketId: string, externalId: string, actionType?: string) {
		try {
			const requestBody: Record<string, any> = { bucketId, externalId }
			if (actionType) {
				requestBody.actionType = actionType
			}
			const response = await this.request(`/playlists/${playlistId}/execute-bucket-adlib`, requestBody, 'POST')
			return this.getResponse(`✅ Bucket AdLib executed. Result: ${JSON.stringify(response?.result)}`)
		} catch (error) {
			return this.getResponse('❌ Failed to execute bucket AdLib', error)
		}
	}

	// Source layer control
	private async clearSourceLayers(playlistId: string, sourceLayerIds: string[]) {
		try {
			await this.request(`/playlists/${playlistId}/clear-sourcelayers`, {
				sourceLayerIds,
			})
			return this.getResponse(`✅ Source layers cleared: ${sourceLayerIds.join(', ')}`)
		} catch (error) {
			return this.getResponse('❌ Failed to clear source layers', error)
		}
	}

	private async clearSourceLayer(playlistId: string, sourceLayerId: string) {
		try {
			await this.request(`/playlists/${playlistId}/sourcelayer/${sourceLayerId}`, undefined, 'DELETE')
			return this.getResponse(`✅ Source layer ${sourceLayerId} cleared (deprecated endpoint)`)
		} catch (error) {
			return this.getResponse('❌ Failed to clear source layer', error)
		}
	}

	private async recallSticky(playlistId: string, sourceLayerId: string) {
		try {
			await this.request(`/playlists/${playlistId}/sourcelayer/${sourceLayerId}/sticky`, undefined, 'POST')
			return this.getResponse(`✅ Sticky piece recalled for source layer ${sourceLayerId}`)
		} catch (error) {
			return this.getResponse('❌ Failed to recall sticky', error)
		}
	}

	// System information (unchanged)
	private async getStudios() {
		try {
			const response = await this.request('/studios')
			if (!response || !response.result) {
				throw new Error('Invalid response format')
			}
			const studios: StudioItem[] = response.result
			return this.getResponse(
				`Available Studios:\n\n` + studios.map((studio, index) => `${index + 1}. Studio ID: ${studio.id}`).join('\n'),
			)
		} catch (error) {
			return this.getResponse('❌ Failed to get studios', error)
		}
	}

	private async getShowStyles() {
		try {
			const response = await this.request('/showstyles')
			if (!response || !response.result) {
				throw new Error('Invalid response format')
			}
			const showStyles: ShowStyleBaseItem[] = response.result
			return this.getResponse(
				`Available Show Styles:\n\n` +
					showStyles.map((style, index) => `${index + 1}. Show Style ID: ${style.id}`).join('\n'),
			)
		} catch (error) {
			return this.getResponse('❌ Failed to get showstyles', error)
		}
	}

	private async getDevices() {
		try {
			const response = await this.request('/devices')
			if (!response || !response.result) {
				throw new Error('Invalid response format')
			}
			const devices: DeviceItem[] = response.result
			return this.getResponse(
				`Connected Devices:\n\n` +
					devices
						.slice(0, 10)
						.map((device, index) => `${index + 1}. Device ID: ${device.id}`)
						.join('\n') +
					(devices.length > 10 ? `\n... and ${devices.length - 10} more devices` : ''),
			)
		} catch (error) {
			return this.getResponse('❌ Failed to get devices', error)
		}
	}

	private async getSystemStatus() {
		try {
			const response = await this.request('/')
			if (!response || !response.result) {
				throw new Error('Invalid response format')
			}
			return this.getResponse(
				`Sofie System Status:\n\n` +
					`Version: ${response.result.version}\n` +
					`API Status: Online\n` +
					`Authentication: Working (IAP)\n`,
			)
		} catch (error) {
			return this.getResponse('❌ Failed to get system status', error)
		}
	}
}
