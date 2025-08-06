let messageInput;
let sendButton;
let chatMessages;
let micButton;
let micButtonIcon;

function initUI() {
  messageInput = document.getElementById('message-input');
  sendButton = document.getElementById('send-button');
  chatMessages = document.getElementById('chat-messages');
  micButton = document.getElementById('mic-button');
  micButtonIcon = micButton.querySelector('.material-icons');
}

function addMessage(message, sender, messageId = null) {
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', `${sender}-message`);
  messageElement.textContent = message;
  if (messageId) {
    messageElement.id = messageId;
  }
  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setMicButtonRecording(isRecording) {
  if (isRecording) {
    micButton.classList.add('recording');
    micButtonIcon.textContent = 'stop';
  } else {
    micButton.classList.remove('recording');
    micButtonIcon.textContent = 'mic';
  }
}

export {
  initUI,
  addMessage,
  messageInput,
  sendButton,
  micButton,
  setMicButtonRecording
};