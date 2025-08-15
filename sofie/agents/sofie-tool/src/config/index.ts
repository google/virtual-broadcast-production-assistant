import * as dotenv from 'dotenv'
import pino from 'pino'
import { Config } from '../typings/config/index.js'
import { logger } from './log.js'

const logLevels: pino.LevelOrString[] = ['trace', 'debug', 'info', 'warn', 'error', 'fatal']

export const loadConfig = (): Config => {
	logger.info('Loading config...')
	dotenv.config({
		quiet: true,
	})

	const logLevelString = process.env.LOG_LEVEL ?? ''
	const logLevel: pino.LevelOrString = logLevels.includes(logLevelString) ? logLevelString : 'info'

	logger.info(`Setting log level to: ${logLevel}`)
	logger.level = logLevel

	const config: Config = {
		port: process.env.PORT ? parseInt(process.env.PORT) : undefined,
		logLevel,
		sofieApiBase: process.env.SOFIE_API_BASE?.trim() || 'https://ibc-sofie.justingrayston.com/api/v1.0',
		liveStatusEndpoint: process.env.SOFIE_LIVE_STATUS_WS || 'wss://sofie-live-status.justingrayston.com',
		iapClientId: process.env.IAP_CLIENT_ID?.trim(),
		serviceAccountPath: process.env.GOOGLE_APPLICATION_CREDENTIALS?.trim(),
	}

	logger.info('Config loaded')
	logger.debug(`Config: ${JSON.stringify(config)}`)

	return config
}
