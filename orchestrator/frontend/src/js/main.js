import {
  messageInput,
  sendButton,
  micButton,
  addMessage,
  initUI,
  setMicButtonRecording,
} from './ui.js';
import {
  initApi
} from './api.js';
import {
  initAudio,
  stopAudioRecording,
  playAudio,
  stopAudioPlayback,
} from './audio.js';

document.addEventListener('DOMContentLoaded', () => {
  initUI();

  let api;
  let isAudio = false;
  let currentMessageId = null;

  function initializeConnection(audioEnabled) {
    if (api) {
      api.disconnect();
    }

    isAudio = audioEnabled;

    api = initApi({
      onMessage: (message) => {
        if (message.turn_complete) {
          currentMessageId = null;
          return;
        }

        if (message.interrupted) {
          stopAudioPlayback();
          return;
        }

        if (message.mime_type === 'audio/pcm') {
          playAudio(message.data);
        }

        if (message.mime_type === 'text/plain') {
          if (currentMessageId === null) {
            currentMessageId = `agent-message-${Date.now()}`;
            addMessage('', 'agent', currentMessageId);
          }
          const messageElement = document.getElementById(currentMessageId);
          if (messageElement) {
            messageElement.textContent += message.data;
          }
        }
      },
      onConnect: () => {
        console.log(`WebSocket connected in ${isAudio ? 'audio' : 'text'} mode.`);
        sendButton.disabled = false;
        micButton.disabled = false;
      },
      onDisconnect: () => {
        console.log('WebSocket disconnected.');
        sendButton.disabled = true;
        micButton.disabled = true;
      },
    }, isAudio);
  }

  function sendTextMessage() {
    const message = messageInput.value.trim();
    if (message && api) {
      addMessage(message, 'user');
      api.sendMessage({
        mime_type: 'text/plain',
        data: message,
      });
      messageInput.value = '';
    }
  }

  // Initial connection in text mode
  initializeConnection(false);

  sendButton.addEventListener('click', sendTextMessage);

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendTextMessage();
    }
  });

  micButton.addEventListener('click', () => {
    if (!isAudio) {
      initializeConnection(true);
      setMicButtonRecording(true);
      initAudio((pcmData) => {
        if (api) {
          api.sendMessage({
            mime_type: 'audio/pcm',
            data: pcmData,
          });
        }
      });
    } else {
      stopAudioRecording();
      setMicButtonRecording(false);
      initializeConnection(false);
    }
  });
});