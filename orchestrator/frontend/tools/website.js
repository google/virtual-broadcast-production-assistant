import { sharedActivityStore } from '../shared/activity-store.js';

class WebsiteTools {
  constructor() {
    this.tools = [
      'post_activity',
      'get_activities',
      'clear_activities',
      'post_system_alert'
    ];
  }

  setWebSocketServer(wss) {
    sharedActivityStore.setWebSocketServer(wss);
  }

  getToolDefinitions() {
    return [
      {
        name: "post_activity",
        description: `Post a new activity to the broadcast feed.

WHEN TO USE:
- After completing any broadcast action (graphics updates, rundown changes, etc.)
- When system events occur that the team should know about
- To log important decisions or status changes

CONTEXT:
This creates a social media-style post in the broadcast activity feed that all team members can see in real-time. Think of it as a live log of everything happening in your broadcast operation.

BEST PRACTICES:
- Always post after completing graphics operations
- Include relevant metadata for debugging
- Use appropriate priority levels
- Be descriptive but concise in messages`,
        inputSchema: {
          type: "object",
          properties: {
            type: {
              type: "string",
              enum: ["graphics", "vision", "sofie", "system", "user"],
              description: "Type of activity"
            },
            title: {
              type: "string",
              description: "Short title for the activity"
            },
            message: {
              type: "string",
              description: "Detailed message or description"
            },
            metadata: {
              type: "object",
              description: "Additional data (screenshots, payloads, etc.)"
            },
            priority: {
              type: "string",
              enum: ["low", "normal", "high", "critical"],
              description: "Priority level (default: normal)"
            },
            agent: {
              type: "string",
              description: "Name of the agent or system posting this"
            }
          },
          required: ["type", "title", "message"]
        }
      },
      {
        name: "get_activities",
        description: "Get recent activities from the feed",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Maximum number of activities to return (default: 50)"
            },
            type: {
              type: "string",
              description: "Filter by activity type"
            }
          }
        }
      },
      {
        name: "clear_activities",
        description: "Clear all activities from the feed",
        inputSchema: {
          type: "object",
          properties: {
            confirm: {
              type: "boolean",
              description: "Must be true to confirm clearing"
            }
          },
          required: ["confirm"]
        }
      },
      {
        name: "post_system_alert",
        description: `Post a high-priority system alert to the broadcast feed.

WHEN TO USE:
- Critical system failures (camera down, audio issues, etc.)
- Breaking news that requires immediate attention
- Equipment malfunctions during live broadcast
- Any situation requiring immediate team notification

CONTEXT:
System alerts appear prominently in the activity feed with visual indicators (red borders, pulsing animations) to ensure they're noticed immediately by all team members.

EXAMPLES:
- Camera failures during live broadcast
- Audio feed interruptions  
- Graphics rendering errors
- Network connectivity issues`,
        inputSchema: {
          type: "object",
          properties: {
            title: {
              type: "string",
              description: "Alert title"
            },
            message: {
              type: "string", 
              description: "Alert message"
            },
            severity: {
              type: "string",
              enum: ["warning", "error", "critical"],
              description: "Alert severity"
            }
          },
          required: ["title", "message"]
        }
      }
    ];
  }

  hasTools(toolName) {
    return this.tools.includes(toolName);
  }

  async callTool(toolName, args) {
    switch (toolName) {
      case 'post_activity':
        return await this.postActivity(args);
      
      case 'get_activities':
        return await this.getActivitiesCommand(args.limit, args.type);
      
      case 'clear_activities':
        return await this.clearActivities(args.confirm);
      
      case 'post_system_alert':
        return await this.postSystemAlert(args);
      
      default:
        throw new Error(`Unknown website tool: ${toolName}`);
    }
  }

  async postActivity(args) {
    const activity = sharedActivityStore.addActivity(args);
    
    return {
      content: [
        {
          type: "text",
          text: `Activity posted successfully! ID: ${activity.id}\nTitle: ${activity.title}\nType: ${activity.type}`
        }
      ]
    };
  }

  addActivity(data) {
    return sharedActivityStore.addActivity(data);
  }

  getActivities(limit = 50, type = null) {
    return sharedActivityStore.getActivities(limit, type);
  }

  async getActivitiesCommand(limit = 50, type = null) {
    const activities = sharedActivityStore.getActivities(limit, type);
    
    return {
      content: [
        {
          type: "text",
          text: `Retrieved ${activities.length} activities${type ? ` of type '${type}'` : ''}\n\n` +
                activities.slice(0, 10).map(a => 
                  `[${a.type.toUpperCase()}] ${a.title}\n${a.message}\n${new Date(a.timestamp).toLocaleString()}\n`
                ).join('\n')
        }
      ]
    };
  }

  async clearActivities(confirm) {
    if (!confirm) {
      return {
        content: [
          {
            type: "text",
            text: "Please confirm clearing by setting confirm: true"
          }
        ]
      };
    }

    const activities = sharedActivityStore.getActivities();
    const count = activities.length;
    sharedActivityStore.clearActivities();

    return {
      content: [
        {
          type: "text",
          text: `Cleared ${count} activities from the feed`
        }
      ]
    };
  }

  async postSystemAlert(args) {
    const activity = sharedActivityStore.addActivity({
      type: 'system',
      title: `🚨 ${args.title}`,
      message: args.message,
      priority: args.severity === 'critical' ? 'critical' : 'high',
      agent: 'system',
      metadata: {
        severity: args.severity || 'warning',
        isAlert: true
      }
    });

    return {
      content: [
        {
          type: "text",
          text: `System alert posted: ${args.title}`
        }
      ]
    };
  }
}

export const websiteTools = new WebsiteTools();