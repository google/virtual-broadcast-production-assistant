import pino from 'pino'

export interface Config {
	port?: number
	logLevel: pino.LevelOrString
	sofieApiBase: string
	liveStatusEndpoint: string
	iapClientId: string
	serviceAccountPath: string
}
