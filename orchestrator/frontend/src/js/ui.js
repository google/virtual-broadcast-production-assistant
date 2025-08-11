let messageInput;
let sendButton;
let chatMessages;
let micButton;
let micButtonIcon;
let signOutButton;
let chatContainer;
let loginContainer;
let loginButton;
let rundownSlider;
let rundownCuez;
let rundownSofie;

function initUI() {
    messageInput = document.getElementById('message-input');
    sendButton = document.getElementById('send-button');
    chatMessages = document.getElementById('chat-messages');
    micButton = document.getElementById('mic-button');
    micButtonIcon = micButton.querySelector('.material-icons');
    signOutButton = document.getElementById('sign-out-button');
    chatContainer = document.getElementById('chat-container');
    loginContainer = document.getElementById('login-container');
    loginButton = document.getElementById('login-button');
    rundownSlider = document.getElementById('rundown-slider');
    rundownCuez = document.getElementById('rundown-cuez');
    rundownSofie = document.getElementById('rundown-sofie');
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

function showLogin() {
    chatContainer.hidden = true;
    signOutButton.hidden = true;
    loginContainer.hidden = false;
    loginButton.hidden = true;
}

function showChat(isAnonymous) {
    chatContainer.hidden = false;
    loginContainer.hidden = true;
    if (isAnonymous) {
        signOutButton.hidden = true;
        loginButton.hidden = false;
    } else {
        signOutButton.hidden = false;
        loginButton.hidden = true;
    }
}

function updateRundownSlider(rundownSystem) {
    const isSofie = rundownSystem === 'sofie';
    rundownSlider.checked = isSofie;
    rundownCuez.classList.toggle('active', !isSofie);
    rundownSofie.classList.toggle('active', isSofie);
}

export {
    initUI,
    addMessage,
    messageInput,
    sendButton,
    micButton,
    signOutButton,
    loginButton,
    rundownSlider,
    setMicButtonRecording,
    showLogin,
    showChat,
    updateRundownSlider,
};