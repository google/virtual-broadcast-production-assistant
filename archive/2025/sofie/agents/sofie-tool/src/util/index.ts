import { Level, Logger } from 'pino'
import { inspect } from 'util'

/**
 * Type guard.
 *
 * @param {T} obj Object to check
 * @returns {T} Object.
 */
export function literal<T>(obj: T): T {
	return obj
}

/**
 * Log an error message with suitable debug.
 *
 * @param {Logger} log Log instance.
 * @param {Level} level Log level.
 * @param {string} msg Log message.
 * @param {unknown} error Error instance or unknown.
 */
export function logError(log: Logger, level: Level, msg: string, error: unknown) {
	if (error instanceof Error) {
		log[level](`${msg} - ${error.message}`)
	} else {
		log[level](msg)
	}
	log.debug(inspect(error))
}
