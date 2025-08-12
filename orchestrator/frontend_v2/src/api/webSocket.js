let websocket;

export function initApi(callbacks, is_audio, uid, getToken) {
  // Vite replaces `import.meta.env.VITE_...` with the value at build time.
  // It falls back to localhost for local development if the variable is not set.
  const final_ws_base_url = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8080';
  console.log('initAPI called with final_ws_base_url', final_ws_base_url);
  async function connect() {
    console.log(`Connecting to ${final_ws_base_url}`);
    const token = await getToken();
    const ws_url = `${final_ws_base_url}/ws/${uid}?is_audio=${is_audio}&token=${token}`;

    websocket = new WebSocket(ws_url);

    websocket.onopen = () => {
      if (callbacks.onConnect) {
        callbacks.onConnect();
      }
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (callbacks.onMessage) {
        callbacks.onMessage(message);
      }
    };

    websocket.onclose = () => {
      if (callbacks.onDisconnect) {
        callbacks.onDisconnect();
      }
      // Do not automatically reconnect. Let the main script handle it.
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  connect();

  return {
    isAudio: is_audio,
    sendMessage(message) {
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify(message));
      }
    },
    disconnect() {
      if (websocket) {
        websocket.close();
      }
    }
  };
}
