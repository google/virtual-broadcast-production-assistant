import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { initApi } from '@/api/webSocket';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { currentUser, getIdToken } = useAuth();
  const [ws, setWs] = useState(null);
  const [status, setStatus] = useState('disconnected');
  const [lastError, setLastError] = useState(null);
  const [retries, setRetries] = useState(0);

  const connect = useCallback(async () => {
    if (!currentUser) {
      console.log("WebSocketContext: no current user, not connecting");
      return;
    }
    console.log("WebSocketContext: connecting...");
    setStatus('connecting');
    const uid = currentUser.uid;

    const callbacks = {
      onConnect: () => {
        setStatus('connected');
        setLastError(null);
        setRetries(0);
      },
      onDisconnect: () => {
        setStatus('disconnected');
        // Optional: implement retry logic here
      },
      onMessage: (message) => {
        // Handle incoming messages
        console.log('WebSocket message received:', message);
      },
      onError: (error) => {
        console.error("WebSocketContext: connection error", error);
        setLastError(error.message || 'WebSocket error');
        setStatus('disconnected');
      }
    };

    const wsInstance = initApi(callbacks, false, uid, getIdToken);
    setWs(wsInstance);

  }, [currentUser, getIdToken]);

  useEffect(() => {
    if (currentUser && status === 'disconnected') {
      const timer = setTimeout(() => {
        setRetries(r => r + 1);
        connect();
      }, 3000); // 3-second delay before reconnecting
      return () => clearTimeout(timer);
    }
  }, [currentUser, status, connect]);

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
