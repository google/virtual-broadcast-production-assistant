import { loadConfig } from './config/index.js'
import { logger } from './config/log.js'
import { version } from './config/version.js'
import { SofieMCPServer } from './server/index.js'
import { Config } from './typings/config/index.js'
import { logError } from './util/index.js'

let server: SofieMCPServer | undefined

logger.info('Sofie MCP Tool starting...')
logger.info(`Version: ${version}`)

void start()

async function start() {
	let config: Config
	try {
		config = loadConfig()
	} catch (e) {
		logError(logger, 'fatal', 'Config error', e)
		await shutdown(1)
		return
	}

	// Start the server
	server = new SofieMCPServer(config)
	try {
		await server.open()
	} catch (e) {
		logError(logger, 'error', 'Failed to run server', e)
		await shutdown(1)
		return
	}
}

async function shutdown(exitCode?: number) {
	if (server) {
		try {
			await server.close()
		} catch (e) {
			logError(logger, 'error', 'Error stopping server', e)
		}
	}
	logger.flush((err) => {
		if (err) {
			console.error('Error stopping logger', err)
		}
		// eslint-disable-next-line n/no-process-exit
		process.exit(exitCode)
	})
}
