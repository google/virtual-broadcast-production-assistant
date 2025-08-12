import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { createWebSocketApi } from '@/api/webSocket';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { currentUser, getIdToken } = useAuth();
  const [ws, setWs] = useState(null);
  const [status, setStatus] = useState('disconnected');
  const [lastError, setLastError] = useState(null);
  const [retries, setRetries] = useState(0);

  const connect = useCallback(async () => {
    if (!ws) {
      console.log("WebSocketContext: ws not initialized, not connecting");
      return;
    }
    console.log("WebSocketContext: connecting...");
    setStatus('connecting');
    await ws.connect();
  }, [ws]);

  useEffect(() => {
    if (currentUser && !ws) {
      const uid = currentUser.uid;
      const callbacks = {
        onConnect: () => {
          setStatus('connected');
          setLastError(null);
          setRetries(0);
        },
        onDisconnect: () => {
          setStatus('disconnected');
        },
        onMessage: (message) => {
          console.log('WebSocket message received:', message);
        },
        onError: (error) => {
          console.error("WebSocketContext: connection error", error);
          setLastError(error.message || 'WebSocket error');
          setStatus('disconnected');
        }
      };
      const wsInstance = createWebSocketApi(callbacks, false, uid, getIdToken);
      setWs(wsInstance);
    } else if (!currentUser && ws) {
      ws.disconnect();
      setWs(null);
    }
  }, [currentUser, getIdToken, ws]);

  useEffect(() => {
    if (ws && status === 'disconnected' && currentUser) {
      const timer = setTimeout(() => {
        setRetries(r => r + 1);
        connect();
      }, 3000); // 3-second delay before reconnecting
      return () => clearTimeout(timer);
    }
  }, [ws, status, connect, currentUser]);

  const sendMessage = (message) => {
    if (ws) {
      ws.sendMessage(message);
    }
  };

  const value = {
    ws,
    status,
    lastError,
    retries,
    sendMessage,
    connect,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

WebSocketProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (context === null) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
