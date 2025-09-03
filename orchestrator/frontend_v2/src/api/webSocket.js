let socket = null;

export const connectSocket = async (uid, getToken) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    return socket;
  }

  if (socket && socket.readyState === WebSocket.CONNECTING) {
    // Wait for the existing connection to open
    return new Promise((resolve, reject) => {
      const onOpen = () => {
        socket.removeEventListener('open', onOpen);
        socket.removeEventListener('close', onClose);
        resolve(socket);
      };
      const onClose = () => {
        socket.removeEventListener('open', onOpen);
        socket.removeEventListener('close', onClose);
        reject(new Error('WebSocket connection failed'));
      };
      socket.addEventListener('open', onOpen);
      socket.addEventListener('close', onClose);
    });
  }

  const final_ws_base_url = '__VITE_WEBSOCKET_URL__';
  const token = await getToken();
  const ws_url = `${final_ws_base_url}/ws/${uid}?is_audio=false`;

  socket = new WebSocket(ws_url, [token]);

  return new Promise((resolve, reject) => {
    const onOpen = () => {
      socket.removeEventListener('open', onOpen);
      socket.removeEventListener('close', onClose);
      resolve(socket);
    };
    const onClose = () => {
      socket.removeEventListener('open', onOpen);
      socket.removeEventListener('close', onClose);
      socket = null;
      reject(new Error('WebSocket connection failed'));
    };
    socket.addEventListener('open', onOpen);
    socket.addEventListener('close', onClose);
  });
};

export const sendMessage = (message) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
  } else {
    console.error("WebSocket is not connected.");
  }
};

export const disconnectSocket = () => {
  if (socket) {
    socket.close();
    socket = null;
  }
};