let websocket;

function initApi(callbacks, is_audio) {
  const sessionId = Math.random().toString().substring(10);
  const ws_url = `ws://localhost:8000/ws/${sessionId}?is_audio=${is_audio}`;

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
