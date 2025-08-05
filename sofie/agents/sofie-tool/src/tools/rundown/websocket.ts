import { GoogleAuth } from 'google-auth-library'
import { EnvHttpProxyAgent, ErrorEvent, WebSocket } from 'undici'
import { version } from '../../config/version.js'
import { Config } from '../../typings/config/index.js'
import { logger } from '../../config/log.js'
import { logError } from '../../util/index.js'

export class SofieWebsocket {
	private readonly auth: GoogleAuth

	private readonly dispatcher = new EnvHttpProxyAgent()

	private readonly config: Config

	private ws?: WebSocket

	constructor(config: Config) {
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
    }

    private onError(err: ErrorEvent) {
        logError(logger, 'error', 'Live Status Gateway Error', err.error)
    }

    private onClose(ev: CloseEvent) {
        logger.error(`Disconnected from Live Status Gateway - Code: ${ev.code} - Reason: ${ev.reason}`)
        this.ws?.removeEventListener('close', this.onClose)
        this.ws?.removeEventListener('error', this.onError)
        this.ws?.removeEventListener('message', this.onMessage)
        this.ws?.removeEventListener('open', this.onOpen)
        this.ws = undefined
        this.open()
    }   

    private onMessage(ev: MessageEvent) {
        const msg = ev.data
        logger.debug(`Live Status Gateway message: ${msg}`)
    }
}
