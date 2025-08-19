import { createContext, useEffect, useState, useCallback } from "react";
import { connectSocket, disconnectSocket } from "@/api/webSocket";
import { useAuth } from "./useAuth";

export const SocketContext = createContext(null);



export const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const { currentUser } = useAuth();

  const reconnect = useCallback(async () => {
    disconnectSocket();
    if (currentUser) {
      setConnectionStatus("connecting");
      try {
        const socket_instance = await connectSocket(currentUser.uid, () => currentUser.getIdToken());
        setSocket(socket_instance);
      } catch (error) {
        console.error("Failed to reconnect WebSocket:", error);
        setConnectionStatus("disconnected");
      }
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      const establishConnection = async () => {
        setConnectionStatus("connecting");
        try {
          const socket_instance = await connectSocket(currentUser.uid, () => currentUser.getIdToken());
          setSocket(socket_instance);
        } catch (error) {
          console.error("Failed to connect WebSocket:", error);
          setConnectionStatus("disconnected");
        }
      };

      establishConnection();

      return () => {
        disconnectSocket();
        setSocket(null);
      };
    }
  }, [currentUser]);

  useEffect(() => {
    if (!socket) return;

    const onOpen = () => setConnectionStatus("connected");
    const onClose = () => setConnectionStatus("disconnected");
    const onError = () => setConnectionStatus("disconnected");

    socket.addEventListener('open', onOpen);
    socket.addEventListener('close', onClose);
    socket.addEventListener('error', onError);

    // Heartbeat to detect dead connections
    const heartbeatInterval = setInterval(() => {
      if (socket.readyState !== WebSocket.OPEN && socket.readyState !== WebSocket.CONNECTING) {
        setConnectionStatus("disconnected");
      }
    }, 5000);

    return () => {
      socket.removeEventListener('open', onOpen);
      socket.removeEventListener('close', onClose);
      socket.removeEventListener('error', onError);
      clearInterval(heartbeatInterval);
    };
  }, [socket]);

  // Auto-reconnect logic
  useEffect(() => {
    if (connectionStatus === "disconnected" && currentUser) {
      const timer = setTimeout(() => {
        reconnect();
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [connectionStatus, currentUser, reconnect]);


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
        socket.addEventListener(eventName, handler);
        return () => socket.removeEventListener(eventName, handler);
      }
    }
    return () => {};
  }, [socket]);

  const value = { socket, addEventListener, reconnect, connectionStatus };

  return (
    <SocketContext.Provider value={value}>{children}</SocketContext.Provider>
  );
};
