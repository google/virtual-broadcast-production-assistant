import { join } from 'path'
import pino from 'pino'

export const logger = pino.default({
	level: 'info',
	transport: {
		target: 'pino-pretty',
		options: {
			append: false,
			colorize: false,
			colorizeObjects: false,
			destination: join(import.meta.dirname, '../', '../', 'log', 'sofie-tool.log'),
			ignore: 'pid,hostname',
			mkdir: true,
			singleLine: true,
			sync: true,
		},
	},
})
