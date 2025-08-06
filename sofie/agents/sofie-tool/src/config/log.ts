import pino from 'pino'

const production = process.env.NODE_ENV?.toUpperCase() === 'PRODUCTION' ? true : false

export const logger = pino.default({
	level: 'info',
	transport: {
		target: 'pino-pretty',
		options: {
			colorize: !production,
			colorizeObjects: !production,
			ignore: 'pid,hostname',
			singleLine: true,
			sync: true,
		},
	},
})
