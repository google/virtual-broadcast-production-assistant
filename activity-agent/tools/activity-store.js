import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { v4 as uuidv4 } from 'uuid';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Shared activities file
const ACTIVITIES_FILE = path.join(__dirname, 'activities.json');

class SharedActivityStore {
  constructor() {
    this.ensureFile();
    this.wss = null; // Will be set by web server
    this.lastKnownActivityCount = 0;
    this.setupFileWatcher();
  }

  ensureFile() {
    if (!fs.existsSync(ACTIVITIES_FILE)) {
      fs.writeFileSync(ACTIVITIES_FILE, JSON.stringify([]));
    }
    // Initialize the count
    this.lastKnownActivityCount = this.readActivities().length;
  }

  setupFileWatcher() {
    // Use fs.watch for better real-time detection
    fs.watch(ACTIVITIES_FILE, (eventType, filename) => {
      if (eventType === 'change') {
        console.log('📁 Activities file changed, checking for new activities...');
        this.checkForNewActivities();
      }
    });
  }

  checkForNewActivities() {
    if (!this.wss) return;

    const activities = this.readActivities();
    const currentCount = activities.length;
    
    // If we have more activities than we knew about
    if (currentCount > this.lastKnownActivityCount) {
      const newActivitiesCount = currentCount - this.lastKnownActivityCount;
      console.log(`📈 Found ${newActivitiesCount} new activities, broadcasting...`);
      
      // Get the new activities (they're at the beginning since newest first)
      const newActivities = activities.slice(0, newActivitiesCount);
      
      // Broadcast each new activity
      newActivities.reverse().forEach(activity => { // Reverse to send in chronological order
        this.broadcastActivity(activity);
      });
      
      this.lastKnownActivityCount = currentCount;
    }
  }

  broadcastActivity(activity) {
    if (this.wss) {
      const message = JSON.stringify({
        type: 'new_activity',
        data: activity
      });

      this.wss.clients.forEach((client) => {
        if (client.readyState === 1) { // WebSocket.OPEN
          client.send(message);
        }
      });
      
      console.log(`📡 Broadcasted activity: ${activity.title} (${activity.type})`);
    }
  }

  setWebSocketServer(wss) {
    this.wss = wss;
    console.log('🔗 WebSocket server connected to activity store');
    // Update our count when WebSocket connects
    this.lastKnownActivityCount = this.readActivities().length;
  }

  readActivities() {
    try {
      const data = fs.readFileSync(ACTIVITIES_FILE, 'utf8');
      return JSON.parse(data);
    } catch (error) {
      console.error('Error reading activities:', error);
      return [];
    }
  }

  writeActivities(activities) {
    try {
      fs.writeFileSync(ACTIVITIES_FILE, JSON.stringify(activities, null, 2));
    } catch (error) {
      console.error('Error writing activities:', error);
    }
  }

  addActivity(data) {
    const activities = this.readActivities();
    
    const activity = {
      id: uuidv4(),
      type: data.type || 'system',
      title: data.title,
      message: data.message,
      metadata: data.metadata || {},
      priority: data.priority || 'normal',
      agent: data.agent || 'unknown',
      timestamp: new Date().toISOString(),
      createdAt: Date.now()
    };

    // Add to beginning of array (newest first)
    activities.unshift(activity);
    
    // Keep only last 1000 activities
    if (activities.length > 1000) {
      activities.splice(1000);
    }

    // Write back to file (this will trigger the file watcher)
    this.writeActivities(activities);

    console.log(`💾 Added activity: ${activity.title} (${activity.type})`);
    
    // If we added this activity directly (not via file watch), broadcast immediately
    if (this.wss) {
      // Small delay to ensure file write completes before file watcher triggers
      setTimeout(() => {
        this.lastKnownActivityCount = activities.length;
      }, 10);
    }
    
    return activity;
  }

  getActivities(limit = 50, type = null) {
    const activities = this.readActivities();
    
    let filtered = activities;
    if (type) {
      filtered = activities.filter(activity => activity.type === type);
    }
    
    return filtered.slice(0, limit);
  }

  clearActivities() {
    this.writeActivities([]);
    this.lastKnownActivityCount = 0;
    
    // Broadcast clear to all clients
    if (this.wss) {
      const message = JSON.stringify({
        type: 'activities_cleared'
      });

      this.wss.clients.forEach((client) => {
        if (client.readyState === 1) {
          client.send(message);
        }
      });
      
      console.log('🗑️ Activities cleared and broadcasted');
    }
  }
}

// Create singleton instance
export const sharedActivityStore = new SharedActivityStore();