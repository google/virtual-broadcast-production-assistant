import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  Activity,
  Server,
  Database
} from "lucide-react";

// Mock system status data
const mockSystemStatus = {
  websocket: {
    status: "connected",
    url: "ws://localhost:8000",
    lastConnected: Date.now() - 30000,
    retries: 0,
    lastError: null
  },
  agents: [
    { name: "CUEZ Agent", status: "online", lastSeen: Date.now() - 10000, responseTime: 120 },
    { name: "Sofie Agent", status: "online", lastSeen: Date.now() - 5000, responseTime: 85 },
    { name: "Content Agent", status: "busy", lastSeen: Date.now() - 2000, responseTime: 200 },
    { name: "Graphics Agent", status: "offline", lastSeen: Date.now() - 300000, responseTime: null }
  ]
};

export default function Status() {
  const [systemStatus, setSystemStatus] = useState(mockSystemStatus);
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetryConnection = async () => {
    setIsRetrying(true);
    // Simulate retry attempt
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    setSystemStatus(prev => ({
      ...prev,
      websocket: {
        ...prev.websocket,
        retries: prev.websocket.retries + 1,
        lastConnected: Date.now()
      }
    }));
    setIsRetrying(false);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
      case 'online':
        return <CheckCircle className="w-4 h-4 text-[#14B8A6]" />;
      case 'busy':
        return <Clock className="w-4 h-4 text-[#FFC857]" />;
      case 'offline':
      case 'disconnected':
        return <WifiOff className="w-4 h-4 text-[#FF2D86]" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-[#A6A0AA]" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected':
      case 'online':
        return 'border-[#14B8A6]/30 text-[#14B8A6] bg-[#14B8A6]/10';
      case 'busy':
        return 'border-[#FFC857]/30 text-[#FFC857] bg-[#FFC857]/10';
      case 'offline':
      case 'disconnected':
        return 'border-[#FF2D86]/30 text-[#FF2D86] bg-[#FF2D86]/10';
      default:
        return 'border-white/30 text-[#A6A0AA] bg-white/5';
    }
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-[#0D0B12] p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#E6E1E5] mb-2">System Status</h1>
          <p className="text-[#A6A0AA]">Monitor connections, agents, and system health</p>
        </div>

        {/* Connection Status */}
        <div className="grid gap-6 mb-8">
          {/* WebSocket Status */}
          <div className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-6 border border-white/10">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-[#14B8A6]/20 rounded-lg">
                  <Wifi className="w-6 h-6 text-[#14B8A6]" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#E6E1E5]">WebSocket Connection</h3>
                  <p className="text-[#A6A0AA]">Real-time communication status</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <Badge variant="outline" className={getStatusColor(systemStatus.websocket.status)}>
                  {systemStatus.websocket.status}
                </Badge>
                <Button
                  variant="outline"
                  onClick={handleRetryConnection}
                  disabled={isRetrying}
                  className="gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
                  {isRetrying ? 'Retrying...' : 'Retry'}
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <Server className="w-4 h-4 text-[#A6A0AA]" />
                  <span className="text-sm font-medium text-[#E6E1E5]">Endpoint</span>
                </div>
                <p className="text-xs text-[#A6A0AA] font-mono">{systemStatus.websocket.url}</p>
              </div>
              
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-[#A6A0AA]" />
                  <span className="text-sm font-medium text-[#E6E1E5]">Retries</span>
                </div>
                <p className="text-xl font-bold text-[#E6E1E5]">{systemStatus.websocket.retries}</p>
              </div>
              
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-[#A6A0AA]" />
                  <span className="text-sm font-medium text-[#E6E1E5]">Last Connected</span>
                </div>
                <p className="text-xs text-[#A6A0AA]">
                  {new Date(systemStatus.websocket.lastConnected).toLocaleTimeString()}
                </p>
              </div>
            </div>

            {systemStatus.websocket.lastError && (
              <div className="mt-4 p-3 bg-[#FF2D86]/10 border border-[#FF2D86]/30 rounded-lg">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-[#FF2D86]" />
                  <span className="text-sm font-medium text-[#FF2D86]">Last Error</span>
                </div>
                <p className="text-xs text-[#FF2D86] mt-1 font-mono">{systemStatus.websocket.lastError}</p>
              </div>
            )}
          </div>
        </div>

        {/* Agents Health */}
        <div className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-6 border border-white/10">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-[#FFC857]/20 rounded-lg">
              <Database className="w-6 h-6 text-[#FFC857]" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#E6E1E5]">Agent Health</h3>
              <p className="text-[#A6A0AA]">Status of connected AI agents</p>
            </div>
          </div>

          <div className="grid gap-4">
            {systemStatus.agents.map((agent) => (
              <div key={agent.name} className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
                <div className="flex items-center gap-4">
                  {getStatusIcon(agent.status)}
                  <div>
                    <h4 className="font-semibold text-[#E6E1E5]">{agent.name}</h4>
                    <p className="text-xs text-[#A6A0AA]">
                      Last seen: {new Date(agent.lastSeen).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  {agent.responseTime && (
                    <div className="text-right">
                      <p className="text-sm font-medium text-[#E6E1E5]">{agent.responseTime}ms</p>
                      <p className="text-xs text-[#A6A0AA]">Response time</p>
                    </div>
                  )}
                  <Badge variant="outline" className={getStatusColor(agent.status)}>
                    {agent.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Info */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-4 border border-white/10">
            <h4 className="font-semibold text-[#E6E1E5] mb-2">Version</h4>
            <p className="text-[#A6A0AA]">v1.0.0-beta</p>
          </div>
          
          <div className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-4 border border-white/10">
            <h4 className="font-semibold text-[#E6E1E5] mb-2">Uptime</h4>
            <p className="text-[#A6A0AA]">2h 34m 12s</p>
          </div>
          
          <div className="bg-gradient-to-br from-[#1C1A22] to-[#2A2731] rounded-xl p-4 border border-white/10">
            <h4 className="font-semibold text-[#E6E1E5] mb-2">Environment</h4>
            <p className="text-[#A6A0AA]">Development</p>
          </div>
        </div>
      </div>
    </div>
  );
}