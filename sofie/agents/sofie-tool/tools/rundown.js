import axios from 'axios';
import { GoogleAuth } from 'google-auth-library';

// Configuration from environment variables
const SOFIE_API_BASE = process.env.SOFIE_API_BASE || 'https://ibc-sofie.justingrayston.com/api/v1.0';
const IAP_CLIENT_ID = process.env.IAP_CLIENT_ID || '542328728538-okirhoruutf0bk3cci4190htqb06g6s1.apps.googleusercontent.com';
const SERVICE_ACCOUNT_PATH = process.env.GOOGLE_APPLICATION_CREDENTIALS || './ibc-agents.json';
const DEBUG = process.env.DEBUG === 'true';

// Initialize Google Auth for IAP
const auth = new GoogleAuth({
  keyFile: SERVICE_ACCOUNT_PATH
});

// Function to get fresh IAP token
async function getIAPToken() {
  try {
    const client = await auth.getClient();
    const idToken = await client.fetchIdToken(IAP_CLIENT_ID);
    return idToken;
  } catch (error) {
    if (DEBUG) console.error('Failed to get IAP token:', error);
    throw error;
  }
}

// Create axios instance with IAP authentication
async function createAuthenticatedClient() {
  const token = await getIAPToken();
  
  return axios.create({
    baseURL: SOFIE_API_BASE,
    timeout: 15000,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': 'Sofie-MCP-Client/1.0.0'
    }
  });
}

class RundownTools {
  constructor() {
    this.tools = [
      // Basic playlist operations
      'list_playlists',
      'get_playlist',
      'get_playlist_status',
      
      // Playlist lifecycle management
      'activate_playlist',
      'deactivate_playlist',
      'reload_playlist',
      'reset_playlist',
      
      // Playout control
      'take',
      'set_next_part',
      'set_next_segment',
      'move_next_part',
      'move_next_segment',
      'queue_next_segment',
      
      // AdLib operations
      'execute_adlib',
      'execute_bucket_adlib',
      
      // Source layer control
      'clear_source_layers',
      'clear_source_layer',
      'recall_sticky',
      
      // System information
      'get_studios',
      'get_showstyles',
      'get_devices',
      'get_system_status'
    ];
  }

  getToolDefinitions() {
    return [
      // Basic playlist operations
      {
        name: "list_playlists",
        description: "Returns all playlists available in Sofie",
        inputSchema: {
          type: "object",
          properties: {}
        }
      },
      {
        name: "get_playlist",
        description: "Get detailed information about a specific playlist by ID",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "The ID of the playlist to retrieve"
            }
          },
          required: ["playlistId"]
        }
      },
      {
        name: "get_playlist_status",
        description: "Get the current status of a playlist",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "The ID of the playlist to check status for"
            }
          },
          required: ["playlistId"]
        }
      },
      
      // Playlist lifecycle management
      {
        name: "activate_playlist",
        description: "Activates a playlist for playout",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to activate"
            },
            rehearsal: {
              type: "boolean",
              description: "Whether to activate into rehearsal mode",
              default: false
            }
          },
          required: ["playlistId"]
        }
      },
      {
        name: "deactivate_playlist",
        description: "Deactivates a playlist",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to deactivate"
            }
          },
          required: ["playlistId"]
        }
      },
      {
        name: "reload_playlist",
        description: "Reloads a playlist from its ingest source (e.g. MOS/Spreadsheet etc.)",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to reload"
            }
          },
          required: ["playlistId"]
        }
      },
      {
        name: "reset_playlist",
        description: "Resets a playlist back to its pre-played state",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to reset"
            }
          },
          required: ["playlistId"]
        }
      },
      
      // Playout control
      {
        name: "take",
        description: "Performs a take in the given playlist",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            fromPartInstanceId: {
              type: "string",
              description: "May be specified to ensure that multiple take requests from the same Part do not result in multiple takes"
            }
          },
          required: ["playlistId"]
        }
      },
      {
        name: "set_next_part",
        description: "Sets the next Part to a given PartId",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            partId: {
              type: "string",
              description: "Part to set as next"
            }
          },
          required: ["playlistId", "partId"]
        }
      },
      {
        name: "set_next_segment",
        description: "Sets the next part to the first playable Part of the Segment with given segmentId",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            segmentId: {
              type: "string",
              description: "Segment to set as next"
            }
          },
          required: ["playlistId", "segmentId"]
        }
      },
      {
        name: "move_next_part",
        description: "Moves the next point by delta places. Negative values move backwards",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to target"
            },
            delta: {
              type: "number",
              description: "Amount to move next point by (+/-)"
            }
          },
          required: ["playlistId", "delta"]
        }
      },
      {
        name: "move_next_segment",
        description: "Moves the next Segment point by delta places. Negative values move backwards",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to target"
            },
            delta: {
              type: "number",
              description: "Amount to move next Segment point by (+/-)"
            },
            ignoreQuickLoop: {
              type: "boolean",
              description: "When true, ignores any boundaries set by the QuickLoop feature"
            }
          },
          required: ["playlistId", "delta"]
        }
      },
      {
        name: "queue_next_segment",
        description: "Queue Segment so that Next point will jump to that Segment when reaching the end of current Segment",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            segmentId: {
              type: "string",
              description: "Segment to queue"
            }
          },
          required: ["playlistId", "segmentId"]
        }
      },
      
      // AdLib operations
      {
        name: "execute_adlib",
        description: "Executes the requested AdLib/AdLib Action",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to execute adLib in"
            },
            adLibId: {
              type: "string",
              description: "AdLib to execute"
            },
            actionType: {
              type: "string",
              description: "An actionType string to specify a particular variation for the AdLibAction"
            },
            adLibOptions: {
              type: "object",
              description: "AdLibAction options object defined according to the optionsSchema"
            }
          },
          required: ["playlistId", "adLibId"]
        }
      },
      {
        name: "execute_bucket_adlib",
        description: "Executes the requested Bucket AdLib/AdLib Action",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Playlist to execute the Bucket AdLib in"
            },
            bucketId: {
              type: "string",
              description: "Bucket to execute the adlib from"
            },
            externalId: {
              type: "string",
              description: "External Id of the Bucket AdLib to execute"
            },
            actionType: {
              type: "string",
              description: "An actionType string to specify a particular variation"
            }
          },
          required: ["playlistId", "bucketId", "externalId"]
        }
      },
      
      // Source layer control
      {
        name: "clear_source_layers",
        description: "Clears the target SourceLayers",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            sourceLayerIds: {
              type: "array",
              items: {
                type: "string"
              },
              description: "Target SourceLayers"
            }
          },
          required: ["playlistId", "sourceLayerIds"]
        }
      },
      {
        name: "clear_source_layer",
        description: "Clears the target SourceLayer (deprecated - use clear_source_layers)",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            sourceLayerId: {
              type: "string",
              description: "Target SourceLayer"
            }
          },
          required: ["playlistId", "sourceLayerId"]
        }
      },
      {
        name: "recall_sticky",
        description: "Recalls the last sticky Piece on the specified SourceLayer",
        inputSchema: {
          type: "object",
          properties: {
            playlistId: {
              type: "string",
              description: "Target playlist"
            },
            sourceLayerId: {
              type: "string",
              description: "Target sourcelayer"
            }
          },
          required: ["playlistId", "sourceLayerId"]
        }
      },
      
      // System information
      {
        name: "get_studios",
        description: "Get all available studios",
        inputSchema: {
          type: "object",
          properties: {}
        }
      },
      {
        name: "get_showstyles",
        description: "Get all available show styles",
        inputSchema: {
          type: "object",
          properties: {}
        }
      },
      {
        name: "get_devices",
        description: "Get all connected devices and gateways",
        inputSchema: {
          type: "object",
          properties: {}
        }
      },
      {
        name: "get_system_status",
        description: "Get overall system health and status",
        inputSchema: {
          type: "object",
          properties: {}
        }
      }
    ];
  }

  hasTools(toolName) {
    return this.tools.includes(toolName);
  }

  async callTool(toolName, args) {
    try {
      switch (toolName) {
        // Basic playlist operations
        case 'list_playlists':
          return await this.listPlaylists();
        case 'get_playlist':
          return await this.getPlaylist(args.playlistId);
        case 'get_playlist_status':
          return await this.getPlaylistStatus(args.playlistId);
        
        // Playlist lifecycle management
        case 'activate_playlist':
          return await this.activatePlaylist(args.playlistId, args.rehearsal);
        case 'deactivate_playlist':
          return await this.deactivatePlaylist(args.playlistId);
        case 'reload_playlist':
          return await this.reloadPlaylist(args.playlistId);
        case 'reset_playlist':
          return await this.resetPlaylist(args.playlistId);
        
        // Playout control
        case 'take':
          return await this.take(args.playlistId, args.fromPartInstanceId);
        case 'set_next_part':
          return await this.setNextPart(args.playlistId, args.partId);
        case 'set_next_segment':
          return await this.setNextSegment(args.playlistId, args.segmentId);
        case 'move_next_part':
          return await this.moveNextPart(args.playlistId, args.delta);
        case 'move_next_segment':
          return await this.moveNextSegment(args.playlistId, args.delta, args.ignoreQuickLoop);
        case 'queue_next_segment':
          return await this.queueNextSegment(args.playlistId, args.segmentId);
        
        // AdLib operations
        case 'execute_adlib':
          return await this.executeAdLib(args.playlistId, args.adLibId, args.actionType, args.adLibOptions);
        case 'execute_bucket_adlib':
          return await this.executeBucketAdLib(args.playlistId, args.bucketId, args.externalId, args.actionType);
        
        // Source layer control
        case 'clear_source_layers':
          return await this.clearSourceLayers(args.playlistId, args.sourceLayerIds);
        case 'clear_source_layer':
          return await this.clearSourceLayer(args.playlistId, args.sourceLayerId);
        case 'recall_sticky':
          return await this.recallSticky(args.playlistId, args.sourceLayerId);
        
        // System information
        case 'get_studios':
          return await this.getStudios();
        case 'get_showstyles':
          return await this.getShowStyles();
        case 'get_devices':
          return await this.getDevices();
        case 'get_system_status':
          return await this.getSystemStatus();
        
        default:
          throw new Error(`Unknown tool: ${toolName}`);
      }
    } catch (error) {
      if (DEBUG) console.error(`Error in ${toolName}:`, error);
      throw error;
    }
  }

  // Basic playlist operations
  async listPlaylists() {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get('/playlists');

      if (!response.data || !response.data.result) {
        throw new Error('Invalid response format');
      }

      const playlists = response.data.result;

      return {
        content: [
          {
            type: "text",
            text: `Found ${playlists.length} playlist(s):\n\n` +
                  playlists.map((playlist, index) => 
                    `${index + 1}. Playlist ID: ${playlist.id}`
                  ).join('\n')
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to list playlists: ${error.message}`
          }
        ]
      };
    }
  }

  async getPlaylist(playlistId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get(`/playlists/${playlistId}`);

      return {
        content: [
          {
            type: "text",
            text: `Playlist Details:\n\n${JSON.stringify(response.data, null, 2)}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to get playlist ${playlistId}: ${error.message}`
          }
        ]
      };
    }
  }

  async getPlaylistStatus(playlistId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get(`/playlists/${playlistId}/status`);

      return {
        content: [
          {
            type: "text",
            text: `Playlist Status:\n\n${JSON.stringify(response.data, null, 2)}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to get playlist status: ${error.message}`
          }
        ]
      };
    }
  }

  // Playlist lifecycle management
  async activatePlaylist(playlistId, rehearsal = false) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.put(`/playlists/${playlistId}/activate`, {
        rehearsal
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Playlist ${playlistId} activated successfully!\nMode: ${rehearsal ? 'Rehearsal' : 'Live'}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to activate playlist ${playlistId}: ${error.message}`
          }
        ]
      };
    }
  }

  async deactivatePlaylist(playlistId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.put(`/playlists/${playlistId}/deactivate`);

      return {
        content: [
          {
            type: "text",
            text: `✅ Playlist ${playlistId} deactivated successfully!`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to deactivate playlist ${playlistId}: ${error.message}`
          }
        ]
      };
    }
  }

  async reloadPlaylist(playlistId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.put(`/playlists/${playlistId}/reload`);

      return {
        content: [
          {
            type: "text",
            text: `✅ Playlist ${playlistId} reloaded successfully!`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to reload playlist ${playlistId}: ${error.message}`
          }
        ]
      };
    }
  }

  async resetPlaylist(playlistId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.put(`/playlists/${playlistId}/reset`);

      return {
        content: [
          {
            type: "text",
            text: `✅ Playlist ${playlistId} reset successfully!`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to reset playlist ${playlistId}: ${error.message}`
          }
        ]
      };
    }
  }

  // Playout control
  async take(playlistId, fromPartInstanceId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const requestBody = fromPartInstanceId ? { fromPartInstanceId } : {};
      const response = await apiClient.post(`/playlists/${playlistId}/take`, requestBody);

      return {
        content: [
          {
            type: "text",
            text: `✅ Take executed successfully for playlist ${playlistId}!`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to take: ${error.message}`
          }
        ]
      };
    }
  }

  async setNextPart(playlistId, partId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.put(`/playlists/${playlistId}/set-next-part`, {
        partId
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Next part set to ${partId} for playlist ${playlistId}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to set next part: ${error.message}`
          }
        ]
      };
    }
  }

  async setNextSegment(playlistId, segmentId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.post(`/playlists/${playlistId}/set-next-segment`, {
        segmentId
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Next segment set to ${segmentId}. Result: ${JSON.stringify(response.data.result)}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to set next segment: ${error.message}`
          }
        ]
      };
    }
  }

  async moveNextPart(playlistId, delta) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.post(`/playlists/${playlistId}/move-next-part`, {
        delta
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Next part moved by ${delta}. New part: ${response.data.result}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to move next part: ${error.message}`
          }
        ]
      };
    }
  }

  async moveNextSegment(playlistId, delta, ignoreQuickLoop) {
    try {
      const apiClient = await createAuthenticatedClient();
      const requestBody = { delta };
      if (ignoreQuickLoop !== undefined) {
        requestBody.ignoreQuickLoop = ignoreQuickLoop;
      }
      const response = await apiClient.post(`/playlists/${playlistId}/move-next-segment`, requestBody);

      return {
        content: [
          {
            type: "text",
            text: `✅ Next segment moved by ${delta}. New part: ${response.data.result}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to move next segment: ${error.message}`
          }
        ]
      };
    }
  }

  async queueNextSegment(playlistId, segmentId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.post(`/playlists/${playlistId}/queue-next-segment`, {
        segmentId
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Segment queued. Result: ${JSON.stringify(response.data.result)}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to queue segment: ${error.message}`
          }
        ]
      };
    }
  }

  // AdLib operations
  async executeAdLib(playlistId, adLibId, actionType, adLibOptions) {
    try {
      const apiClient = await createAuthenticatedClient();
      const requestBody = { adLibId };
      if (actionType) requestBody.actionType = actionType;
      if (adLibOptions) requestBody.adLibOptions = adLibOptions;
      
      const response = await apiClient.post(`/playlists/${playlistId}/execute-adlib`, requestBody);

      return {
        content: [
          {
            type: "text",
            text: `✅ AdLib executed. Result: ${JSON.stringify(response.data.result)}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to execute AdLib: ${error.message}`
          }
        ]
      };
    }
  }

  async executeBucketAdLib(playlistId, bucketId, externalId, actionType) {
    try {
      const apiClient = await createAuthenticatedClient();
      const requestBody = { bucketId, externalId };
      if (actionType) requestBody.actionType = actionType;
      
      const response = await apiClient.post(`/playlists/${playlistId}/execute-bucket-adlib`, requestBody);

      return {
        content: [
          {
            type: "text",
            text: `✅ Bucket AdLib executed. Result: ${JSON.stringify(response.data.result)}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to execute bucket AdLib: ${error.message}`
          }
        ]
      };
    }
  }

  // Source layer control
  async clearSourceLayers(playlistId, sourceLayerIds) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.put(`/playlists/${playlistId}/clear-sourcelayers`, {
        sourceLayerIds
      });

      return {
        content: [
          {
            type: "text",
            text: `✅ Source layers cleared: ${sourceLayerIds.join(', ')}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to clear source layers: ${error.message}`
          }
        ]
      };
    }
  }

  async clearSourceLayer(playlistId, sourceLayerId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.delete(`/playlists/${playlistId}/sourcelayer/${sourceLayerId}`);

      return {
        content: [
          {
            type: "text",
            text: `✅ Source layer ${sourceLayerId} cleared (deprecated endpoint)`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to clear source layer: ${error.message}`
          }
        ]
      };
    }
  }

  async recallSticky(playlistId, sourceLayerId) {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.post(`/playlists/${playlistId}/sourcelayer/${sourceLayerId}/sticky`);

      return {
        content: [
          {
            type: "text",
            text: `✅ Sticky piece recalled for source layer ${sourceLayerId}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to recall sticky: ${error.message}`
          }
        ]
      };
    }
  }

  // System information (unchanged)
  async getStudios() {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get('/studios');

      if (!response.data || !response.data.result) {
        throw new Error('Invalid response format');
      }

      const studios = response.data.result;

      return {
        content: [
          {
            type: "text",
            text: `Available Studios:\n\n` +
                  studios.map((studio, index) => 
                    `${index + 1}. Studio ID: ${studio.id}`
                  ).join('\n')
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to get studios: ${error.message}`
          }
        ]
      };
    }
  }

  async getShowStyles() {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get('/showstyles');

      if (!response.data || !response.data.result) {
        throw new Error('Invalid response format');
      }

      const showStyles = response.data.result;

      return {
        content: [
          {
            type: "text",
            text: `Available Show Styles:\n\n` +
                  showStyles.map((style, index) => 
                    `${index + 1}. Show Style ID: ${style.id}`
                  ).join('\n')
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to get show styles: ${error.message}`
          }
        ]
      };
    }
  }

  async getDevices() {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get('/devices');

      if (!response.data || !response.data.result) {
        throw new Error('Invalid response format');
      }

      const devices = response.data.result;

      return {
        content: [
          {
            type: "text",
            text: `Connected Devices:\n\n` +
                  devices.slice(0, 10).map((device, index) => 
                    `${index + 1}. Device ID: ${device.id}`
                  ).join('\n') +
                  (devices.length > 10 ? `\n... and ${devices.length - 10} more devices` : '')
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to get devices: ${error.message}`
          }
        ]
      };
    }
  }

  async getSystemStatus() {
    try {
      const apiClient = await createAuthenticatedClient();
      const response = await apiClient.get('/');

      if (!response.data || !response.data.result) {
        throw new Error('Invalid response format');
      }

      return {
        content: [
          {
            type: "text",
            text: `Sofie System Status:\n\n` +
                  `Version: ${response.data.result.version}\n` +
                  `API Status: Online\n` +
                  `Authentication: Working (IAP)\n`
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `❌ Failed to get system status: ${error.message}`
          }
        ]
      };
    }
  }
}

export const rundownTools = new RundownTools();