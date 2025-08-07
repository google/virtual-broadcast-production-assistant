let websocket;

function initApi(callbacks, is_audio) {
  const sessionId = Math.random().toString().substring(10);
  // This placeholder is replaced by the entrypoint.sh script in the Docker container.
  // It falls back to localhost for local development if the placeholder is not replaced.
  const ws_base_url = '__WEBSOCKET_URL__';
  const final_ws_base_url = ws_base_url.startsWith('__') ? 'ws://localhost:8000' : ws_base_url;

  const ws_url = `${final_ws_base_url}/ws/${sessionId}?is_audio=${is_audio}`;

  function connect() {
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

export {
  initApi
};
