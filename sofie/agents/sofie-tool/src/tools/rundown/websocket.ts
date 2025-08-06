import {
	ActivePiecesEvent,
	ActivePlaylistEvent,
	AdLibsEvent,
	BucketsEvent,
	PackagesEvent,
	SegmentsEvent,
	Slash,
	SubscriptionName,
} from '@sofie-automation/live-status-gateway-api'
import EventEmitter from 'events'
import { GoogleAuth } from 'google-auth-library'
import { EnvHttpProxyAgent, ErrorEvent, WebSocket } from 'undici'
import { logger } from '../../config/log.js'
import { version } from '../../config/version.js'
import { Config } from '../../typings/config/index.js'
import { logError } from '../../util/index.js'

export class SofieWebsocket extends EventEmitter {
	private readonly auth: GoogleAuth

	private readonly dispatcher = new EnvHttpProxyAgent()

	private readonly config: Config

	private ws?: WebSocket

	private activePlaylist?: ActivePlaylistEvent

	private activePieces?: ActivePiecesEvent

	private adLibs?: AdLibsEvent

	private buckets?: BucketsEvent

	private packages?: PackagesEvent

	private segments?: SegmentsEvent

	get ActivePlaylist(): string {
		if (this.activePlaylist) {
			return `The active playlist ID is: ${this.activePlaylist.id}\n
			Name: ${this.activePlaylist.name}\n
			Current Part: ${this.activePlaylist.currentPart?.name}\n
			Next Part: ${this.activePlaylist.currentPart?.name}`
		}
		return 'There is no active playlist'
	}

	get ActivePieces(): string {
		if (this.activePieces) {
			return `The Active Pieces are:\n
			${this.activePieces.activePieces.map((v) => JSON.stringify(v) + '\n')}`
		}
		return 'There are no Active Pieces'
	}

	get AdLibs(): string {
		if (this.adLibs) {
			return `The AdLibs are:\n
			Global: ${this.adLibs.globalAdLibs.map((v) => JSON.stringify(v) + '\n')}\n
			Part Specific: ${this.adLibs.adLibs.map((v) => JSON.stringify(v) + '\n')}`
		}
		return 'There are no AdLibs'
	}

	get Buckets(): string {
		if (this.buckets) {
			return `The Buckets are:\n
			${this.buckets.buckets.map((v) => JSON.stringify(v) + '\n')}`
		}
		return 'There are no buckets'
	}

	get Packages(): string {
		if (this.packages) {
			return `The Packages are:\n
			${this.packages.packages.map((v) => JSON.stringify(v) + '\n')}`
		}
		return 'There are no packages'
	}

	get Segments(): string {
		if (this.segments) {
			return `The Segments are:\n
			${this.segments.segments.map((v) => JSON.stringify(v) + '\n')}`
		}
		return 'There are no segments'
	}

	constructor(config: Config) {
		super()
		this.config = config
		this.auth = new GoogleAuth({
			keyFile: this.config.serviceAccountPath,
		})
		this.onClose = this.onClose.bind(this)
		this.onError = this.onError.bind(this)
		this.onOpen = this.onOpen.bind(this)
		this.onMessage = this.onMessage.bind(this)
	}

	async open() {
		if (this.ws) {
			return
		}
		logger.info(`Connecting to Live Status Gateway - Endpoint: ${this.config.liveStatusEndpoint}`)
		const token = await this.getToken()
		this.ws = new WebSocket(this.config.liveStatusEndpoint, {
			dispatcher: this.dispatcher,
			headers: {
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json',
				Accept: 'application/json',
				'User-Agent': `Sofie-MCP-Client/${version}`,
			},
		})
		this.ws.addEventListener('close', this.onClose)
		this.ws.addEventListener('error', this.onError)
		this.ws.addEventListener('message', this.onMessage)
		this.ws.addEventListener('open', this.onOpen)
	}

	close() {
		if (!this.ws) {
			return
		}
		this.ws.close()
		this.ws = undefined
	}

	private async getToken() {
		const client = await this.auth.getIdTokenClient(this.config.iapClientId)
		return await client.idTokenProvider.fetchIdToken(this.config.iapClientId)
	}

	private onOpen() {
		logger.info('Connected to Live Status Gateway')
		// Subscribe to all events.
		Object.values(SubscriptionName).forEach((val, i) => {
			this.ws?.send(JSON.stringify({ event: 'subscribe', subscription: { name: val }, reqid: i + 1 }))
		})
	}

	private onError(err: ErrorEvent) {
		logError(logger, 'error', 'Live Status Gateway Error', err.error)
	}

	// eslint-disable-next-line n/no-unsupported-features/node-builtins
	private onClose(ev: CloseEvent) {
		logger.error(`Disconnected from Live Status Gateway - Code: ${ev.code} - Reason: ${ev.reason}`)
		this.ws?.removeEventListener('close', this.onClose)
		this.ws?.removeEventListener('error', this.onError)
		this.ws?.removeEventListener('message', this.onMessage)
		this.ws?.removeEventListener('open', this.onOpen)
		this.ws = undefined
		void this.open()
	}

	private async onMessage(ev: MessageEvent) {
		const msg = ev.data
		logger.debug(`Live Status Gateway message: ${msg}`)
		if (typeof ev.data !== 'string') {
			return
		}
		let result: Slash
		try {
			result = JSON.parse(ev.data)
		} catch (e) {
			logError(logger, 'error', 'Error parsing Live Status Gateway message', e)
			return
		}
		switch (result.event) {
			case 'activePieces':
				this.activePieces = result
				break

			case 'activePlaylist':
				this.activePlaylist = result
				break

			case 'adLibs':
				this.adLibs = result
				break

			case 'buckets':
				this.buckets = result
				break

			case 'packages':
				this.packages = result
				break

			case 'segments':
				this.segments = result
				break
		}
	}
}
