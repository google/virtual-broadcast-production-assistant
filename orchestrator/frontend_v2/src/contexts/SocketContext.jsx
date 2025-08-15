import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { connectSocket, disconnectSocket } from "@/api/webSocket";
import { useAuth } from "./AuthContext";

const SocketContext = createContext(null);

export const useSocket = () => useContext(SocketContext);

export const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const { currentUser } = useAuth();

  useEffect(() => {
    if (currentUser) {
      const establishConnection = async () => {
        try {
          const socket_instance = await connectSocket(currentUser.uid, () => currentUser.getIdToken());
          setSocket(socket_instance);
        } catch (error) {
          console.error("Failed to connect WebSocket:", error);
        }
      };

      establishConnection();

      return () => {
        disconnectSocket();
        setSocket(null);
      };
    }
  }, [currentUser]);

  const addEventListener = useCallback((eventName, handler) => {
    if (socket) {
      if (eventName === 'message') {
        const messageHandler = (event) => {
          try {
            const message = JSON.parse(event.data);
            handler(message);
          } catch (error) {
            console.error("Failed to parse WebSocket message:", error);
          }
        };
        socket.addEventListener('message', messageHandler);
        return () => socket.removeEventListener('message', messageHandler);
      } else {
        // For other events like 'open', 'close', 'error', just pass the event through
        socket.addEventListener(eventName, handler);
        return () => socket.removeEventListener(eventName, handler);
      }
    }
    return () => {};
  }, [socket]);

  const reconnect = useCallback(async () => {
    disconnectSocket();
    if (currentUser) {
      try {
        const socket_instance = await connectSocket(currentUser.uid, () => currentUser.getIdToken());
        setSocket(socket_instance);
      } catch (error) {
        console.error("Failed to reconnect WebSocket:", error);
      }
    }
  }, [currentUser]);


  const value = { socket, addEventListener, reconnect };

  return (
    <SocketContext.Provider value={value}>{children}</SocketContext.Provider>
  );
};
