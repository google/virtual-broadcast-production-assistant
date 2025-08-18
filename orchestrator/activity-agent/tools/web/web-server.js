#!/usr/bin/env node

import dotenv from 'dotenv';
import { WebSocketServer } from 'ws';
import express from 'express';
import cors from 'cors';

// Load environment variables
dotenv.config();

// Import shared activity store
import { sharedActivityStore } from "./shared/activity-store.js";

class WebServer {
  constructor() {
    this.setupWebServer();
  }

  setupWebServer() {
    // Express server for REST API
    this.app = express();
    this.app.use(cors());
    this.app.use(express.json());
    
    const PORT = process.env.WEB_PORT || 3002;
    
    // Serve static files from web directory
    this.app.use(express.static('web/dist'));
    
    // API routes
    this.app.get('/api/activities', (req, res) => {
      res.json(sharedActivityStore.getActivities());
    });
    
    this.app.post('/api/activities', (req, res) => {
      const activity = sharedActivityStore.addActivity(req.body);
      res.json(activity);
    });
    
    // Start HTTP server
    this.httpServer = this.app.listen(PORT, () => {
      console.log(`✅ Web server running on http://localhost:${PORT}`);
    });
    
    // WebSocket server
    this.wss = new WebSocketServer({ server: this.httpServer });
    
    this.wss.on('connection', (ws) => {
      console.log('🔌 New WebSocket connection');
      
      // Send recent activities to new connection
      const recentActivities = sharedActivityStore.getActivities(20);
      ws.send(JSON.stringify({
        type: 'initial_activities',
        data: recentActivities
      }));
      
      console.log(`📤 Sent ${recentActivities.length} initial activities to client`);
      
      ws.on('close', () => {
        console.log('❌ WebSocket connection closed');
      });
      
      ws.on('error', (error) => {
        console.error('🚨 WebSocket error:', error);
      });
    });
    
    // Pass WebSocket server to shared store for broadcasting
    sharedActivityStore.setWebSocketServer(this.wss);
    
    console.log(`🔗 WebSocket server ready with ${this.wss.clients.size} clients`);
    
    // Graceful shutdown
    process.on("SIGINT", () => {
      console.log('\n🛑 Shutting down web server...');
      this.httpServer.close();
      this.wss.close();
      process.exit(0);
    });
  }
}

// Start the web server
new WebServer();
console.log('🚀 Activity Feed Web Server starting...');