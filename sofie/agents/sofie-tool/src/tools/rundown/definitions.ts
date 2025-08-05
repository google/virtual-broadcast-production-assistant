import { ListToolsResultSchema } from '@modelcontextprotocol/sdk/types.js'

type Tools = (typeof ListToolsResultSchema)['_output']['tools']

export const toolDefinitions: Tools = [
	// Basic playlist operations
	{
		name: 'list_playlists',
		description: 'Returns all playlists available in Sofie',
		inputSchema: {
			type: 'object',
			properties: {},
		},
	},
	{
		name: 'get_playlist',
		description: 'Get detailed information about a specific playlist by ID',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'The ID of the playlist to retrieve',
				},
			},
			required: ['playlistId'],
		},
	},
	{
		name: 'get_playlist_status',
		description: 'Get the current status of a playlist',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'The ID of the playlist to check status for',
				},
			},
			required: ['playlistId'],
		},
	},

	// Playlist lifecycle management
	{
		name: 'activate_playlist',
		description: 'Activates a playlist for playout',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to activate',
				},
				rehearsal: {
					type: 'boolean',
					description: 'Whether to activate into rehearsal mode',
					default: false,
				},
			},
			required: ['playlistId'],
		},
	},
	{
		name: 'deactivate_playlist',
		description: 'Deactivates a playlist',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to deactivate',
				},
			},
			required: ['playlistId'],
		},
	},
	{
		name: 'reload_playlist',
		description: 'Reloads a playlist from its ingest source (e.g. MOS/Spreadsheet etc.)',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to reload',
				},
			},
			required: ['playlistId'],
		},
	},
	{
		name: 'reset_playlist',
		description: 'Resets a playlist back to its pre-played state',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to reset',
				},
			},
			required: ['playlistId'],
		},
	},

	// Playout control
	{
		name: 'take',
		description: 'Performs a take in the given playlist',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				fromPartInstanceId: {
					type: 'string',
					description:
						'May be specified to ensure that multiple take requests from the same Part do not result in multiple takes',
				},
			},
			required: ['playlistId'],
		},
	},
	{
		name: 'set_next_part',
		description: 'Sets the next Part to a given PartId',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				partId: {
					type: 'string',
					description: 'Part to set as next',
				},
			},
			required: ['playlistId', 'partId'],
		},
	},
	{
		name: 'set_next_segment',
		description: 'Sets the next part to the first playable Part of the Segment with given segmentId',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				segmentId: {
					type: 'string',
					description: 'Segment to set as next',
				},
			},
			required: ['playlistId', 'segmentId'],
		},
	},
	{
		name: 'move_next_part',
		description: 'Moves the next point by delta places. Negative values move backwards',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to target',
				},
				delta: {
					type: 'number',
					description: 'Amount to move next point by (+/-)',
				},
			},
			required: ['playlistId', 'delta'],
		},
	},
	{
		name: 'move_next_segment',
		description: 'Moves the next Segment point by delta places. Negative values move backwards',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to target',
				},
				delta: {
					type: 'number',
					description: 'Amount to move next Segment point by (+/-)',
				},
				ignoreQuickLoop: {
					type: 'boolean',
					description: 'When true, ignores any boundaries set by the QuickLoop feature',
				},
			},
			required: ['playlistId', 'delta'],
		},
	},
	{
		name: 'queue_next_segment',
		description: 'Queue Segment so that Next point will jump to that Segment when reaching the end of current Segment',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				segmentId: {
					type: 'string',
					description: 'Segment to queue',
				},
			},
			required: ['playlistId', 'segmentId'],
		},
	},

	// AdLib operations
	{
		name: 'execute_adlib',
		description: 'Executes the requested AdLib/AdLib Action',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to execute adLib in',
				},
				adLibId: {
					type: 'string',
					description: 'AdLib to execute',
				},
				actionType: {
					type: 'string',
					description: 'An actionType string to specify a particular variation for the AdLibAction',
				},
				adLibOptions: {
					type: 'object',
					description: 'AdLibAction options object defined according to the optionsSchema',
				},
			},
			required: ['playlistId', 'adLibId'],
		},
	},
	{
		name: 'execute_bucket_adlib',
		description: 'Executes the requested Bucket AdLib/AdLib Action',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Playlist to execute the Bucket AdLib in',
				},
				bucketId: {
					type: 'string',
					description: 'Bucket to execute the adlib from',
				},
				externalId: {
					type: 'string',
					description: 'External Id of the Bucket AdLib to execute',
				},
				actionType: {
					type: 'string',
					description: 'An actionType string to specify a particular variation',
				},
			},
			required: ['playlistId', 'bucketId', 'externalId'],
		},
	},

	// Source layer control
	{
		name: 'clear_source_layers',
		description: 'Clears the target SourceLayers',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				sourceLayerIds: {
					type: 'array',
					items: {
						type: 'string',
					},
					description: 'Target SourceLayers',
				},
			},
			required: ['playlistId', 'sourceLayerIds'],
		},
	},
	{
		name: 'clear_source_layer',
		description: 'Clears the target SourceLayer (deprecated - use clear_source_layers)',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				sourceLayerId: {
					type: 'string',
					description: 'Target SourceLayer',
				},
			},
			required: ['playlistId', 'sourceLayerId'],
		},
	},
	{
		name: 'recall_sticky',
		description: 'Recalls the last sticky Piece on the specified SourceLayer',
		inputSchema: {
			type: 'object',
			properties: {
				playlistId: {
					type: 'string',
					description: 'Target playlist',
				},
				sourceLayerId: {
					type: 'string',
					description: 'Target sourcelayer',
				},
			},
			required: ['playlistId', 'sourceLayerId'],
		},
	},

	// System information
	{
		name: 'get_studios',
		description: 'Get all available studios',
		inputSchema: {
			type: 'object',
			properties: {},
		},
	},
	{
		name: 'get_showstyles',
		description: 'Get all available show styles',
		inputSchema: {
			type: 'object',
			properties: {},
		},
	},
	{
		name: 'get_devices',
		description: 'Get all connected devices and gateways',
		inputSchema: {
			type: 'object',
			properties: {},
		},
	},
	{
		name: 'get_system_status',
		description: 'Get overall system health and status',
		inputSchema: {
			type: 'object',
			properties: {},
		},
	},
]
